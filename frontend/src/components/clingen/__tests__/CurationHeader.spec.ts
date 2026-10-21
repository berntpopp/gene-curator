import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import CurationHeader from '../CurationHeader.vue'

describe('CurationHeader schema caption', () => {
  it('shows the schema name and version from the curation schema', () => {
    const wrapper = mount(CurationHeader, {
      props: { schema: { name: 'Custom Schema', version: '2.1' } },
      global: { plugins: [createVuetify()] }
    })
    expect(wrapper.text()).toContain('Custom Schema v2.1')
  })

  it('shows no schema caption when no schema is in context', () => {
    const wrapper = mount(CurationHeader, { global: { plugins: [createVuetify()] } })
    expect(wrapper.text()).not.toContain(' v')
  })
})
