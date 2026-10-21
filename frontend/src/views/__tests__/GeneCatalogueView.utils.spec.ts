import { describe, it, expect } from 'vitest'
import {
  formatClassification,
  formatScore,
  getBestScore,
  getBestClassification,
  getScoreColorClass,
  getClassificationColor,
  getClassificationIcon
} from '@/views/GeneCatalogueView.utils'

describe('formatClassification', () => {
  it('capitalises and replaces underscores', () => {
    expect(formatClassification('no_known')).toBe('No known')
    expect(formatClassification('definitive')).toBe('Definitive')
  })
  it('returns Unknown for empty input', () => {
    expect(formatClassification(null)).toBe('Unknown')
    expect(formatClassification('')).toBe('Unknown')
  })
})

describe('formatScore', () => {
  it('returns a dash for null or undefined', () => {
    expect(formatScore(null)).toBe('-')
    expect(formatScore(undefined)).toBe('-')
  })
  it('formats numbers to one decimal and passes strings through', () => {
    expect(formatScore(7.25)).toBe('7.3')
    expect(formatScore('n/a')).toBe('n/a')
  })
})

describe('getBestScore', () => {
  it('returns null without scope curations', () => {
    expect(getBestScore({ scope_curations: [] } as never)).toBeNull()
    expect(getBestScore({} as never)).toBeNull()
  })
  it('returns null when no curation has a score', () => {
    const item = { scope_curations: [{ total_score: null }, { total_score: undefined }] }
    expect(getBestScore(item as never)).toBeNull()
  })
  it('returns the highest score', () => {
    const item = {
      scope_curations: [{ total_score: 4 }, { total_score: null }, { total_score: 9 }]
    }
    expect(getBestScore(item as never)).toBe(9)
  })
})

describe('getBestClassification', () => {
  it('returns null without classifications', () => {
    expect(getBestClassification({ classifications: {} } as never)).toBeNull()
    expect(getBestClassification({} as never)).toBeNull()
  })
  it('picks the highest-priority classification', () => {
    const item = { classifications: { refuted: 1, moderate: 2, definitive: 1 } }
    expect(getBestClassification(item as never)).toBe('definitive')
  })
  it('ranks unknown classifications last', () => {
    const item = { classifications: { custom: 1, limited: 1 } }
    expect(getBestClassification(item as never)).toBe('limited')
  })
})

describe('getScoreColorClass', () => {
  it.each([
    [null, 'text-medium-emphasis'],
    [undefined, 'text-medium-emphasis'],
    [12, 'text-success'],
    [9, 'text-primary'],
    [6, 'text-warning'],
    [2, 'text-secondary']
  ])('score %s -> %s', (score, expected) => {
    expect(getScoreColorClass(score)).toBe(expected)
  })
})

describe('getClassificationColor and getClassificationIcon', () => {
  it('maps known classifications case-insensitively', () => {
    expect(getClassificationColor('Definitive')).toBe('success')
    expect(getClassificationIcon('DEFINITIVE')).toBe('mdi-check-circle')
  })
  it('falls back for unknown or missing classifications', () => {
    expect(getClassificationColor('unknown')).toBe('default')
    expect(getClassificationColor(null)).toBe('default')
    expect(getClassificationIcon(undefined)).toBe('mdi-help-circle-outline')
  })
})
