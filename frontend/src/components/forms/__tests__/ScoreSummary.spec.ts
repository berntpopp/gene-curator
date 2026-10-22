import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import ScoreSummary from '../ScoreSummary.vue'
describe('ScoreSummary', () => {
  it('renders qualitative scores without inventing a total or a breakdown', () => {
    const w = mount(ScoreSummary, {
      props: { scores: { total: null, trace: null }, classification: 'Supportive' },
      global: { plugins: [createVuetify()] }
    })
    expect(w.text()).toContain('Supportive')
    expect(w.text()).toContain('Unavailable')
    expect(w.text()).toContain('Score breakdown unavailable')
    expect(w.text()).not.toContain('0.00')
  })
})
