import { describe, it, expect } from 'vitest'
import {
  groupDiff,
  itemKey,
  itemLabel,
  itemState,
  formatValue,
  approveBlockers,
  queryTodos,
  checklistFor,
  REVIEW_TEXT_MAX
} from '../reviewModel'
import type { Schema } from '@/types/api'

type Item = Schema<'DiffItem'>
type Comment = Schema<'ReviewComment'>

const c = (o: Partial<Comment>): Comment => ({
  id: `c${Math.random()}`,
  curation_id: 'cur',
  review_id: null,
  item_path: 'genetic_evidence.case_level[a]',
  body: '',
  author_id: 'bob',
  status: 'open',
  kind: 'query',
  created_at: '2026-10-20T10:00:00Z',
  updated_at: '2026-10-20T10:00:00Z',
  ...o
})

describe('itemKey / itemLabel', () => {
  it('groups fields of a list record under the record, scalars stay their own item', () => {
    expect(itemKey('genetic_evidence.case_level[a1].points')).toBe(
      'genetic_evidence.case_level[a1]'
    )
    expect(itemKey('genetic_evidence.case_level[a1]')).toBe('genetic_evidence.case_level[a1]')
    expect(itemKey('evidence_summary')).toBe('evidence_summary')
  })

  it('makes readable labels without raw paths, naming the enclosing section', () => {
    expect(itemLabel('genetic_evidence.case_level[a1]')).toBe('Case level (Genetic evidence)')
    expect(itemLabel('evidence_summary')).toBe('Evidence summary')
    const key =
      'genetic_evidence.case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null[0]'
    expect(itemLabel(key)).toBe('Predicted or proven null #1 (Autosomal dominant or X-linked)')
    const evidence = {
      genetic_evidence: {
        case_level: {
          autosomal_dominant_or_x_linked: { predicted_or_proven_null: [{ proband_label: 'C1' }] }
        }
      }
    }
    expect(itemLabel(key, { evidence })).toBe(
      'Predicted or proven null · C1 (Autosomal dominant or X-linked)'
    )
  })

  it('spells domain abbreviations in fallback labels, schema titles win', () => {
    expect(itemLabel('g.pmid')).toBe('PMID (G)')
    expect(itemLabel('hpo_terms')).toBe('HPO terms')
    expect(itemLabel('mondo_id')).toBe('MONDO ID')
    expect(itemLabel('omim_hgnc_lod_score')).toBe('OMIM HGNC LOD score')
    expect(itemLabel('identity')).toBe('Identity')
    expect(itemLabel('pmid', { fields: { pmid: { title: 'PubMed' } } })).toBe('PubMed')
  })
})

describe('groupDiff', () => {
  const items: Item[] = [
    { path: 'g.cases[a].points', change: 'changed', before: 1.5, after: 2 },
    { path: 'g.cases[a].explanation', change: 'added', before: null, after: 'splice assay' },
    { path: 'g.cases[b]', change: 'added', before: null, after: { pmid: '1' } },
    { path: 'summary', change: 'changed', before: 'x', after: 'y' }
  ]
  const groups = groupDiff(items)

  it('collects field rows per item in first-seen order', () => {
    expect(groups.map(g => g.key)).toEqual(['g.cases[a]', 'g.cases[b]', 'summary'])
    expect(groups[0]!.fields.map(f => f.name)).toEqual(['points', 'explanation'])
  })

  it('classifies an item as added, removed or changed', () => {
    expect(groups[0]!.change).toBe('changed')
    expect(groups[1]!.change).toBe('added')
    expect(groups[1]!.fields[0]!.name).toBe('pmid') // an added record is listed by field
  })
})

