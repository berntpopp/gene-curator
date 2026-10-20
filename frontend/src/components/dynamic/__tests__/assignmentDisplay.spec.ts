/**
 * Tests for the gene assignment display helpers.
 *
 * @see src/components/dynamic/assignmentDisplay.ts
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import {
  formatDate,
  formatPriority,
  formatStatus,
  getDueDateClass,
  getDueDateStatus,
  getPriorityColor,
  getStatusColor,
  priorityOptions,
  statusOptions
} from '../assignmentDisplay'

const DAY_MS = 1000 * 60 * 60 * 24

describe('assignmentDisplay', () => {
  describe('options', () => {
    it('lists every assignment status once', () => {
      expect(statusOptions.map(o => o.value)).toEqual([
        'unassigned',
        'assigned',
        'in_progress',
        'under_review',
        'completed',
        'on_hold'
      ])
    })

    it('lists priorities from low to urgent', () => {
      expect(priorityOptions.map(o => o.title)).toEqual(['Low', 'Medium', 'High', 'Urgent'])
    })
  })

  describe('getStatusColor', () => {
    it('maps known statuses to their colour', () => {
      expect(getStatusColor('completed')).toBe('success')
      expect(getStatusColor('on_hold')).toBe('orange')
    })

    it('falls back to grey for unknown statuses', () => {
      expect(getStatusColor('something_else')).toBe('grey')
    })
  })

  describe('getPriorityColor', () => {
    it('maps known priorities to their colour', () => {
      expect(getPriorityColor('urgent')).toBe('deep-purple')
      expect(getPriorityColor('low')).toBe('green')
    })

    it('falls back to grey for missing or unknown priorities', () => {
      expect(getPriorityColor(undefined)).toBe('grey')
      expect(getPriorityColor(null)).toBe('grey')
      expect(getPriorityColor('bogus')).toBe('grey')
    })
  })

  describe('formatStatus and formatPriority', () => {
    it('turns snake_case status into Title Case', () => {
      expect(formatStatus('in_progress')).toBe('In Progress')
      expect(formatStatus('assigned')).toBe('Assigned')
    })

    it('capitalises the first letter of a priority', () => {
      expect(formatPriority('high')).toBe('High')
    })
  })

  describe('formatDate', () => {
    it('formats an ISO date with the locale date string', () => {
      expect(formatDate('2026-03-15T00:00:00Z')).toBe(
        new Date('2026-03-15T00:00:00Z').toLocaleDateString()
      )
    })
  })

  describe('due dates', () => {
    beforeEach(() => {
      vi.useFakeTimers()
      vi.setSystemTime(new Date('2026-06-10T12:00:00Z'))
    })

    afterEach(() => {
      vi.useRealTimers()
    })

    it('reports overdue dates in red with the number of days', () => {
      const due = new Date(Date.now() - 3 * DAY_MS).toISOString()
      expect(getDueDateClass(due)).toBe('text-error')
      expect(getDueDateStatus(due)).toBe('3 days overdue')
    })

    it('reports dates due within a week as a warning', () => {
      const due = new Date(Date.now() + 3 * DAY_MS).toISOString()
      expect(getDueDateClass(due)).toBe('text-warning')
      expect(getDueDateStatus(due)).toBe('3 days remaining')
    })

    it('reports dates a week or more away as success', () => {
      const due = new Date(Date.now() + 10 * DAY_MS).toISOString()
      expect(getDueDateClass(due)).toBe('text-success')
      expect(getDueDateStatus(due)).toBe('10 days remaining')
    })

    it('uses dedicated wording for today and tomorrow', () => {
      const today = new Date(Date.now()).toISOString()
      expect(getDueDateStatus(today)).toBe('Due today')

      const tomorrow = new Date(Date.now() + DAY_MS).toISOString()
      expect(getDueDateStatus(tomorrow)).toBe('Due tomorrow')
    })
  })
})
