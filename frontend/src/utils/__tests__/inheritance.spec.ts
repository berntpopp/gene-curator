import { describe, it, expect } from 'vitest'
import { formatInheritance, relationshipLabel } from '../inheritance'
import { label } from '@/views/curation/entityChoices'

describe('formatInheritance', () => {
  it.each([
    ['AD', 'Autosomal dominant'],
    ['xlr', 'X-linked recessive'],
    ['MT', 'Mitochondrial'],
    ['XL', 'X-linked'],
    ['SD', 'Semidominant'],
    ['Undetermined', 'Undetermined'],
    ['Autosomal dominant', 'Autosomal dominant'],
    ['', 'Unknown'],
    [undefined, 'Unknown']
  ])('%s -> %s', (moi, label) => {
    expect(formatInheritance(moi)).toBe(label)
  })
})

describe('relationshipLabel', () => {
  it('labels susceptibility only; Mendelian stays unlabelled', () => {
    expect(relationshipLabel('susceptibility')).toBe('Susceptibility')
    expect(relationshipLabel('mendelian')).toBe('')
    expect(relationshipLabel(undefined)).toBe('')
  })

  it('tells two entities of one MONDO id and MOI apart in the chooser', () => {
    const e = { disease_name: 'Foo', mondo_id: 'MONDO:1', mode_of_inheritance: 'AD' }
    expect(label({ ...e, relationship_type: 'mendelian' }, 'active')).toBe(
      'Foo · MONDO:1 · Autosomal dominant · active'
    )
    expect(label({ ...e, relationship_type: 'susceptibility' }, 'active')).toBe(
      'Foo · MONDO:1 · Autosomal dominant · Susceptibility · active'
    )
  })
})
