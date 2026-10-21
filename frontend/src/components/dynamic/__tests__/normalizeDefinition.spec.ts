import { describe, it, expect } from 'vitest'
import { normalizeDefinition, normalizeField } from '../normalizeDefinition'
import { conditionHolds, resolveField } from '../conditions'
import { precurationSeed } from './precurationSeed'

describe('normalizeDefinition', () => {
  it('turns the seeded precuration sections into steps of field paths', () => {
    const doc = normalizeDefinition(precurationSeed)
    const tabs = doc.ui_configuration!.layout!.tabs!
    expect(tabs.map(t => t.name)).toEqual([
      'Disease Entity Definition',
      'Mode of Inheritance',
      'Lumping & Splitting',
      'Precuration Metadata'
    ])
    expect(tabs[1]!.sections[0]!.fields).toEqual(['mode_of_inheritance', 'moi_notes'])
    expect(doc.scoring_configuration).toBeUndefined()

    const p = doc.properties!
    expect(p.mondo_id).toMatchObject({
      type: 'string',
      title: 'Mondo Disease ID',
      component: 'MONDOAutocomplete',
      required: true
    })
    expect(p.disease_phenotypes!.component).toBe('HPOInput')
    expect(p.mode_of_inheritance).toMatchObject({
      type: 'string',
      enum: ['AD', 'AR', 'XLD', 'XLR', 'SD', 'MT', 'Other']
    })
    expect(p.mode_of_inheritance!.enumOptions![0]).toEqual({
      value: 'AD',
      label: 'Autosomal Dominant (HP:0000006)'
    })
    expect(p.moi_notes).toMatchObject({
      multiline: true,
      visible_when: { mode_of_inheritance: 'Other' }
    })
    expect(p.affiliation!.hint).toBe('Your ClinGen Expert Panel or curation group')
  })

  it('maps evidence tables, nested objects and seed vocabulary for curation config', () => {
    const doc = normalizeDefinition({
      field_definitions: {
        entity: {
          type: 'object',
          properties: {
            mondo_id: { type: 'string', readonly: true, validation: 'mondo_id_format' }
          }
        },
        segregation: {
          type: 'array',
          ui_component: 'EvidenceTable',
          item_schema: { lod_score: { type: 'number', min: 0, max: 5, step: 0.1 } }
        },
        refs: { type: 'array', item_schema: { pmid: { type: 'string', min_length: 1 } } }
      },
      ui_configuration: {
        layout: {
          type: 'tabs',
          tabs: [
            {
              id: 'a',
              name: 'A',
              sections: [
                { name: 'Score', component: 'ScoreSummary' },
                { name: 'S', fields: ['segregation'] }
              ]
            },
            {
              id: 'b',
              name: 'B',
              sections: [{ name: 'Lumping', component: 'LumpingSplittingSection' }]
            }
          ]
        }
      },
      scoring_configuration: { engine: 'clingen' }
    })
    const p = doc.properties!
    expect(p.entity!.properties!.mondo_id).toMatchObject({
      readOnly: true,
      pattern: '^MONDO:\\d{6,9}$'
    })
    expect(p.segregation).toMatchObject({
      type: 'evidence_table',
      columns: { lod_score: { minimum: 0, maximum: 5, step: 0.1 } }
    })
    expect(p.refs!.items!.properties!.pmid!.minLength).toBe(1)
    // component-only sections have no fields to render
    expect(doc.ui_configuration!.layout!.tabs!.map(t => t.sections.length)).toEqual([1, 0])
    expect(doc.scoring_configuration).toEqual({ engine: 'clingen' })
  })

  it('accepts a config already in FieldSchema vocabulary and no layout', () => {
    const doc = normalizeDefinition({
      field_definitions: { score: { type: 'number', title: 'Score', minimum: 1, enum: [1, 2] } }
    })
    expect(doc.properties!.score).toMatchObject({ title: 'Score', minimum: 1, enum: [1, 2] })
    expect(doc.ui_configuration).toBeUndefined()
    expect(normalizeDefinition({}).properties).toEqual({})
  })

  it('reads columns of an evidence_table field', () => {
    const field = normalizeField({
      type: 'evidence_table',
      columns: { pmid: { type: 'text', validation: 'pmid_format' } }
    })
    expect(field.columns!.pmid).toMatchObject({
      type: 'string',
      pattern: '^(PMID:?\\s*)?\\d{1,9}$'
    })
  })
})

describe('conditions', () => {
  const data = { moi: 'AR', nested: { flag: true } }

  it('supports equals, in and nested paths; all entries must hold', () => {
    expect(conditionHolds({ moi: 'AR' }, data)).toBe(true)
    expect(conditionHolds({ moi: ['AD', 'AR'] }, data)).toBe(true)
    expect(conditionHolds({ 'nested.flag': true, moi: 'AD' }, data)).toBe(false)
    expect(conditionHolds({ 'missing.path': true }, data)).toBe(false)
  })

  it('hides fields and resolves required_when', () => {
    expect(resolveField({ type: 'string', visible_when: { moi: 'AD' } }, data)).toBeNull()
    const plain = { type: 'string' }
    expect(resolveField(plain, data)).toBe(plain)
    expect(resolveField({ type: 'string', required_when: { moi: 'AR' } }, data)!.required).toBe(
      true
    )
    expect(resolveField({ type: 'string', required_when: { moi: 'AD' } }, data)!.required).toBe(
      false
    )
  })
})
