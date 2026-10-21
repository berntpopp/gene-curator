import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ScoreSummary from '../ScoreSummary.vue'
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

describe('CurationHeader', () => {
  it.each([
    ['AD', 'Autosomal dominant'],
    ['Autosomal dominant', 'Autosomal dominant'],
    ['ar', 'Autosomal recessive'],
    ['X-linked', 'X-linked'],
    ['MT', 'Mitochondrial'],
    ['Unknown', 'Unknown']
  ])('shows mode of inheritance %s as %s', (moi, display) => {
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
    expect(wrapper.text()).toContain('Not classified')
    expect(wrapper.text()).toContain('Draft')
  })
})
