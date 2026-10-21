import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FAQ from '@/views/FAQ.vue'

describe('FAQ view', () => {
  it('renders one expansion panel per FAQ entry', () => {
    const wrapper = mount(FAQ)
    expect(wrapper.find('h1').text()).toBe('Frequently Asked Questions')
    expect(wrapper.findAll('.v-expansion-panel-title').length).toBe(12)
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

describe('FAQ accuracy', () => {
  it('points reviewers to the Review Queue', async () => {
    const wrapper = mount(FAQ)
    await wrapper.find('#review-workflow .v-expansion-panel-title').trigger('click')
    expect(wrapper.text()).toContain('/review-queue')
  })

  it('explains the ClinGen point bands and Disputed', async () => {
    const wrapper = mount(FAQ)
    await wrapper.find('#clingen-classification .v-expansion-panel-title').trigger('click')
    const text = wrapper.text()
    expect(text).toContain('Limited is 1 to 6 points')
    expect(text).toContain('Disputed')
  })

  it('describes assignment edits and approval accurately', async () => {
    const wrapper = mount(FAQ)
    for (const title of wrapper.findAll('.v-expansion-panel-title')) await title.trigger('click')
    const html = wrapper.html()
    expect(html).toContain('priority, due date and notes')
    expect(html).not.toContain('priority only')
    expect(html).not.toContain('Start Curation becomes available')
    expect(html).toContain('curation draft is created automatically')
  })
})
