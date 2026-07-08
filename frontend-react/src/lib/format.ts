export function fmtMultiple(value: number | null | undefined): string {
  return value == null ? '—' : `${value.toFixed(2)}x`
}

export function fmtPct(value: number | null | undefined, digits = 1): string {
  return value == null ? '—' : `${(value * 100).toFixed(digits)}%`
}

export function fmtSignedPct(value: number | null | undefined, digits = 1): string {
  if (value == null) return '—'
  const sign = value > 0 ? '+' : ''
  return `${sign}${(value * 100).toFixed(digits)}%`
}

export function fmtSize(musd: number | null | undefined): string {
  if (musd == null) return '—'
  if (musd >= 1000) return `$${(musd / 1000).toFixed(1)}B`
  return `$${musd.toFixed(0)}M`
}

export function fmtStatus(status: string): string {
  return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
