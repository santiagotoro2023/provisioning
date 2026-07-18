using System.Runtime.InteropServices;
using Microsoft.Extensions.Logging;

namespace DeployCoreAgent;

/// <summary>
/// Launches a process INTO the active console session (Session 1+, wherever
/// a real user is actually logged in) instead of as a normal child of this
/// service - which would otherwise inherit Session 0, same as every other
/// Windows service, with no access to the real interactive desktop at all.
///
/// THIS IS THE CONFIRMED ROOT CAUSE of Shadow's black screen on the first
/// real end-to-end test (see agent.log from that test: the WebRTC peer
/// connection reached "connected" - networking is session-independent, so
/// that part was always going to work - but zero video frames were ever
/// logged, because ffmpeg, launched via plain Process.Start from
/// ShadowSession, inherited THIS SERVICE's own Session 0). Session 0
/// isolation (present since Windows Vista, specifically to separate
/// services from the interactive user session for security) means a
/// Session-0 process's own desktop has no real rendered content on it at
/// all - this is true for gdigrab AND DXGI Desktop Duplication equally
/// (ddagrab was already flagged elsewhere as a future upgrade for
/// throughput/latency, but it would NOT have fixed this specific problem -
/// this is a session-level restriction, not a capture-API-level one).
///
/// Adapted from a well-known, community-verified reference implementation
/// (github.com/murrayju/CreateProcessAsUser - fetched and reviewed
/// directly, not reconstructed from memory) rather than derived from
/// scratch: this is genuinely one of the trickier, more security-sensitive
/// corners of Win32 - a wrong struct layout or P/Invoke signature here
/// fails silently or crashes a service process, not a compile error, and
/// this project already spent one real test cycle on an unverified-API
/// guess (SIPSorcery) it isn't willing to repeat here.
///
/// Deliberately does NOT try to redirect the launched process's stdout via
/// an inherited pipe handle across the CreateProcessAsUser boundary -
/// confirmed via research (not assumed) that ffmpeg writing to a named pipe
/// as its OUTPUT target is a known-unreliable pattern on Windows (it
/// commonly creates a plain file at that path instead of actually opening
/// the pipe). ShadowSession instead points ffmpeg at a real file and tails
/// it - see that class - which needs no handle-inheritance plumbing here at
/// all, at the cost of a small amount of disk I/O that's genuinely
/// negligible at this data rate (a low-fps H.264 stream, not raw video).
///
/// KNOWN LIMITATION, stated plainly, not hidden: WTSQueryUserToken needs an
/// ACTUAL logged-in user session to query a token from. If nobody is signed
/// in yet (the Windows lock/login screen itself - the original "including
/// the Windows login screen" goal from this feature's own README), there is
/// no token to query and StartInActiveSessionAsync throws. Capturing the
/// pre-login secure desktop is a genuinely separate, harder problem
/// (attaching to WinSta0's "Winlogon" desktop specifically, with its own
/// distinct restrictions even for SYSTEM) that mature remote-desktop
/// products have entire subsystems for - not attempted here. Shadow today
/// requires someone already logged into the target machine; test it that
/// way, not sitting at the lock screen.
/// </summary>
internal static class SessionCapture
{
    #region Win32 constants

    private const int CREATE_UNICODE_ENVIRONMENT = 0x00000400;
    private const int CREATE_NO_WINDOW = 0x08000000;
    private const uint INVALID_SESSION_ID = 0xFFFFFFFF;
    private static readonly IntPtr WTS_CURRENT_SERVER_HANDLE = IntPtr.Zero;

    private const uint TOKEN_ADJUST_PRIVILEGES = 0x0020;
    private const uint TOKEN_QUERY = 0x0008;
    private const uint SE_PRIVILEGE_ENABLED = 0x00000002;

    #endregion

    #region Win32 structs

