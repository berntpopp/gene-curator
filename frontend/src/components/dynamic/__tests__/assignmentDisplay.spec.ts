/**
 * Tests for the gene assignment display helpers.
 *
 * @see src/components/dynamic/assignmentDisplay.ts
 */

import { describe, it, expect } from 'vitest'
import { formatPriority, getPriorityColor, priorityOptions } from '../assignmentDisplay'

describe('assignmentDisplay', () => {
  it('lists priorities from low to urgent', () => {
    expect(priorityOptions.map(o => o.title)).toEqual(['Low', 'Medium', 'High', 'Urgent'])
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

  it('capitalises priorities', () => {
    expect(formatPriority('high')).toBe('High')
  })
})
