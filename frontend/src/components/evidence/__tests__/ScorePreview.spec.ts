/**
 * ScorePreview Tests
 *
 * Covers the live ClinGen SOP v11 preview: totals, classification,
 * evidence count messaging, detail toggle and the scorecard link.
 */
import { describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ScorePreview from '../ScorePreview.vue'

const genetic = (category: string, score: number) => ({
  evidence_type: 'genetic',
  evidence_category: category,
  computed_score: score
})

describe('ScorePreview', () => {
  it('shows the empty state with no evidence and a zero-score classification', () => {
    const wrapper = mount(ScorePreview)

    expect(wrapper.text()).toContain('No Known Disease Relationship')
    expect(wrapper.text()).toContain('No evidence items added yet')
    expect(wrapper.text()).toContain('0.00')
  })

  it('sums genetic and experimental evidence into a classified total', () => {
    const wrapper = mount(ScorePreview, {
      props: {
        evidenceItems: [
          genetic('case_level', 3),
          genetic('segregation', 2),
          { evidence_type: 'experimental', evidence_category: 'expression', computed_score: 1 }
        ]
      }
    })

    expect(wrapper.text()).toContain('6.00')
    expect(wrapper.text()).toContain('Moderate')
    expect(wrapper.text()).toContain('3 evidence items added')
    expect(wrapper.text()).not.toContain('Add more evidence for classification')
  })

  it('caps the genetic and experimental subtotals at their SOP maxima', () => {
    const wrapper = mount(ScorePreview, {
      props: {
        evidenceItems: [
          genetic('case_level', 20),
          { evidence_type: 'experimental', evidence_category: 'rescue', computed_score: 9 }
        ]
      }
    })

    expect(wrapper.text()).toContain('12.00')
    expect(wrapper.text()).toContain('Definitive')
    expect(wrapper.text()).toContain('18.00')
  })

  it('uses singular wording for one item and no "add more" hint at Strong or above', () => {
    const wrapper = mount(ScorePreview, {
      props: { evidenceItems: [genetic('case_level', 8)] }
    })

    expect(wrapper.text()).toContain('1 evidence item added')
    expect(wrapper.text()).toContain('Strong')
    expect(wrapper.text()).not.toContain('Add more evidence')
  })

  it('hides the detailed breakdown when showDetails is false', () => {
    const shown = mount(ScorePreview, { props: { evidenceItems: [genetic('case_level', 1)] } })
    const hidden = mount(ScorePreview, {
      props: { evidenceItems: [genetic('case_level', 1)], showDetails: false }
    })

    expect(shown.text()).toContain('Detailed Breakdown')
    expect(hidden.text()).not.toContain('Detailed Breakdown')
  })

  it('shows the scorecard action only when requested and emits view-full-score', async () => {
    const withoutLink = mount(ScorePreview)
    expect(withoutLink.text()).not.toContain('View Full Scorecard')

    const wrapper = mount(ScorePreview, { props: { showFullScoreLink: true } })
    const button = wrapper.findAll('button').find(b => b.text().includes('View Full Scorecard'))
    expect(button).toBeDefined()
    await button?.trigger('click')

    expect(wrapper.emitted('view-full-score')).toHaveLength(1)
  })

  it('expands the detailed breakdown into per-category scores', async () => {
    const wrapper = mount(ScorePreview, {
      props: { evidenceItems: [genetic('case_level', 1)] },
      attachTo: document.body
    })

    await wrapper.find('.v-expansion-panel-title').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Case-Level')
    expect(wrapper.text()).toContain('Rescue')
    wrapper.unmount()
  })
})
