import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import ScoreSummary from '../ScoreSummary.vue'

describe('ScoreSummary thresholds panel', () => {
  it('lists the SOP v11 ranges', async () => {
    const wrapper = mount(ScoreSummary, { global: { plugins: [createVuetify()] } })
    await wrapper.find('.v-expansion-panel-title').trigger('click')
    const text = wrapper.text()
    expect(text).toContain('12-18 points + replication over time')
    expect(text).toContain('7-11 points')
    expect(text).toContain('1-6 points')
  })
})
