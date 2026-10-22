import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import ScoreDisplay from '../ScoreDisplay.vue'
describe('ScoreDisplay', () => {
  it('uses the returned verdict even when configured thresholds disagree', () => {
    const w = mount(ScoreDisplay, {
      props: {
        scoreCalculations: { total_score: 0, verdict: 'Custom strong' },
        scoringConfiguration: { engine: 'custom', classification_thresholds: { Limited: 0 } }
      },
      global: { plugins: [createVuetify()] }
    })
    expect(w.text()).toContain('Custom strong')
    expect(w.text()).toContain('0.00')
    expect(w.text()).not.toContain('Limited')
    expect(w.text()).not.toContain('/ 18')
  })
  it('hides the old score while validating', () => {
    const w = mount(ScoreDisplay, {
      props: { loading: true, scoreCalculations: { total_score: 99, verdict: 'Stale' } },
      global: { plugins: [createVuetify()] }
    })
    expect(w.find('.v-skeleton-loader').exists()).toBe(true)
    expect(w.text()).not.toContain('Stale')
  })
})
