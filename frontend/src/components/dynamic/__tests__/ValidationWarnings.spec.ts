import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ValidationWarnings from '../ValidationWarnings.vue'

const mountWarnings = (messages: string[]) => mount(ValidationWarnings, { props: { messages } })

describe('ValidationWarnings', () => {
  it('renders nothing without warnings', () => {
    const wrapper = mountWarnings([])
    expect(wrapper.get('[role="status"]').text()).toBe('')
    expect(wrapper.find('.v-card').exists()).toBe(false)
  })

  it('summarises as one status alert with a count and a collapsed list', async () => {
    const wrapper = mountWarnings(['Name: a', 'Age: b'])

    const alert = wrapper.get('[role="status"] .v-card')
    expect(alert.text()).toContain('2 warnings')
    expect(wrapper.find('li').exists()).toBe(false)

    const toggle = wrapper.get('button[aria-expanded]')
    expect(toggle.attributes('aria-expanded')).toBe('false')
    await toggle.trigger('click')

    expect(toggle.attributes('aria-expanded')).toBe('true')
    expect(wrapper.findAll('li').map(li => li.text())).toEqual(['Name: a', 'Age: b'])
  })

  it('uses the singular for one warning', () => {
    expect(mountWarnings(['Name: a']).get('.font-weight-medium').text()).toBe('1 warning')
  })

  it('can be dismissed and comes back when the warnings change', async () => {
    const wrapper = mountWarnings(['Name: a'])
    await wrapper.get('button[aria-label="Dismiss warnings"]').trigger('click')
    expect(wrapper.find('[role="status"] .v-card').exists()).toBe(false)

    await wrapper.setProps({ messages: ['Name: a'] })
    expect(wrapper.find('[role="status"] .v-card').exists()).toBe(false)

    await wrapper.setProps({ messages: ['Name: a', 'Age: b'] })
    expect(wrapper.find('[role="status"] .v-card').exists()).toBe(true)
  })
})
