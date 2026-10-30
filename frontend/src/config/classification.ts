import { reactive } from 'vue'

/**
 * ClinGen classifications: the single source for label, order, colour, icon and mark strength.
 * A schema may declare its own (`scoring_configuration.classifications`, #539); each renders
 * like the ClinGen class its `tone` names. Without one, the ClinGen list applies.
 * `color` is a theme colour (see main.ts); `bars` is the number of filled bars in ClassificationMark.
 * Only Disputed and Refuted carry a hue; strength is shape, not colour.
 */
export type ClassificationKey =
  'definitive' | 'strong' | 'moderate' | 'limited' | 'no_known' | 'disputed' | 'refuted'

export interface ClassificationInfo {
  key: string
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

/** A schema-declared class (#539); the backend validates the shape on publish. */
export interface DeclaredClassification {
  key: string
  label: string
  order: number
  tone: ClassificationKey
}

// Declared classes by normalised key, with their rank; reactive so marks re-render.
const declared = reactive(new Map<string, ClassificationInfo & { order: number }>())

const normalise = (value: string | null | undefined) =>
  (value ?? '').trim().toLowerCase().replace(/[ -]/g, '_') // each one, as the backend's class_key

/** The class key the API stores: same rule as the backend's class_key. */
export function classKey(value: string | null | undefined): string {
  const v = normalise(value)
  return v.startsWith('no_known') ? 'no_known' : v
}

/** Make a schema's classes known everywhere; a list without them changes nothing. */
export function registerClassifications(list: unknown): void {
  if (!Array.isArray(list)) return
  for (const c of list as DeclaredClassification[]) {
    const tone = CLASSIFICATIONS.find(t => t.key === c?.tone)
    if (!tone || typeof c.key !== 'string') continue
    declared.set(normalise(c.key), { ...tone, key: c.key, label: c.label, order: c.order })
  }
}

/** Resolve "Strong", "strong", "No Known Disease Relationship" or "no_known"; unknown values are neutral. */
export function getClassification(value: string | null | undefined): ClassificationInfo {
  const v = normalise(value)
  const own = declared.get(v)
  if (own) return own
  const key = v.startsWith('no_known') ? 'no_known' : v
  const found = CLASSIFICATIONS.find(c => c.key === key)
  if (found) return found
  return value ? { ...UNKNOWN, label: value } : UNKNOWN
}

/** Sort rank, strongest first: a declared class's order, else its ClinGen position. */
export function classificationRank(value: string | null | undefined): number {
  const own = declared.get(normalise(value))
  if (own) return own.order
  const i = CLASSIFICATIONS.indexOf(getClassification(value))
  return i < 0 ? CLASSIFICATIONS.length : i
}

/** Array.sort comparator: strongest first. */
export const compareClassifications = (a: string, b: string) =>
  classificationRank(a) - classificationRank(b)