describe('groupDiff, first review (whole sections added)', () => {
  const section = {
    case_level: { ad: { null_variants: [{ proband: 'P1', pmid: '123', points: 99 }], other: [] } },
    summary: 'text',
    empty: [],
    tags: ['a', 'b']
  }

  it('splits an added section into its records and scalars, filled leaves only', () => {
    const groups = groupDiff([
      { path: 'genetic_evidence', change: 'added', before: null, after: section }
    ])
    expect(groups.map(g => g.key)).toEqual([
      'genetic_evidence.case_level.ad.null_variants[0]',
      'genetic_evidence.summary',
      'genetic_evidence.tags'
    ])
    expect(groups[0]!.change).toBe('added')
    expect(groups[0]!.fields.map(f => [f.name, f.after])).toEqual([
      ['proband', 'P1'],
      ['pmid', '123'],
      ['points', 99]
    ])
    expect(groups[2]!.fields).toEqual([
      { name: '', label: '', change: 'added', before: undefined, after: 'a, b' }
    ])
    expect(groups.flatMap(g => g.fields).every(f => f.before === undefined)).toBe(true)
  })

  it('shows removed sections as rows of their old values', () => {
    const [g] = groupDiff([{ path: 's', change: 'removed', before: { a: 1 }, after: null }])
    expect(g!.key).toBe('s.a')
    expect(g!.fields).toEqual([
      { name: '', label: '', change: 'removed', before: 1, after: undefined }
    ])
  })

  // #406: a first submission lists empty sections as added; there is nothing to review in them
  it('drops an empty value added, keeps one "none" row for an empty record removed', () => {
    const groups = groupDiff([
      { path: 'contradictory_evidence', change: 'added', before: null, after: [] },
      { path: 'g.cases[r9]', change: 'removed', before: { id: 'r9', note: '' }, after: null }
    ])
    expect(groups.map(g => [g.key, g.change, g.fields])).toEqual([
      [
        'g.cases[r9]',
        'removed',
        [{ name: '', label: '', change: 'removed', before: 'none', after: undefined }]
      ]
    ])
  })
})

describe('groupDiff, records with ids (same keys as the backend in later rounds)', () => {
  const round1 = groupDiff([
    {
      path: 'g',
      change: 'added',
      before: null,
      after: {
        cases: [
          { id: 'u1', proband_label: 'C1', pmid: '1' },
          { id: 'u2', proband_label: 'C2', pmid: '2' }
        ],
        plain: [{ pmid: '3' }]
      }
    }
  ])
  const round2 = groupDiff([
    { path: 'g.cases[u1].pmid', change: 'changed', before: '1', after: '9' }
  ])

  it('keys records by id, like the backend diff, and hides the id row', () => {
    expect(round1.map(g => g.key)).toEqual(['g.cases[u1]', 'g.cases[u2]', 'g.plain[0]'])
    expect(round1[0]!.key).toBe(round2[0]!.key)
    expect(round1[0]!.fields.map(f => f.name)).toEqual(['proband_label', 'pmid'])
    expect(round1[0]!.label).toBe('Cases · C1')
  })

  it('keeps a round-1 open query blocking approval in round 2', () => {
    const query = c({ item_path: round1[0]!.key, body: 'Which transcript?' })
    expect(approveBlockers(round2, [query], 'bob').map(g => g.key)).toEqual(['g.cases[u1]'])
  })

  it('says whether a blocker is queried or just not accepted yet', () => {
    const query = c({ item_path: 'g.cases[u1]', body: 'Which transcript?' })
    expect(approveBlockers(round1, [query], 'bob').map(g => [g.key, g.queried])).toEqual([
      ['g.cases[u1]', true],
      ['g.cases[u2]', false],
      ['g.plain[0]', false]
    ])
  })

  it('names an id-keyed record from the evidence, numeric ids included', () => {
    const evidence = {
      g: {
        cases: [
          { id: 'u1', proband_label: 'C1' },
          { id: 0, label: 'Zero' }
        ]
      }
    }
    expect(itemLabel('g.cases[u1]', { evidence })).toBe('Cases · C1 (G)')
    expect(itemLabel('g.cases[0]', { evidence })).toBe('Cases · Zero (G)')
  })
})

