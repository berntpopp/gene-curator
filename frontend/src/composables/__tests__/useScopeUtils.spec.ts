import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('@/services/logService', () => ({
  logService: { warn: vi.fn(), error: vi.fn(), info: vi.fn(), debug: vi.fn() }
}))

import { useScopeUtils } from '../useScopeUtils'
import { logService } from '@/services/logService'

describe('useScopeUtils', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('formatDate', () => {
    it('returns placeholder for empty values', () => {
      const { formatDate } = useScopeUtils()

      expect(formatDate(null)).toBe('No due date')
      expect(formatDate(undefined)).toBe('No due date')
      expect(formatDate('')).toBe('No due date')
    })

    it('formats ISO strings and Date objects with locale formatting', () => {
      const { formatDate } = useScopeUtils()
      const date = new Date('2025-12-31T12:00:00Z')

      expect(formatDate('2025-12-31T12:00:00Z')).toBe(date.toLocaleDateString())
      expect(formatDate(date)).toBe(date.toLocaleDateString())
    })

    it('returns "Invalid date" and logs a warning when formatting throws', () => {
      const { formatDate } = useScopeUtils()
      const broken = {
        toLocaleDateString: () => {
          throw new Error('bad date')
        }
      } as unknown as Date

      expect(formatDate(broken)).toBe('Invalid date')
      expect(logService.warn).toHaveBeenCalledWith('Invalid date format', {
        date: broken,
        error: 'bad date'
      })
    })
  })

  describe('calculateProgress', () => {
    it('computes a rounded percentage', () => {
      const { calculateProgress } = useScopeUtils()

      expect(calculateProgress(7, 10)).toBe(70)
      expect(calculateProgress(1, 3)).toBe(33)
    })

    it('returns 0 for missing total, zero total or non-positive completed', () => {
      const { calculateProgress } = useScopeUtils()

      expect(calculateProgress(5, 0)).toBe(0)
      expect(calculateProgress(5, null)).toBe(0)
      expect(calculateProgress(0, 10)).toBe(0)
      expect(calculateProgress(-3, 10)).toBe(0)
      expect(calculateProgress(undefined, 10)).toBe(0)
    })

    it('caps progress at 100', () => {
      const { calculateProgress } = useScopeUtils()

      expect(calculateProgress(15, 10)).toBe(100)
    })
  })

  describe('visibility helpers', () => {
    it('returns icon and label for public and private scopes', () => {
      const { getScopeVisibilityIcon, getScopeVisibilityLabel } = useScopeUtils()

      expect(getScopeVisibilityIcon(true)).toBe('mdi-earth')
      expect(getScopeVisibilityIcon(false)).toBe('mdi-lock')
      expect(getScopeVisibilityLabel(true)).toBe('Public')
      expect(getScopeVisibilityLabel(false)).toBe('Private')
    })
  })

  describe('formatScopeName', () => {
    it('converts dashed names to title case', () => {
      const { formatScopeName } = useScopeUtils()

      expect(formatScopeName('kidney-genetics')).toBe('Kidney Genetics')
      expect(formatScopeName('neuro-oncology')).toBe('Neuro Oncology')
    })

    it('returns empty string for empty input', () => {
      const { formatScopeName } = useScopeUtils()

      expect(formatScopeName('')).toBe('')
      expect(formatScopeName(null)).toBe('')
    })
  })

  describe('isValidScopeName', () => {
    it.each([
      ['kidney-genetics', true],
      ['abc1', true],
      ['Kidney-Genetics', false],
      ['kidney_genetics', false],
      ['kid--genetics', false],
      ['ab', false],
      ['-kidney', false],
      ['', false],
      [null, false],
      [undefined, false]
    ])('isValidScopeName(%s) is %s', (name, expected) => {
      const { isValidScopeName } = useScopeUtils()

      expect(isValidScopeName(name)).toBe(expected)
    })
  })
})
