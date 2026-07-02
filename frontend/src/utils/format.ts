export function formatNPR(value: number | string | undefined | null, decimals = 2): string {
  if (value == null) return '\u2014'
  const num = typeof value === 'string' ? parseFloat(value.replace(/[^0-9.-]/g, '')) : value
  if (isNaN(num)) return '\u2014'
  return `NPR ${num.toLocaleString('en', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`
}

export function formatPercent(value: number | string | undefined | null, decimals = 2): string {
  if (value == null) return '\u2014'
  const num = typeof value === 'string' ? parseFloat(value.replace(/[^0-9.-]/g, '')) : value
  if (isNaN(num)) return '\u2014'
  const sign = num >= 0 ? '+' : ''
  return `${sign}${num.toFixed(decimals)}%`
}

export function formatChange(value: number | string | undefined | null): string {
  if (value == null) return '\u2014'
  const num = typeof value === 'string' ? parseFloat(value.replace(/[^0-9.-]/g, '')) : value
  if (isNaN(num)) return '\u2014'
  const sign = num >= 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}`
}
