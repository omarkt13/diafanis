export const CABIN_LABEL: Record<string, string> = { economy: 'Economy', premium: 'Premium economy', business: 'Business', first: 'First' }

export const time = (iso: string) => iso.slice(11, 16)

export function dayLabel(iso: string, long = false): string {
  const d = new Date(iso.slice(0, 10) + 'T12:00:00Z')
  return d.toLocaleDateString('en-GB', { weekday: long ? 'long' : 'short', day: 'numeric', month: 'short', timeZone: 'UTC' })
}

export function shiftDate(iso: string, days: number): string {
  const d = new Date(iso + 'T12:00:00Z')
  d.setUTCDate(d.getUTCDate() + days)
  return d.toISOString().slice(0, 10)
}

export const dayOffset = (a: string, b: string) => Math.round((Date.parse(b.slice(0, 10)) - Date.parse(a.slice(0, 10))) / 86_400_000)

export function duration(minutes: number): string {
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return m ? `${h} hr ${m} min` : `${h} hr`
}

export const miles = (n: number) => (n >= 1000 ? `${(n / 1000).toFixed(n % 1000 ? 1 : 0)}k` : String(n))

export function money(value: number, currency: string | null): string {
  if (!currency || currency === 'mixed') return `≈ $${Math.round(value)}`
  try {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(value)
  } catch {
    return `${Math.round(value)} ${currency}`
  }
}

export const usd = (v: number) => '$' + Math.round(v).toLocaleString('en-US')

export function age(hours: number): { label: string; tone: 'fresh' | 'aging' | 'stale' } {
  if (hours < 0) return { label: 'age unknown', tone: 'stale' }
  const label = hours < 24 ? `checked ${Math.max(1, Math.round(hours))} h ago` : `checked ${Math.round(hours / 24)} d ago`
  return { label, tone: hours < 24 ? 'fresh' : hours < 24 * 7 ? 'aging' : 'stale' }
}
