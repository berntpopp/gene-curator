import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ScoreSummary from '../ScoreSummary.vue'
import ScopeSummaryCard from '../ScopeSummaryCard.vue'
import CurationHeader from '../CurationHeader.vue'

describe('ScoreSummary', () => {
  it('shows the total with one decimal and the breakdown with two decimals', () => {
    const wrapper = mount(ScoreSummary, {
      props: {
        geneticScore: 7.5,
        experimentalScore: 2,
        totalScore: 9.5,
        classification: 'Strong',
        geneticBreakdown: { caseLevel: 4.5, segregation: 1, caseControl: 2 },
        experimentalBreakdown: { function: 1, functionalAlteration: 0, models: 1, rescue: 0 }
      }
    })
    expect(wrapper.find('.score-value').text()).toBe('9.5')
    expect(wrapper.text()).toContain('7.50')
    expect(wrapper.text()).toContain('2.00')
    expect(wrapper.text()).toContain('9.50')
    expect(wrapper.text()).toContain('4.50')
    expect(wrapper.find('.score-strong').exists()).toBe(true)
  })

  it('shows zero placeholders when a breakdown value is missing', () => {
    const wrapper = mount(ScoreSummary, {
      props: { geneticBreakdown: {}, experimentalBreakdown: {} }
    })
    expect(wrapper.text()).toContain('0.00')
  })

  it('warns about contradictory evidence only when flagged', () => {
    expect(mount(ScoreSummary).text()).not.toContain('Contradictory evidence present')
    const flagged = mount(ScoreSummary, { props: { hasContradictory: true } })
    expect(flagged.text()).toContain('Contradictory evidence present')
  })
})

describe('ScopeSummaryCard', () => {
  const summary = {
    scope_name: 'Hearing loss',
    classification: 'Definitive',
    genetic_score: 10,
    experimental_score: 2,
    total_score: 12,
    curator_count: 2,
    evidence_count: 5,
    last_updated: '2024-03-05T10:00:00Z',
    is_public: true
  }

  it('renders scores, counts and a formatted date', () => {
    const wrapper = mount(ScopeSummaryCard, { props: { scopeSummary: summary } })
    expect(wrapper.text()).toContain('Hearing loss')
    expect(wrapper.text()).toContain('10.00')
    expect(wrapper.text()).toContain('12.00')
    expect(wrapper.text()).toContain('2 curators')
    expect(wrapper.text()).toContain('5 evidence items')
    expect(wrapper.text()).toContain('Updated:')
    expect(wrapper.text()).not.toContain('Private')
  })

  it('marks non-public scopes as private and shows an em dash without a date', () => {
    const wrapper = mount(ScopeSummaryCard, {
      props: {
        scopeSummary: { ...summary, classification: null, is_public: false, last_updated: null }
      }
    })
    expect(wrapper.text()).toContain('Private')
    expect(wrapper.text()).toContain('Updated: —')
  })
})

describe('CurationHeader', () => {
  it.each([
    ['Autosomal dominant', 'AD'],
    ['ar', 'AR'],
    ['X-linked', 'X-linked'],
    ['Mitochondrial', 'MT'],
    ['Unknown', 'Unknown']
  ])('maps mode of inheritance %s to %s', (moi, display) => {
    const wrapper = mount(CurationHeader, { props: { moi } })
    expect(wrapper.text()).toContain(display)
  })

  it('shows gene, disease, status label and a truncated curation id', () => {
    const wrapper = mount(CurationHeader, {
      props: {
        gene: { approved_symbol: 'HNF1B', hgnc_id: 'HGNC:5024' },
        disease: { name: 'Renal cysts', mondo_id: 'MONDO:0000001' },
        status: 'in_review',
        curationId: '123e4567-e89b-12d3-a456-426614174000',
        expertPanel: 'Kidney GCEP'
      }
    })
    expect(wrapper.text()).toContain('HNF1B')
    expect(wrapper.text()).toContain('Renal cysts')
    expect(wrapper.text()).toContain('In review')
    expect(wrapper.text()).toContain('ID: 123e4567...')
    expect(wrapper.text()).toContain('Expert Panel: Kidney GCEP')
  })

  it('falls back to placeholders when no gene, disease or classification is set', () => {
    const wrapper = mount(CurationHeader)
    expect(wrapper.text()).toContain('Unknown')
    expect(wrapper.text()).toContain('Not specified')
    expect(wrapper.text()).toContain('Not Classified')
    expect(wrapper.text()).toContain('Draft')
  })
})
