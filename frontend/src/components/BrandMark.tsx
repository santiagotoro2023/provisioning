export default function BrandMark({ size = 32, className = "" }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <rect x="3" y="4" width="19" height="6" rx="1.5" fill="#1d4ed8" />
      <rect x="3" y="13" width="19" height="6" rx="1.5" fill="#2563eb" />
      <rect x="3" y="22" width="19" height="6" rx="1.5" fill="#3b82f6" />
      <path d="M22 22.3 L30 25 L22 27.7 Z" fill="#38bdf8" />
    </svg>
  );
}
