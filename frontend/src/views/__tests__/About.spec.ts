import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import About from '@/views/About.vue'

describe('About view', () => {
  it('describes the project for curators without architecture wording', () => {
    const wrapper = mount(About)
    expect(wrapper.find('h1').text()).toBe('Gene Curator')
    expect(wrapper.text()).toContain('Supported methodologies')
    expect(wrapper.text()).not.toContain('Vue.js')
    expect(wrapper.text()).not.toContain('architectural')
  })

  it('renders the methodology list as a real unordered list', () => {
    const wrapper = mount(About)
    expect(wrapper.findAll('ul li').length).toBe(3)
  })
})
