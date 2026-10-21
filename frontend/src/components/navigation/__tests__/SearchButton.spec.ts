import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SearchButton from '../SearchButton.vue'

describe('SearchButton', () => {
  it('is a labelled button that can be clicked without error', async () => {
    const btn = mount(SearchButton).find('button')
    expect(btn.attributes('aria-label')).toBe('Search')
    await btn.trigger('click')
  })
})
