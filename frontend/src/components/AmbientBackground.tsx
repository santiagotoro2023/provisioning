import ConnectedDots from "./ConnectedDots";

/** The decorative blurred-blob + connected-dots layer shared by
 * AuthBackground (login/setup, full intensity) and any page that wants a
 * quieter version of the same effect behind real working content (the
 * Dashboard). Always pointer-events-none and absolutely positioned to
 * fill its nearest `relative` ancestor. */
export default function AmbientBackground({ subtle = false }: { subtle?: boolean }) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className={subtle ? "opacity-50" : ""}>
        <div className="auth-bg-blob-a absolute -left-24 -top-24 h-96 w-96 rounded-full bg-blue-400/60 blur-3xl dark:bg-blue-800/30" />
        <div className="auth-bg-blob-b absolute -right-32 top-1/3 h-[28rem] w-[28rem] rounded-full bg-sky-400/50 blur-3xl dark:bg-sky-900/25" />
        <div className="auth-bg-blob-c absolute -bottom-32 left-1/4 h-80 w-80 rounded-full bg-blue-500/40 blur-3xl dark:bg-blue-950/40" />
      </div>
      {/* The connecting dots are the signature detail, so they stay
          outside the blobs' dimming wrapper on purpose: even the "subtle"
          Dashboard variant only backs off a little, not to near-invisible. */}
      <ConnectedDots opacity={subtle ? 0.8 : 1} />
    </div>
  );
}
