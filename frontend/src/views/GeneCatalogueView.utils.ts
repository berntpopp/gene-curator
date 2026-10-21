// Pure display helpers for GeneCatalogueView.vue
import type { Schema } from '@/types/api'

type CatalogueEntry = Schema<'GeneCatalogueEntry'>

const CLASSIFICATION_PRIORITY = [
  'definitive',
  'strong',
  'moderate',
  'limited',
  'no_known',
  'disputed',
  'refuted'
]

export const formatClassification = (classification: string | null | undefined): string => {
  if (!classification) return 'Unknown'
  // Capitalize first letter
  return classification.charAt(0).toUpperCase() + classification.slice(1).replace(/_/g, ' ')
}

export const formatScore = (score: number | string | null | undefined): string => {
  if (score === null || score === undefined) return '-'
  return typeof score === 'number' ? score.toFixed(1) : score
}

// Get best (highest) score from all scope curations
export const getBestScore = (item: CatalogueEntry): number | null => {
  if (!item.scope_curations || item.scope_curations.length === 0) return null
  const scores = item.scope_curations
    .map(c => c.total_score)
    .filter((s): s is number => s !== null && s !== undefined)
  if (scores.length === 0) return null
  return Math.max(...scores)
}

// Get best (highest priority) classification
export const getBestClassification = (item: CatalogueEntry): string | null => {
  const classifications = Object.keys(item.classifications || {})
  if (classifications.length === 0) return null

  // Sort by priority and return the best one
  classifications.sort((a, b) => {
    const aIndex = CLASSIFICATION_PRIORITY.indexOf(a.toLowerCase())
    const bIndex = CLASSIFICATION_PRIORITY.indexOf(b.toLowerCase())
    return (aIndex === -1 ? 999 : aIndex) - (bIndex === -1 ? 999 : bIndex)
  })
  return classifications[0] ?? null
}

// Get score color class based on value
export const getScoreColorClass = (score: number | null | undefined): string => {
  if (score === null || score === undefined) return 'text-medium-emphasis'
  if (score >= 12) return 'text-success'
  if (score >= 9) return 'text-primary'
  if (score >= 6) return 'text-warning'
  return 'text-secondary'
}

const CLASSIFICATION_COLORS: Record<string, string> = {
  definitive: 'success',
  strong: 'primary',
  moderate: 'warning',
  limited: 'secondary',
  no_known: 'default',
  disputed: 'error',
  refuted: 'error'
}

// Classification color mapping
export const getClassificationColor = (classification: string | null | undefined): string => {
  return CLASSIFICATION_COLORS[classification?.toLowerCase() ?? ''] || 'default'
}

const CLASSIFICATION_ICONS: Record<string, string> = {
  definitive: 'mdi-check-circle',
  strong: 'mdi-check-circle-outline',
  moderate: 'mdi-alert-circle',
  limited: 'mdi-help-circle',
  no_known: 'mdi-minus-circle',
  disputed: 'mdi-alert',
  refuted: 'mdi-close-circle'
}

// Classification icon mapping
export const getClassificationIcon = (classification: string | null | undefined): string => {
  return CLASSIFICATION_ICONS[classification?.toLowerCase() ?? ''] || 'mdi-help-circle-outline'
}
