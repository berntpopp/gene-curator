/**
 * ClinGen classifications: the single source for label, order, colour, icon and mark strength.
 * `color` is a theme colour (see main.ts); `bars` is the number of filled bars in ClassificationMark.
 * Only Disputed and Refuted carry a hue; strength is shape, not colour.
 */
export type ClassificationKey =
  'definitive' | 'strong' | 'moderate' | 'limited' | 'no_known' | 'disputed' | 'refuted'

export interface ClassificationInfo {
  key: ClassificationKey | 'unknown'
  label: string
  color: string
  icon: string
  bars: number
}

/** Ordered strongest evidence first. */
export const CLASSIFICATIONS: readonly ClassificationInfo[] = [
  {
    key: 'definitive',
    label: 'Definitive',
    color: 'cls-definitive',
    icon: 'mdi-check-circle',
    bars: 4
  },
  {
    key: 'strong',
    label: 'Strong',
    color: 'cls-strong',
    icon: 'mdi-check-circle-outline',
    bars: 3
  },
  {
    key: 'moderate',
    label: 'Moderate',
    color: 'cls-moderate',
    icon: 'mdi-circle-half-full',
    bars: 2
  },
  { key: 'limited', label: 'Limited', color: 'cls-limited', icon: 'mdi-circle-outline', bars: 1 },
  {
    key: 'no_known',
    label: 'No known disease relationship',
    color: 'cls-no-known',
    icon: 'mdi-minus-circle-outline',
    bars: 0
  },
  {
    key: 'disputed',
    label: 'Disputed',
    color: 'cls-disputed',
    icon: 'mdi-scale-unbalanced',
    bars: 0
  },
  { key: 'refuted', label: 'Refuted', color: 'cls-refuted', icon: 'mdi-close', bars: 0 }
]

const UNKNOWN: ClassificationInfo = {
  key: 'unknown',
  label: 'Not classified',
  color: 'cls-no-known',
  icon: 'mdi-help-circle-outline',
  bars: 0
}

/** Resolve "Strong", "strong", "No Known Disease Relationship" or "no_known"; unknown values are neutral. */
export function getClassification(value: string | null | undefined): ClassificationInfo {
  const v = (value ?? '')
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_')
  const key = v.startsWith('no_known') ? 'no_known' : v
  const found = CLASSIFICATIONS.find(c => c.key === key)
  if (found) return found
  return value ? { ...UNKNOWN, label: value } : UNKNOWN
}
