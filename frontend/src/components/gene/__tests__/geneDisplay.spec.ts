import { describe, it, expect } from 'vitest'
import {
  calculateProgress,
  getPriorityColor,
  getPriorityIcon,
  getPriorityLabel,
  getProgressColor,
  getStatusColor,
  getStatusLabel
} from '../geneDisplay'
import { CURATION_STATUS } from '@/config/status'

describe('geneDisplay', () => {
  describe('calculateProgress', () => {
    it.each([
      ['assigned', 0],
      ['in_progress', 25],
      ['in_review', 75],
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
      expect(getStatusLabel('in_review')).toBe('In review')
      expect(getStatusColor('in_review')).toBe('warning')
    })

    it('labels and colours every real CurationStatus like the shared status map', () => {
      for (const [value, { label, color }] of Object.entries(CURATION_STATUS)) {
        expect(getStatusLabel(value)).toBe(label)
        expect(getStatusColor(value)).toBe(color)
      }
    })

    it("reads 'Unassigned' for an assigned status without a curator", () => {
      expect(getStatusLabel('assigned', false)).toBe('Unassigned')
      expect(getStatusLabel('assigned', true)).toBe('Assigned')
      expect(getStatusLabel('in_progress', false)).toBe('In Progress')
    })

    it('falls back for unknown statuses', () => {
      expect(getStatusColor('mystery')).toBe('grey')
      expect(getStatusLabel('mystery')).toBe('mystery')
    })
  })

  describe('priority display', () => {
    it('maps high, medium and low priorities', () => {
      expect(getPriorityColor('high')).toBe('error')
      expect(getPriorityColor('medium')).toBe('warning')
      expect(getPriorityColor('low')).toBe('success')
      expect(getPriorityIcon('high')).toBe('mdi-flag')
      expect(getPriorityIcon('low')).toBe('mdi-flag-outline')
      expect(getPriorityLabel('medium')).toBe('Medium')
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
})