describe('groupDiff, readable names', () => {
  const pnull = 'case_level.autosomal_dominant_or_x_linked.predicted_or_proven_null'
  const fields = {
    genetic_evidence: {
      properties: {
        case_level: {
          properties: {
            autosomal_dominant_or_x_linked: {
              title: 'Autosomal dominant or X-linked',
              properties: {
                predicted_or_proven_null: {
                  title: 'Predicted or proven null variant',
                  item_schema: {
                    proband_label: { type: 'string' },
                    pmid: { title: 'PMID' },
                    variant_type: {
                      options: [{ value: 'nonsense', label: 'Nonsense' }, 'frameshift']
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }

  it('names a record by the schema title and its label field, fields by schema or key', () => {
    const [g] = groupDiff(
      [
        {
          path: 'genetic_evidence',
          change: 'added',
          before: null,
          after: {
            [pnull.split('.')[0]!]: {
              autosomal_dominant_or_x_linked: {
                predicted_or_proven_null: [
                  {
                    pmid: '1',
                    proband_label: 'C1',
                    variant_type: 'nonsense',
                    proband_counted_points: 1.5
                  }
                ]
              }
            }
          }
        }
      ],
      { fields }
    )
    expect(g!.label).toBe('Predicted or proven null variant · C1')
    expect(g!.context).toBe('Genetic evidence › Case level › Autosomal dominant or X-linked')
    expect(g!.fields.map(f => f.label)).toEqual([
      'PMID',
      'Proband label',
      'Variant type',
      'Proband counted points'
    ])
    expect(g!.fields[2]!.options).toHaveLength(2)
  })

  it('names a changed record from the current evidence, else by its position', () => {
    const items: Item[] = [
      { path: `genetic_evidence.${pnull}[0].pmid`, change: 'changed', before: '1', after: '2' },
      { path: 'g.cases[3].x', change: 'changed', before: 1, after: 2 },
      { path: 'g.cases[abc].x', change: 'changed', before: 1, after: 2 }
    ]
    const evidence = {
      genetic_evidence: {
        case_level: {
          autosomal_dominant_or_x_linked: { predicted_or_proven_null: [{ proband_label: 'C7' }] }
        }
      },
      g: { cases: [{ id: 'abc', label: 'Mouse' }] }
    }
    expect(groupDiff(items, { fields, evidence }).map(g => g.label)).toEqual([
      'Predicted or proven null variant · C7',
      'Cases #4',
      'Cases · Mouse'
    ])
    expect(groupDiff(items).map(g => g.label)).toEqual([
      'Predicted or proven null #1',
      'Cases #4',
      'Cases'
    ])
  })
})

describe('evidence table options (monkey R2-7)', () => {
  it('offers an evidence table column its option labels', () => {
    const fields = {
      genetic: {
        properties: {
          probands: {
            type: 'evidence_table',
            columns: {
              zygosity: {
                label: 'Zygosity',
                options: [{ value: 'compound_heterozygous', label: 'Compound heterozygous' }]
              }
            }
          }
        }
      }
    }
    const items = [
      { path: 'genetic.probands[0]', change: 'added', after: { zygosity: 'compound_heterozygous' } }
    ] as Item[]
    const field = groupDiff(items, { fields })[0]!.fields[0]!
    expect(formatValue(field.after, field.options)).toBe('Compound heterozygous')
  })

  it('labels a select inside nested objects (KGDB mane_status, monkey R3-2)', () => {
    const fields = {
      diagnostics: {
        type: 'object',
        properties: {
          recommended_transcript: {
            type: 'object',
            properties: {
              mane_status: {
                type: 'select',
                options: [{ value: 'select', label: 'MANE Select' }]
              }
            }
          }
        }
      }
    }
    const items = [
      {
        path: 'diagnostics.recommended_transcript.mane_status',
        change: 'changed',
        before: null,
        after: 'select'
      }
    ] as Item[]
    const field = groupDiff(items, { fields })[0]!.fields[0]!
    expect(formatValue(field.after, field.options)).toBe('MANE Select')
  })
})

describe('formatValue', () => {
  it('renders scalars, objects and nothing', () => {
    expect(formatValue(null)).toBe('—') // an empty cell shows a dash (monkey R2-7)
    expect(formatValue(undefined)).toBe('—')
    expect(formatValue(2)).toBe('2')
    expect(formatValue('abc')).toBe('abc')
    expect(formatValue({ a: 1 })).toBe('{"a":1}')
  })

  it('uses enum labels from the schema and Yes/No', () => {
    const options = [{ value: 'nonsense', label: 'Nonsense' }, 'frameshift']
    expect(formatValue('nonsense', options)).toBe('Nonsense')
    expect(formatValue('frameshift', options)).toBe('frameshift')
    expect(formatValue(true)).toBe('Yes')
    expect(formatValue(false)).toBe('No')
    expect(formatValue('')).toBe('—')
  })
})

describe('itemState', () => {
  const path = 'g.cases[a]'
  it('is unreviewed without comments', () => {
    expect(itemState([], path, 'bob')).toEqual({
      status: 'unreviewed',
      queries: [],
      accepted: null
    })
  })

  it('is accepted by my open accepted row, ignoring other reviewers and withdrawn ones', () => {
    const mine = c({ item_path: path, kind: 'accepted' })
    expect(itemState([mine], path, 'bob').status).toBe('accepted')
    expect(
      itemState([c({ item_path: path, kind: 'accepted', author_id: 'carl' })], path, 'bob').status
    ).toBe('unreviewed')
    expect(itemState([{ ...mine, status: 'resolved' }], path, 'bob').status).toBe('unreviewed')
  })

  it('is queried while a query is open, answered once all are resolved', () => {
    const open = c({ item_path: path })
    expect(itemState([open], path, 'bob').status).toBe('queried')
    expect(itemState([{ ...open, status: 'resolved' }], path, 'bob').status).toBe('answered')
  })
})

describe('approveBlockers', () => {
  const groups = groupDiff([
    { path: 'g.a[1].x', change: 'changed', before: 1, after: 2 },
    { path: 'g.b[2]', change: 'added', before: null, after: 1 }
  ])
  it('lists items that are neither accepted nor resolved', () => {
    expect(approveBlockers(groups, [], 'bob')).toHaveLength(2)
    const comments = [c({ item_path: 'g.a[1]', kind: 'accepted' }), c({ item_path: 'g.b[2]' })]
    expect(approveBlockers(groups, comments, 'bob').map(b => b.key)).toEqual(['g.b[2]'])
    expect(
      approveBlockers(groups, [comments[0]!, { ...comments[1]!, status: 'resolved' }], 'bob')
    ).toEqual([])
  })
})

describe('queryTodos', () => {
  it('turns open queries into a to-do list for the curator', () => {
    const text = queryTodos('alice', [
      c({ item_path: 'g.a[1]', body: 'Check gnomAD' }),
      c({ item_path: 'g.a[1]', body: 'resolved one', status: 'resolved' }),
      c({ item_path: 'summary', body: 'Explain' }),
      c({ item_path: 'g.b[2]', kind: 'accepted' }),
      c({ item_path: 'g.a[1]', body: 'Added the segregation data', author_id: 'alice' })
    ])
    expect(text).toBe('- A #2 (G): Check gnomAD\n- Summary: Explain')
  })
  it('names items from the schema and evidence when given', () => {
    const text = queryTodos('alice', [c({ item_path: 'g.a[0]', body: 'Why?' })], {
      fields: { g: { title: 'Genetic', properties: { a: { title: 'Cases' } } } },
      evidence: { g: { a: [{ label: 'Fam 1' }] } }
    })
    expect(text).toBe('- Cases · Fam 1 (Genetic): Why?')
  })
  it('is empty without open queries', () => {
    expect(queryTodos('alice', [])).toBe('')
  })
  it('never exceeds the feedback limit, and says how many queries did not fit', () => {
    const many = Array.from({ length: 40 }, (_, i) =>
      c({ item_path: 'summary', body: `Question ${i} ${'x'.repeat(100)}` })
    )
    const text = queryTodos('alice', many)
    expect(text.length).toBeLessThanOrEqual(REVIEW_TEXT_MAX)
    expect(text).toMatch(/- …and \d+ more open quer(y|ies)/)
    const huge = queryTodos('alice', [c({ item_path: 'summary', body: 'y'.repeat(5000) })])
    expect(huge.length).toBeLessThanOrEqual(REVIEW_TEXT_MAX)
    expect(huge.endsWith('…')).toBe(true)
  })
})

describe('checklistFor', () => {
  it('adds the replication check for Definitive only', () => {
    expect(checklistFor('Strong').map(i => i.id)).toEqual([
      'publication',
      'points',
      'contradictory'
    ])
    expect(checklistFor('Definitive').map(i => i.id)).toContain('replication')
  })
})
