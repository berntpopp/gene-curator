/**
 * Tests for the gene assignment display helpers.
 *
 * @see src/components/dynamic/assignmentDisplay.ts
 */

import { describe, it, expect } from 'vitest'
import { formatPriority, getPriorityColor, priorityOptions } from '../assignmentDisplay'

describe('assignmentDisplay', () => {
  it('only offers priorities the backend accepts', () => {
    expect(priorityOptions.map(o => o.title)).toEqual(['Low', 'Medium', 'High'])
  })

  describe('getPriorityColor', () => {
    it('maps known priorities to their colour', () => {
      expect(getPriorityColor('urgent')).toBe('grey')
      expect(getPriorityColor('low')).toBe('success')
    })

    it('falls back to grey for missing or unknown priorities', () => {
      expect(getPriorityColor(undefined)).toBe('grey')
      expect(getPriorityColor(null)).toBe('grey')
      expect(getPriorityColor('bogus')).toBe('grey')
    })
  })

  it('capitalises priorities', () => {
    expect(formatPriority('high')).toBe('High')
  })
})
