/** The synopsis of an active curation, when the API sends one (evidence visibility). */
import { describe, it, expect } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import GeneAssertions from '../GeneAssertions.vue'
import type { Schema } from '@/types/api'

const row = (synopsis: string | null): Schema<'ScopeSummary'> => ({
  scope_id: 's1',
  scope_name: 'kidney-genetics',
  scope_display_name: 'Kidney genetics',
  is_public: true,
  classification: 'definitive',
  curation_id: 'c1',
  synopsis,
  relationship_type: 'mendelian',
  in_progress: false,
  genetic_score: 1,
  experimental_score: 0,
  total_score: 1,
  last_updated: '2026-10-17T10:00:00Z',
  curator_count: 1,
  evidence_count: 1
})

describe('GeneAssertions synopsis', () => {
  it.each([
    ['CKD, adult onset', 1],
    [null, 0]
  ])('shows %s', (synopsis, rows) => {
    const w = mount(GeneAssertions, {
      props: { scopes: [row(synopsis)], linked: false },
      global: { stubs: { RouterLink: RouterLinkStub } }
    })
    expect(w.findAll('.assertions__synopsis')).toHaveLength(rows)
    if (synopsis) expect(w.text()).toContain(synopsis)
  })
})
