import { describe, it, expect } from 'vitest'
import {
  CLASSIFICATIONS,
  classKey,
  classificationRank,
  compareClassifications,
  getClassification,
  registerClassifications
} from '../classification'

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

describe('schema-declared classifications (#539)', () => {
  it('render like their tone, rank by their order and leave ClinGen as is', () => {
    registerClassifications([
      { key: 'uncertain_risk', label: 'Uncertain association', order: 3, tone: 'limited' },
      { key: 'established_risk', label: 'Established association', order: 1, tone: 'strong' },
      { key: 'bad', label: 'Bad', order: 9, tone: 'red' }
    ])
    registerClassifications(undefined)
    expect(getClassification('Established_Risk')).toMatchObject({
      key: 'established_risk',
      label: 'Established association',
      color: 'cls-strong',
      bars: 3
    })
    expect(getClassification('bad').key).toBe('unknown')
    expect(['uncertain_risk', 'established_risk'].sort(compareClassifications)).toEqual([
      'established_risk',
      'uncertain_risk'
    ])
    expect(classificationRank('strong')).toBe(1)
    expect(classificationRank('whatever')).toBe(CLASSIFICATIONS.length)
    expect(getClassification('strong').label).toBe('Strong')
  })
})

describe('classKey (#539)', () => {
  it('replaces each space or hyphen like the backend class_key', () => {
    expect(classKey('Limited - Moderate')).toBe('limited___moderate')
    expect(classKey(' Strong  Association ')).toBe('strong__association')
    expect(classKey('No Known Disease Relationship')).toBe('no_known')
  })
})
