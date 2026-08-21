import { ZoomIn, ZoomOut, Maximize2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"

interface DocumentToolbarProps {
  filename: string
  downloadReady: boolean
  zoomPercent: number
  onZoomIn: () => void
  onZoomOut: () => void
  onZoomFit: () => void
}

export function DocumentToolbar({
  filename,
  downloadReady,
  zoomPercent,
  onZoomIn,
  onZoomOut,
  onZoomFit,
}: DocumentToolbarProps) {
  return (
    <div className="glass-1 flex shrink-0 flex-wrap items-center justify-between gap-2 rounded-md px-2.5 py-1.5">
      <div className="min-w-0 flex-1">
        <p className="m-0 truncate text-[0.8125rem] font-medium text-[hsl(var(--foreground))]">{filename}</p>
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {downloadReady ? (
          <Badge variant="success" role="status">
            Ready
          </Badge>
        ) : (
          <Badge variant="default">Review</Badge>
        )}
        <div
          className="flex items-center rounded border border-[hsla(var(--foreground)/0.06)] bg-[hsla(var(--background)/0.35)] p-0.5"
          role="group"
          aria-label="Zoom controls"
        >
          <Button variant="ghost" className="size-6 px-0" aria-label="Zoom out" onClick={onZoomOut}>
            <ZoomOut className="size-3" aria-hidden />
          </Button>
          <span
            className="min-w-[2.5rem] px-0.5 text-center text-[0.65rem] tabular-nums text-[hsl(var(--muted))]"
            aria-live="polite"
          >
            {zoomPercent}%
          </span>
          <Button variant="ghost" className="size-6 px-0" aria-label="Zoom in" onClick={onZoomIn}>
            <ZoomIn className="size-3" aria-hidden />
          </Button>
          <Button variant="ghost" className="size-6 px-0" aria-label="Fit to view" onClick={onZoomFit}>
            <Maximize2 className="size-3" aria-hidden />
          </Button>
        </div>
      </div>
    </div>
  )
}
