import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent, h } from 'vue'
import { VLayout } from 'vuetify/components'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia } from 'pinia'
import PhoneHeader from '../PhoneHeader.vue'

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

const component = { render: () => null }

describe('PhoneHeader', () => {
  it('shows the route title, a labelled search button and the theme toggle', async () => {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/assignments', component, meta: { title: 'My work' } }]
    })
    await router.push('/assignments')
    const wrapper = mount(defineComponent({ render: () => h(VLayout, () => h(PhoneHeader)) }), {
      global: { plugins: [router, createPinia()] }
    })
    await flushPromises()

    expect(wrapper.find('header h1').text()).toBe('My work')
    expect(wrapper.find('button[aria-label="Search"]').exists()).toBe(true)
    expect(wrapper.find('button[aria-label^="Theme:"]').exists()).toBe(true)
    wrapper.unmount()
  })
})
