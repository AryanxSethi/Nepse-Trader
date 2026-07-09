/** Format a number as NPR currency string. */
export function formatNPR(value: number | string | undefined | null, decimals = 2): string {
  if (value == null) return '\u2014'
  const num = typeof value === 'string' ? parseFloat(value.replace(/[^0-9.-]/g, '')) : value
  if (isNaN(num)) return '\u2014'
  return `NPR ${num.toLocaleString('en', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })}`
}

/** Format a value as signed percentage string. */
export function formatPercent(value: number | string | undefined | null, decimals = 2): string {
  if (value == null) return '\u2014'
  const num = typeof value === 'string' ? parseFloat(value.replace(/[^0-9.-]/g, '')) : value
  if (isNaN(num)) return '\u2014'
  const sign = num >= 0 ? '+' : ''
  return `${sign}${num.toFixed(decimals)}%`
}

/** Format a large turnover/volume number with abbreviated units. */
export function formatTurnover(val: number | null | undefined, scale: 'intl' | 'nepali' = 'intl'): string {
  if (val == null) return '\u2014'
  if (scale === 'nepali') {
    if (val >= 1e9) return `${(val / 1e9).toFixed(2)}B`
    if (val >= 1e7) return `${(val / 1e7).toFixed(2)}Cr`
    if (val >= 1e5) return `${(val / 1e5).toFixed(2)}L`
    return val.toLocaleString()
  }
  if (val >= 1e9) return `${(val / 1e9).toFixed(2)}B`
  if (val >= 1e6) return `${(val / 1e6).toFixed(2)}M`
  if (val >= 1e3) return `${(val / 1e3).toFixed(2)}K`
  return val.toFixed(2)
}

/** Format a value as signed numeric change. */
export function formatChange(value: number | string | undefined | null): string {
  if (value == null) return '\u2014'
  const num = typeof value === 'string' ? parseFloat(value.replace(/[^0-9.-]/g, '')) : value
  if (isNaN(num)) return '\u2014'
  const sign = num >= 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}`
}
