import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FAQ from '@/views/FAQ.vue'

describe('FAQ view', () => {
  it('renders one expansion panel per FAQ entry', () => {
    const wrapper = mount(FAQ)
    expect(wrapper.find('h1').text()).toBe('Frequently Asked Questions')
    expect(wrapper.findAll('.v-expansion-panel-title').length).toBe(14)
    expect(wrapper.text()).toContain('What is Gene Curator?')
  })
})
