export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function isDocxFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".docx")
}

export function taskLabel(taskText: string): string {
  const match = taskText.match(/^(Q\d+|C\d+|[A-Za-z]\d*[\.)])/)
  return match ? match[1].replace(/\.$/, "") : "Question"
}
