import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { useSearchStore } from '@/stores/search'
import SearchButton from '../SearchButton.vue'

describe('SearchButton', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('is a labelled button that opens the command palette', async () => {
    const btn = mount(SearchButton).find('button')
    expect(btn.attributes('aria-label')).toBe('Search')
    expect(useSearchStore().isOpen).toBe(false)
    await btn.trigger('click')
    expect(useSearchStore().isOpen).toBe(true)
  })
})
