import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ThemeToggle from '../ThemeToggle.vue'

const logger = vi.hoisted(() => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))

afterEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

describe('ThemeToggle', () => {
  it('cycles system -> light -> dark -> system, persisting each choice', async () => {
    const wrapper = mount(ThemeToggle)
    const btn = wrapper.find('button')
    expect(btn.attributes('aria-label')).toBe('Theme: system. Switch to light theme')
    expect(btn.html()).toContain('mdi-theme-light-dark')

    for (const [next, label, icon] of [
      ['light', 'Theme: light. Switch to dark theme', 'mdi-white-balance-sunny'],
      ['dark', 'Theme: dark. Switch to system theme', 'mdi-weather-night'],
      ['system', 'Theme: system. Switch to light theme', 'mdi-theme-light-dark']
    ]) {
      await btn.trigger('click')
      expect(localStorage.getItem('theme')).toBe(next)
      expect(logger.info).toHaveBeenLastCalledWith('Theme changed', { theme: next })
      expect(btn.attributes('aria-label')).toBe(label)
      expect(btn.html()).toContain(icon)
    }
  })

  it('starts from the saved theme', () => {
    localStorage.setItem('theme', 'dark')
    expect(mount(ThemeToggle).find('button').attributes('aria-label')).toBe(
      'Theme: dark. Switch to system theme'
    )
  })
})