    private enum WTS_CONNECTSTATE_CLASS
    {
        WTSActive, WTSConnected, WTSConnectQuery, WTSShadow, WTSDisconnected,
        WTSIdle, WTSListen, WTSReset, WTSDown, WTSInit,
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct WTS_SESSION_INFO
    {
        public readonly uint SessionID;
        [MarshalAs(UnmanagedType.LPStr)] public readonly string pWinStationName;
        public readonly WTS_CONNECTSTATE_CLASS State;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct PROCESS_INFORMATION
    {
        public IntPtr hProcess;
        public IntPtr hThread;
        public uint dwProcessId;
        public uint dwThreadId;
    }

    private enum SECURITY_IMPERSONATION_LEVEL { SecurityAnonymous = 0, SecurityIdentification = 1, SecurityImpersonation = 2, SecurityDelegation = 3 }
    private enum TOKEN_TYPE { TokenPrimary = 1, TokenImpersonation = 2 }

    [StructLayout(LayoutKind.Sequential)]
    private struct STARTUPINFO
    {
        public int cb;
        public string? lpReserved;
        public string? lpDesktop;
        public string? lpTitle;
        public uint dwX, dwY, dwXSize, dwYSize, dwXCountChars, dwYCountChars, dwFillAttribute, dwFlags;
        public short wShowWindow, cbReserved2;
        public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct LUID { public uint LowPart; public int HighPart; }

    [StructLayout(LayoutKind.Sequential)]
    private struct LUID_AND_ATTRIBUTES { public LUID Luid; public uint Attributes; }

    [StructLayout(LayoutKind.Sequential)]
    private struct TOKEN_PRIVILEGES { public uint PrivilegeCount; public LUID_AND_ATTRIBUTES Privileges; }

    #endregion

    #region DllImports

    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool CreateProcessAsUser(
        IntPtr hToken, string? lpApplicationName, string lpCommandLine, IntPtr lpProcessAttributes,
        IntPtr lpThreadAttributes, bool bInheritHandles, uint dwCreationFlags, IntPtr lpEnvironment,
        string? lpCurrentDirectory, ref STARTUPINFO lpStartupInfo, out PROCESS_INFORMATION lpProcessInformation);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool DuplicateTokenEx(IntPtr hExistingToken, uint dwDesiredAccess, IntPtr lpTokenAttributes,
        int impersonationLevel, int tokenType, ref IntPtr phNewToken);

    [DllImport("userenv.dll", SetLastError = true)]
    private static extern bool CreateEnvironmentBlock(ref IntPtr lpEnvironment, IntPtr hToken, bool bInherit);

    [DllImport("userenv.dll", SetLastError = true)]
    private static extern bool DestroyEnvironmentBlock(IntPtr lpEnvironment);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool CloseHandle(IntPtr hObject);

    [DllImport("kernel32.dll")]
    private static extern uint WTSGetActiveConsoleSessionId();

    [DllImport("wtsapi32.dll", SetLastError = true)]
    private static extern bool WTSQueryUserToken(uint sessionId, out IntPtr phToken);

    [DllImport("wtsapi32.dll", SetLastError = true)]
    private static extern int WTSEnumerateSessions(IntPtr hServer, int reserved, int version, out IntPtr ppSessionInfo, out int pCount);

    [DllImport("wtsapi32.dll")]
    private static extern void WTSFreeMemory(IntPtr pMemory);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool OpenProcessToken(IntPtr processHandle, uint desiredAccess, out IntPtr tokenHandle);

    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool LookupPrivilegeValue(string? lpSystemName, string lpName, out LUID lpLuid);

    [DllImport("advapi32.dll", SetLastError = true)]
    private static extern bool AdjustTokenPrivileges(IntPtr tokenHandle, bool disableAllPrivileges,
        ref TOKEN_PRIVILEGES newState, uint bufferLength, IntPtr previousState, IntPtr returnLength);

    [DllImport("kernel32.dll")]
    private static extern IntPtr GetCurrentProcess();

    #endregion

    /// <summary>
    /// WTSQueryUserToken needs SeTcbPrivilege - held by LocalSystem's token
    /// (which this service runs as - New-Service with no -Credential in
    /// remote_agent_install.ps1 defaults to LocalSystem) but, like several
    /// of LocalSystem's privileges, not necessarily ENABLED by default.
    /// Mirrors the existing EnsureSoftwareSasGeneration pattern (explicitly
    /// ensure a required privilege/policy rather than assume it) - called
    /// once at agent startup, alongside that call, not per-session.
    /// </summary>
    public static void EnsureTcbPrivilege(ILogger logger)
    {
        try
        {
            if (!OpenProcessToken(GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, out var hToken))
            {
                logger.LogWarning("OpenProcessToken failed (0x{Error:X}) - Shadow's session-launch may not work.", Marshal.GetLastWin32Error());
                return;
            }
            try
            {
                if (!LookupPrivilegeValue(null, "SeTcbPrivilege", out var luid))
                {
                    logger.LogWarning("LookupPrivilegeValue(SeTcbPrivilege) failed (0x{Error:X}).", Marshal.GetLastWin32Error());
                    return;
                }
                var privileges = new TOKEN_PRIVILEGES
                {
                    PrivilegeCount = 1,
                    Privileges = new LUID_AND_ATTRIBUTES { Luid = luid, Attributes = SE_PRIVILEGE_ENABLED },
                };
                if (!AdjustTokenPrivileges(hToken, false, ref privileges, 0, IntPtr.Zero, IntPtr.Zero))
                {
                    logger.LogWarning("AdjustTokenPrivileges(SeTcbPrivilege) failed (0x{Error:X}).", Marshal.GetLastWin32Error());
                    return;
                }
                logger.LogInformation("SeTcbPrivilege enabled - session-launch (Shadow capture) is available.");
            }
            finally
            {
                CloseHandle(hToken);
            }
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Could not ensure SeTcbPrivilege - Shadow's session-launch may not work.");
        }
    }

    private static uint GetActiveConsoleSessionId()
    {
        // WTSEnumerateSessions + the first WTSActive entry first (the
        // documented, more reliable way to find the session an actual
        // logged-in user owns); WTSGetActiveConsoleSessionId as a fallback
        // for when enumeration itself doesn't turn up an active session.
        if (WTSEnumerateSessions(WTS_CURRENT_SERVER_HANDLE, 0, 1, out var pSessionInfo, out var count) != 0)
        {
            try
            {
                var elementSize = Marshal.SizeOf<WTS_SESSION_INFO>();
                for (var i = 0; i < count; i++)
                {
                    var info = Marshal.PtrToStructure<WTS_SESSION_INFO>(pSessionInfo + i * elementSize);
                    if (info.State == WTS_CONNECTSTATE_CLASS.WTSActive) return info.SessionID;
                }
            }
            finally
            {
                WTSFreeMemory(pSessionInfo);
            }
        }
        return WTSGetActiveConsoleSessionId();
    }

    /// <summary>
    /// Launches <paramref name="commandLine"/> into the active console
    /// session's own desktop - not this service's Session 0 - and returns
    /// the new process's id (so the caller can later terminate it via the
    /// normal System.Diagnostics.Process.GetProcessById/.Kill(), which works
    /// on any process this SYSTEM-context service has rights over regardless
    /// of who actually started it).
    /// </summary>
    public static uint StartInActiveSession(string commandLine, string? workingDirectory)
    {
        var sessionId = GetActiveConsoleSessionId();
        if (sessionId == INVALID_SESSION_ID)
        {
            throw new InvalidOperationException("No active console session found - is anyone actually logged into this machine? (see this class's own \"known limitation\" doc comment - the pre-login lock/login screen has no user token to query).");
        }

        if (!WTSQueryUserToken(sessionId, out var hImpersonationToken))
        {
            throw new InvalidOperationException($"WTSQueryUserToken for session {sessionId} failed (0x{Marshal.GetLastWin32Error():X}) - no logged-in user to launch into, or SeTcbPrivilege isn't enabled (see EnsureTcbPrivilege).");
        }

        var hUserToken = IntPtr.Zero;
        var pEnv = IntPtr.Zero;
        try
        {
            // An impersonation token from WTSQueryUserToken must be
            // duplicated to a PRIMARY token before CreateProcessAsUser will
            // accept it - confirmed against the reference implementation,
            // not assumed.
            if (!DuplicateTokenEx(hImpersonationToken, 0, IntPtr.Zero,
                    (int)SECURITY_IMPERSONATION_LEVEL.SecurityImpersonation, (int)TOKEN_TYPE.TokenPrimary, ref hUserToken))
            {
                throw new InvalidOperationException($"DuplicateTokenEx failed (0x{Marshal.GetLastWin32Error():X}).");
            }

            if (!CreateEnvironmentBlock(ref pEnv, hUserToken, false))
            {
                throw new InvalidOperationException($"CreateEnvironmentBlock failed (0x{Marshal.GetLastWin32Error():X}).");
            }

            var startupInfo = new STARTUPINFO
            {
                cb = Marshal.SizeOf<STARTUPINFO>(),
                lpDesktop = "winsta0\\default",
            };
            const uint creationFlags = CREATE_UNICODE_ENVIRONMENT | CREATE_NO_WINDOW;

            if (!CreateProcessAsUser(hUserToken, null, commandLine, IntPtr.Zero, IntPtr.Zero, false,
                    creationFlags, pEnv, workingDirectory, ref startupInfo, out var processInfo))
            {
                throw new InvalidOperationException($"CreateProcessAsUser failed (0x{Marshal.GetLastWin32Error():X}).");
            }

            CloseHandle(processInfo.hThread);
            CloseHandle(processInfo.hProcess);
            return processInfo.dwProcessId;
        }
        finally
        {
            if (pEnv != IntPtr.Zero) DestroyEnvironmentBlock(pEnv);
            if (hUserToken != IntPtr.Zero) CloseHandle(hUserToken);
            CloseHandle(hImpersonationToken);
        }
    }
}
