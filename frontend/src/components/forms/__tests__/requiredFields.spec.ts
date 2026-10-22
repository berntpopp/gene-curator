import { describe, it, expect } from 'vitest'
import { missingRequiredLabels, missingRequiredPaths } from '../requiredFields'
import cases from '@/components/dynamic/__tests__/conditionCases.json'

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

describe('missingRequiredLabels with conditional fields', () => {
  // Seeded lumping & splitting section: decision/rationale only when applicable is checked
  const lumping = {
    sections: [
      {
        id: 'lumping_splitting',
        fields: [
          { id: 'applicable', label: 'Applicable', type: 'boolean', required: true },
          { id: 'decision', label: 'Decision', required: true, show_when: { applicable: true } },
          {
            id: 'rationale',
            label: 'Rationale',
            required: true,
            visible_when: { applicable: true }
          }
        ]
      }
    ]
  }

  it('requires an answer to a required boolean and skips fields hidden by it', () => {
    expect(missingRequiredLabels(lumping, {})).toEqual(['Applicable'])
    expect(missingRequiredLabels(lumping, { applicable: false })).toEqual([])
  })

  it('requires the conditional fields once their condition holds', () => {
    expect(missingRequiredLabels(lumping, { applicable: true })).toEqual(['Decision', 'Rationale'])
    // strict equality, as the backend: a truthy non-boolean is not `true`
    expect(missingRequiredLabels(lumping, { applicable: 'true' })).toEqual([])
  })

  it('resolves paths listed only in required_fields against their field config', () => {
    const plain = {
      sections: [
        {
          id: 'l',
          fields: [
            { id: 'applicable', label: 'Applicable', type: 'boolean' },
            { id: 'decision', label: 'Decision', show_when: { applicable: true } }
          ]
        }
      ]
    }
    const rules = { required_fields: ['applicable', 'decision'] }
    expect(missingRequiredLabels(plain, {}, rules)).toEqual(['Applicable'])
    expect(missingRequiredLabels(plain, { applicable: true }, rules)).toEqual(['Decision'])
  })
})

// The shared table (#433): backend `missing_required_fields` runs the same cases
describe('missingRequiredPaths', () => {
  it.each(cases.required)('$name', ({ fields, data, missing, ...rest }) => {
    expect(missingRequiredPaths(fields, data, 'rules' in rest ? rest.rules : undefined)).toEqual(
      missing
    )
  })
})
