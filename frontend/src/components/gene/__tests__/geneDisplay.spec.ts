import { describe, it, expect } from 'vitest'
import {
  calculateProgress,
  formatDate,
  getPriorityColor,
  getPriorityIcon,
  getPriorityLabel,
  getProgressColor,
  getStatusColor,
  getStatusLabel
} from '../geneDisplay'

describe('geneDisplay', () => {
  describe('calculateProgress', () => {
    it.each([
      ['assigned', 0],
      ['in_progress', 25],
      ['under_review', 75],
      ['completed', 100]
    ])('maps status %s to %i percent', (status, expected) => {
      expect(calculateProgress({ status })).toBe(expected)
    })

    it('falls back to 0 for unknown or missing status', () => {
      expect(calculateProgress({ status: 'bogus' })).toBe(0)
      expect(calculateProgress({ status: null })).toBe(0)
      expect(calculateProgress({})).toBe(0)
    })
  })

  describe('status display', () => {
    it('colours and labels known statuses', () => {
      expect(getStatusColor('completed')).toBe('success')
      expect(getStatusColor('in_progress')).toBe('warning')
      expect(getStatusLabel('under_review')).toBe('Under Review')
    })

    it('falls back for unknown statuses', () => {
      expect(getStatusColor('mystery')).toBe('grey')
      expect(getStatusLabel('mystery')).toBe('mystery')
    })
  })

  describe('priority display', () => {
    it('maps high, medium/normal and low priorities', () => {
      expect(getPriorityColor('high')).toBe('error')
      expect(getPriorityColor('normal')).toBe('warning')
      expect(getPriorityIcon('high')).toBe('mdi-flag')
      expect(getPriorityIcon('low')).toBe('mdi-flag-outline')
      expect(getPriorityLabel('normal')).toBe('Medium')
      expect(getPriorityLabel('low')).toBe('Low')
    })

    it('falls back for unknown priorities', () => {
      expect(getPriorityColor('urgent')).toBe('grey')
      expect(getPriorityIcon('urgent')).toBe('mdi-flag-outline')
      expect(getPriorityLabel('urgent')).toBe('urgent')
    })
  })

  describe('getProgressColor', () => {
    it.each([
      [100, 'success'],
      [75, 'success'],
      [50, 'info'],
      [25, 'warning'],
      [0, 'grey'],
      [null, 'grey'],
      [undefined, 'grey']
    ])('progress %s -> %s', (progress, expected) => {
      expect(getProgressColor(progress)).toBe(expected)
    })
  })

  describe('formatDate', () => {
    it('shows a dash when there is no date', () => {
      expect(formatDate(null)).toBe('—')
      expect(formatDate(undefined)).toBe('—')
      expect(formatDate('')).toBe('—')
    })

    it('formats a date string with the locale date format', () => {
      expect(formatDate('2025-03-04T00:00:00Z')).toBe(
        new Date('2025-03-04T00:00:00Z').toLocaleDateString()
      )
    })
  })
})
