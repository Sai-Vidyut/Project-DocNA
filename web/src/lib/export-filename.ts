/** Client-side export filename helpers — download blob name only; backend unchanged. */

export function defaultExportBasename(sourceFilename: string): string {
  const base = sourceFilename.replace(/\.docx$/i, "").trim()
  if (!base) return "completed"
  return `${base}_completed`
}

/** Strip extension and unsafe path characters; never returns empty. */
export function sanitizeExportBasename(raw: string): string {
  let name = raw.trim().replace(/\.docx$/i, "")
  name = name.replace(/[/\\?%*:|"<>]/g, "-")
  name = name.replace(/\s+/g, " ").replace(/^\.+/, "").trim()
  if (!name) return "completed"
  return name.slice(0, 200)
}

export function exportDownloadFilename(basename: string): string {
  return `${sanitizeExportBasename(basename)}.docx`
}
