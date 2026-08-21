import { cn } from "@/lib/utils"

interface ProcessingOrbProps {
  activeLabel: string
}

export function ProcessingOrb({ activeLabel }: ProcessingOrbProps) {
  return (
    <div className="relative mx-auto my-5 size-[4.5rem]" role="img" aria-label={activeLabel}>
      <div
        className="pointer-events-none absolute inset-[-12%] rounded-full bg-[radial-gradient(circle,hsla(var(--ai-glow)/0.12),transparent_70%)] motion-safe:animate-pulse motion-reduce:animate-none"
        aria-hidden
      />
      <svg
        className="absolute inset-0 size-full -rotate-90 motion-safe:animate-[spin_10s_linear_infinite] motion-reduce:animate-none"
        viewBox="0 0 72 72"
        aria-hidden
      >
        <circle cx="36" cy="36" r="30" fill="none" stroke="hsla(var(--foreground) / 0.05)" strokeWidth="1.5" />
        <circle
          cx="36"
          cy="36"
          r="30"
          fill="none"
          stroke="url(#processing-ring)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeDasharray="56 132"
          className="motion-safe:animate-[spin_3s_linear_infinite] motion-reduce:animate-none"
        />
        <defs>
          <linearGradient id="processing-ring" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="hsl(var(--primary))" />
            <stop offset="100%" stopColor="hsl(var(--secondary))" />
          </linearGradient>
        </defs>
      </svg>
      <div
        className={cn(
          "absolute inset-[32%] rounded-full",
          "bg-gradient-to-br from-[hsl(var(--primary))] to-[hsl(var(--secondary))]",
          "shadow-[0_0_16px_hsla(var(--ai-glow)/0.35)]",
        )}
        aria-hidden
      />
    </div>
  )
}
