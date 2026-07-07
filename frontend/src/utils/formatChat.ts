function sanitize(text: string): string {
  const map: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#x27;',
  }
  return text.replace(/[&<>"']/g, (c) => map[c])
}

/** Sanitize and convert markdown-like text to HTML. */
export function formatResponse(text: string): string {
  const escaped = sanitize(text)
  let formatted = escaped
  formatted = formatted.replace(/\*\*(.+?)\*\*/g, '$1')
  formatted = formatted.replace(/__(.+?)__/g, '$1')
  formatted = formatted.replace(/^### (.+)$/gm, '<div class="text-xs font-semibold text-text mt-2 mb-1">$1</div>')
  formatted = formatted.replace(/^- (.+)$/gm, '<span class="block text-text-muted">\u2022 $1</span>')
  formatted = formatted.replace(/\n{2,}/g, '<div class="h-2"></div>')
  formatted = formatted.replace(/\n/g, '<br/>')
  return formatted
}
