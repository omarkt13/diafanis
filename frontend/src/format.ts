export const CABIN_LABEL: Record<string, string> = {
  economy: 'Economy',
  premium: 'Premium',
  business: 'Business',
  first: 'First',
}

export function time(iso: string): string {
  return iso.slice(11, 16)
}

export function dayLabel(iso: string): string {
  const d = new Date(iso.slice(0, 10) + 'T12:00:00Z')
  return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })
}

export function dayOffset(fromIso: string, toIso: string): number {
  const a = Date.parse(fromIso.slice(0, 10))
  const b = Date.parse(toIso.slice(0, 10))
  return Math.round((b - a) / 86_400_000)
}

export function duration(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return `${h} h ${m.toString().padStart(2, '0')} min`
}

export function miles(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(n % 1000 ? 1 : 0)}k` : String(n)
}

export function money(value: number, currency: string | null): string {
  if (!currency || currency === 'mixed') return `${value.toFixed(0)}${currency === 'mixed' ? ' (mixed)' : ''}`
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(value)
  } catch {
    return `${value.toFixed(0)} ${currency}`
  }
}

export function age(hours: number): { label: string; tone: 'fresh' | 'aging' | 'stale' } {
  if (hours < 0) return { label: 'age unknown', tone: 'stale' }
  const label = hours < 24 ? `${Math.max(1, Math.round(hours))} h old` : `${Math.round(hours / 24)} d old`
  return { label, tone: hours < 24 ? 'fresh' : hours < 24 * 7 ? 'aging' : 'stale' }
}
