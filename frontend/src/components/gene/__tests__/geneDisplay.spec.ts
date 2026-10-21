import { describe, it, expect } from 'vitest'
import { getPriorityColor, getPriorityLabel } from '../geneDisplay'

describe('geneDisplay', () => {
  it('maps high, medium and low priorities', () => {
    expect(getPriorityColor('high')).toBe('error')
    expect(getPriorityColor('medium')).toBe('warning')
    expect(getPriorityColor('low')).toBe('success')
    expect(getPriorityLabel('medium')).toBe('Medium')
    expect(getPriorityLabel('low')).toBe('Low')
  })

  it('falls back for unknown priorities', () => {
    expect(getPriorityColor('urgent')).toBe('grey')
    expect(getPriorityColor(null)).toBe('grey')
    expect(getPriorityLabel('urgent')).toBe('urgent')
  })
})
