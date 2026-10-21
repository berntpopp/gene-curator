import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FAQ from '@/views/FAQ.vue'

describe('FAQ view', () => {
  it('renders one expansion panel per FAQ entry', () => {
    const wrapper = mount(FAQ)
    expect(wrapper.find('h1').text()).toBe('Frequently Asked Questions')
    expect(wrapper.findAll('.v-expansion-panel-title').length).toBe(11)
    expect(wrapper.text()).toContain('What is Gene Curator?')
  })

  it('gives each question a stable anchor id and renders no raw HTML', () => {
    const wrapper = mount(FAQ)
    expect(wrapper.find('#review-workflow').exists()).toBe(true)
    expect(wrapper.html()).not.toContain('<br')
    expect(wrapper.html()).not.toContain('bell icon')
  })
})

describe('FAQ answers', () => {
  it('lists the scope roles in a real list once the panel is opened', async () => {
    const wrapper = mount(FAQ)
    await wrapper.findAll('.v-expansion-panel-title')[1]!.trigger('click')
    const items = wrapper.findAll('ul li').map(li => li.text())
    expect(items).toContain('Reviewer: reviews curations submitted by others (4-eyes principle)')
    expect(items.length).toBe(4)
  })
})
