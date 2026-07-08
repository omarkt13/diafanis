import { Badge } from '@/components/ui/badge'
import { fmtSignedPct } from '@/lib/format'

export function PmeBadge({ value }: { value: number | null }) {
  if (value == null) return <span className="text-slate-400">—</span>
  const tone = value > 0.02 ? 'positive' : value < -0.02 ? 'negative' : 'neutral'
  return <Badge tone={tone}>{fmtSignedPct(value)} vs benchmark</Badge>
}

export function ConfidenceBadge({ value }: { value: string | null }) {
  if (!value) return null
  const tone = value === 'high' ? 'positive' : value === 'medium' ? 'neutral' : 'negative'
  const label = value === 'high' ? 'Calibrated to public mark' : value === 'medium' ? 'Track-record based' : 'Model only'
  return <Badge tone={tone}>{label}</Badge>
}
