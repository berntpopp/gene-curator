import { describe, it, expect } from 'vitest'
import { CLASSIFICATIONS, getClassification } from '../classification'

describe('getClassification', () => {
  it.each(CLASSIFICATIONS.map(c => c.key))('resolves %s in both casings', key => {
    const info = getClassification(key)
    expect(info.key).toBe(key)
    expect(getClassification(info.label).key).toBe(key)
    expect(getClassification(info.label.toUpperCase()).key).toBe(key)
  })

  it('accepts the long no-known label', () => {
    expect(getClassification('No Known Disease Relationship').key).toBe('no_known')
  })

  it('strength falls from definitive to limited', () => {
    expect(
      ['definitive', 'strong', 'moderate', 'limited'].map(k => getClassification(k).bars)
    ).toEqual([4, 3, 2, 1])
  })

  it('maps unknown and empty values to neutral', () => {
    expect(getClassification('Weird')).toMatchObject({
      key: 'unknown',
      label: 'Weird',
      color: 'cls-no-known'
    })
    expect(getClassification(null)).toMatchObject({ key: 'unknown', bars: 0 })
  })
})
