import { describe, it, expect } from 'vitest'
import {
  dropField,
  layoutSections,
  orderLayout,
  placeField,
  referencedIn,
  renameConditions,
  renameInLayout
} from '../layoutRefs'
import { readLayout, writeLayout } from '../fieldModel'

const ui = () => ({
  layout: {
    type: 'tabs',
    tabs: [
      {
        id: 'summary',
        name: 'Summary',
        sections: [
          { name: 'Classification', fields: ['evidence_summary'] },
          { name: 'Score', component: 'ScoreSummary' }
        ]
      },
      {
        id: 'genetic',
        name: 'Genetic',
        sections: [
          { name: 'Case level', fields: ['genetic.case_level', 'genetic.segregation', 'notes'] }
        ]
      }
    ]
  }
})

describe('layoutRefs', () => {
  it('lists the tab sections that place fields, skipping component-only ones', () => {
    expect(layoutSections(ui())).toEqual([
      {
        ref: { tab: 0, section: 0 },
        label: 'Summary › Classification',
        paths: ['evidence_summary']
      },
      {
        ref: { tab: 1, section: 0 },
        label: 'Genetic › Case level',
        paths: ['genetic.case_level', 'genetic.segregation', 'notes']
      }
    ])
    expect(layoutSections({})).toEqual([])
    expect(layoutSections(null)).toEqual([])
    expect(layoutSections({ layout: { tabs: [{ sections: 'x' }, 'bad'] } })).toEqual([])
  })

  it('places a new field in the given section, else the last; no layout is a no-op', () => {
    const u = ui()
    placeField(u, 'a', { tab: 0, section: 0 })
    placeField(u, 'b')
    expect(u.layout.tabs[0]!.sections[0]!.fields).toEqual(['evidence_summary', 'a'])
    expect(u.layout.tabs[1]!.sections[0]!.fields).toEqual([
      'genetic.case_level',
      'genetic.segregation',
      'notes',
      'b'
    ])
    const none = {}
    placeField(none, 'a')
    placeField(u, 'c', { tab: 5, section: 0 })
    expect(none).toEqual({})
  })

  it('drops and renames a field with its nested paths only', () => {
    const u = ui()
    renameInLayout(u, 'genetic', 'gen')
    expect(u.layout.tabs[1]!.sections[0]!.fields).toEqual([
      'gen.case_level',
      'gen.segregation',
      'notes'
    ])
    renameInLayout(u, 'gen.case', 'x') // not a whole segment
    dropField(u, 'gen')
    expect(u.layout.tabs[1]!.sections[0]!.fields).toEqual(['notes'])
  })

  it('orders a section by top-level ids, nested paths moving with their field', () => {
    const u = ui()
    orderLayout(u, { tab: 1, section: 0 }, ['notes', 'genetic'])
    expect(u.layout.tabs[1]!.sections[0]!.fields).toEqual([
      'notes',
      'genetic.case_level',
      'genetic.segregation'
    ])
    orderLayout(u, { tab: 0, section: 1 }, []) // component section: no-op
    expect(u.layout.tabs[0]!.sections[1]).toEqual({ name: 'Score', component: 'ScoreSummary' })
  })

  it('renames condition paths everywhere: sections, columns, nested properties', () => {
    const defs = {
      sections: [{ fields: [{ id: 'b', show_when: { moi: 'AD', other: 1 } }] }],
      table: { columns: { c: { visible_when: { 'moi.code': ['x'] } } } },
      group: { properties: { d: { required_when: { moi: true } } } },
      misc: { show_when: 'malformed' }
    }
    renameConditions(defs, 'moi', 'inheritance')
    expect(defs.sections[0]!.fields[0]!.show_when).toEqual({ inheritance: 'AD', other: 1 })
    expect(defs.table.columns.c.visible_when).toEqual({ 'inheritance.code': ['x'] })
    expect(defs.group.properties.d.required_when).toEqual({ inheritance: true })
    expect(defs.misc.show_when).toBe('malformed')
  })

  it('reports blocks mentioning an id as a whole path segment', () => {
    const blocks = {
      scoring_configuration: { types: [{ path: 'genetic.probands' }] },
      validation_rules: { rules: [{ field: 'probands_extra' }] },
      empty: null
    }
    expect(referencedIn(blocks, 'probands')).toEqual(['scoring_configuration'])
    expect(referencedIn(blocks, 'genetic')).toEqual(['scoring_configuration'])
    expect(referencedIn(blocks, 'a.b')).toEqual([])
  })

  it('groups a flat map by its layout and writes it back flat', () => {
    const defs = {
      evidence_summary: { type: 'textarea' },
      genetic: { type: 'object' },
      notes: { type: 'text' },
      loose: { type: 'text' }
    }
    const layout = readLayout(defs, ui())
    expect(layout.sectioned).toBe(false)
    expect(layout.sections.map(s => [s.label, s.layout, s.fields.map(f => f.id)])).toEqual([
      ['Summary › Classification', { tab: 0, section: 0 }, ['evidence_summary']],
      ['Genetic › Case level', { tab: 1, section: 0 }, ['genetic', 'notes']],
      ['Not in the layout', undefined, ['loose']]
    ])
    expect(writeLayout(layout, defs)).toEqual(defs)
  })
})
