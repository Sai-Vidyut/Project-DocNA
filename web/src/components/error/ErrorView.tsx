import { Button } from "@/components/ui/button"

interface ErrorViewProps {
  title: string
  detail: string
  onRetry: () => void
}

export function ErrorView({ title, detail, onRetry }: ErrorViewProps) {
  return (
    <section
      className="flex min-h-[calc(100vh-var(--header-height))] flex-col items-center justify-center px-4 py-12"
      role="alert"
    >
      <span className="mb-4 text-lg text-[hsla(var(--error)/0.7)]" aria-hidden>
        ◇
      </span>
      <h2 className="m-0 mb-2 text-center text-[0.9375rem] font-medium text-[hsl(var(--error))]">{title}</h2>
      <p className="m-0 mb-5 max-w-[20rem] text-center text-sm text-[hsl(var(--muted))]">{detail}</p>
      <Button variant="secondary" type="button" onClick={onRetry}>
        Back to documents
      </Button>
    </section>
  )
}
