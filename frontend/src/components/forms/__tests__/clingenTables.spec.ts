/**
 * The seeded ClinGen evidence tables, rendered from the pinned v1 config (after the 046
 * correction), keep the columns and new-row values of the hand-written form they replace.
 * Fixture: the ClinGen_SOP_v11 v1 snapshot (field_definitions, ui_configuration) of a fresh
 * database built from database/sql.
 */
import { describe, it, expect } from 'vitest'
import { normalizeDefinition } from '@/components/dynamic/normalizeDefinition'
import { emptyValue } from '@/components/dynamic/componentRegistry'
import type { FieldSchema } from '@/components/dynamic/types'
import snapshot from './clingenV1Snapshot.json'
import { TODAY_TABLES } from './clingenTodayTables'

const doc = normalizeDefinition(snapshot)

function field(path: string): FieldSchema {
  const [first, ...rest] = path.split('.')
  return rest.reduce<FieldSchema>((f, key) => f.properties![key]!, doc.properties![first!]!)
}

const kind = (c: FieldSchema) =>
  c.format === 'pmid' ? 'pmid' : c.enum ? 'select' : c.type === 'number' ? 'number' : 'text'

describe('ClinGen evidence tables from the pinned config', () => {
  it.each(Object.keys(TODAY_TABLES))('%s keeps the columns users had', path => {
    const table = field(path)
    expect(table.type).toBe('evidence_table')
    const columns = Object.entries(table.columns ?? {}).map(([key, c]) => ({
      key,
      label: c.title,
      type: kind(c),
      ...(c.enum && { options: c.enum }),
      ...(c.minimum !== undefined && { min: c.minimum }),
      ...(c.maximum !== undefined && { max: c.maximum })
    }))
    expect(columns).toEqual(TODAY_TABLES[path]!.columns)
  })

  it.each(Object.keys(TODAY_TABLES))('%s starts a new row with the same values', path => {
    const columns = field(path).columns ?? {}
    const row = Object.fromEntries(Object.entries(columns).map(([k, c]) => [k, emptyValue(c)]))
    expect(row).toEqual(TODAY_TABLES[path]!.newRow)
  })

  it('lays the tables out in the ClinGen steps, with the score and lumping sections', () => {
    const tabs = doc.ui_configuration!.layout!.tabs!
    expect(tabs.map(t => t.id)).toEqual([
      'summary',
      'genetic',
      'experimental',
      'contradictory',
      'lumping'
    ])
    expect(tabs.flatMap(t => t.sections.map(s => s.component).filter(Boolean))).toEqual([
      'ScoreSummary',
      'LumpingSplittingSection'
    ])
  })
})
