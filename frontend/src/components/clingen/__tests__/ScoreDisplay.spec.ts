import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ScoreSummary from '../ScoreSummary.vue'
import ClinGenScoreCard from '../ClinGenScoreCard.vue'
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

describe('ClinGenScoreCard', () => {
  const base = {
    classification: 'Moderate',
    total_score: 3,
    genetic_total: 2,
    experimental_total: 1
  }

  it('caps category scores at the SOP maxima and shows the rounded percentage', () => {
    const wrapper = mount(ClinGenScoreCard, {
      props: {
        breakdown: {
          ...base,
          total_score: 18,
          genetic_total: 12,
          experimental_total: 6,
          case_level_score: 40,
          segregation_score: 9,
          case_control_score: 9,
          expression_score: 5,
          function_score: 5,
          models_score: 9,
          rescue_score: 9
        }
      }
    })
    expect(wrapper.text()).toContain('18.00')
    expect(wrapper.text()).toContain('100%')
    expect(wrapper.text()).toContain('12.00')
    expect(wrapper.text()).toContain('6.00')
    expect(wrapper.text()).not.toContain('insufficient evidence')
  })

  it('shows category breakdown values, capped per SOP, once the panels are expanded', async () => {
    const wrapper = mount(ClinGenScoreCard, {
      props: {
        breakdown: {
          ...base,
          case_level_score: 14,
          segregation_score: 2,
          case_control_score: 1,
          expression_score: 1,
          function_score: 3,
          models_score: 2,
          rescue_score: 0
        }
      }
    })
    for (const title of wrapper.findAll('.v-expansion-panel-title')) await title.trigger('click')
    expect(wrapper.text()).toContain('Case-Level Evidence')
    expect(wrapper.text()).toContain('Maximum 12 points')
    // Function is capped at its SOP maximum of 2 even though the payload says 3.
    expect(wrapper.text()).toContain('Protein Function Evidence')
    expect(wrapper.text()).toContain('2.00')
  })

  it('reports insufficient evidence below 0.1 points and no Definitive banner', () => {
    const wrapper = mount(ClinGenScoreCard, {
      props: { breakdown: { total_score: 0, classification: 'No Known Disease Relationship' } }
    })
    expect(wrapper.text()).toContain('insufficient evidence')
    expect(wrapper.text()).not.toContain('Definitive classification achieved')
  })

  it('shows the Definitive banner for a Definitive classification', () => {
    const wrapper = mount(ClinGenScoreCard, {
      props: { breakdown: { ...base, total_score: 12, classification: 'Definitive' } }
    })
    expect(wrapper.text()).toContain('Definitive classification achieved')
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

  it('marks non-public scopes as private and shows N/A without a date', () => {
    const wrapper = mount(ScopeSummaryCard, {
      props: {
        scopeSummary: { ...summary, classification: null, is_public: false, last_updated: null }
      }
    })
    expect(wrapper.text()).toContain('Private')
    expect(wrapper.text()).toContain('N/A')
    expect(wrapper.text()).toContain('N/A')
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
    expect(wrapper.text()).toContain('In Review')
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
