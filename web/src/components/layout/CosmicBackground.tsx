export function CosmicBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden" aria-hidden>
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_50%_at_50%_-8%,hsla(228_50%_14%/0.5)_0%,transparent_50%),linear-gradient(180deg,hsl(228_44%_3%)_0%,hsl(var(--background))_40%,hsl(228_38%_5%)_100%)]" />
      <div className="cosmic-ambient cosmic-ambient-a absolute rounded-full blur-[100px]" />
      <div className="cosmic-ambient cosmic-ambient-b absolute rounded-full blur-[100px]" />
      <div className="cosmic-ambient cosmic-ambient-c absolute rounded-full blur-[80px]" />
    </div>
  )
}
