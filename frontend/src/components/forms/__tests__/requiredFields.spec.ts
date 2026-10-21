import { describe, it, expect } from 'vitest'
import { missingRequiredLabels } from '../requiredFields'

// Shape of the seeded "ClinGen Precuration" schema (016_seed_precuration_schema.sql)
const sections = {
  sections: [
    {
      id: 'disease_entity',
      fields: [
        { id: 'mondo_id', label: 'Mondo Disease ID', required: true },
        { id: 'notes', label: 'Notes', required: false }
      ]
    },
    { id: 'metadata', fields: [{ id: 'affiliation', label: 'Affiliation', required: true }] }
  ]
}
const rules = { required_fields: ['mondo_id', 'disease_name', 'mode_of_inheritance'] }

describe('missingRequiredLabels', () => {
  it('blocks an empty submit against the seeded sections schema', () => {
    expect(missingRequiredLabels(sections, {}, rules)).toEqual([
      'Mondo Disease ID',
      'Affiliation',
      'Disease name',
      'Mode of inheritance'
    ])
  })

  it('passes once every required field is filled', () => {
    const data = {
      mondo_id: 'MONDO:1',
      affiliation: 'a',
      disease_name: 'd',
      mode_of_inheritance: 'x'
    }
    expect(missingRequiredLabels(sections, data, rules)).toEqual([])
  })

  it('still reads the flat and nested shape', () => {
    const flat = { a: { type: 'object', properties: { b: { required: true, label: 'B' } } } }
    expect(missingRequiredLabels(flat, { a: {} })).toEqual(['B'])
  })
})
