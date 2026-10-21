/**
 * MONDOAutocomplete slot rendering with real Vuetify (guards the Vuetify 4 `item` API:
 * the slot item is the raw hit, not a wrapper with `.raw`).
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { VAutocomplete } from 'vuetify/components'
import MONDOAutocomplete from '../MONDOAutocomplete.vue'

vi.mock('@/api', () => ({ ontologyAPI: { searchMONDO: vi.fn() } }))

const hit = {
  mondo_id: 'MONDO:0001073',
  label: 'Intellectual disability',
  definition: 'Impaired cognition',
  xrefs: ['OMIM:1', 'HP:2', 'EFO:3'],
  displayText: 'Intellectual disability (MONDO:0001073)'
}
const bare = { mondo_id: 'MONDO:2', label: 'Bare', displayText: 'Bare (MONDO:2)' }

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('MONDOAutocomplete slots', () => {
  it('renders item fields in the open menu', async () => {
    wrapper = mount(MONDOAutocomplete, { attachTo: document.body })
    ;(wrapper.vm as unknown as { searchResults: unknown[] }).searchResults = [hit, bare]
    await flushPromises()
    wrapper.findComponent(VAutocomplete).vm.menu = true
    await flushPromises()
    const text = document.body.textContent ?? ''
    expect(text).toContain('Intellectual disability')
    expect(text).toContain('Impaired cognition')
    expect(text).toContain('OMIM:1')
    expect(text).not.toContain('EFO:3')
    expect(text).toContain('No definition available')
  })

  it('renders the selection slot from the selected item', async () => {
    wrapper = mount(MONDOAutocomplete, { attachTo: document.body })
    ;(wrapper.vm as unknown as { searchResults: unknown[] }).searchResults = [hit]
    await flushPromises()
    wrapper.findComponent(VAutocomplete).vm.$emit('update:modelValue', hit)
    await flushPromises()
    expect(wrapper.text()).toContain('MONDO:0001073')
    expect(wrapper.text()).toContain('Intellectual disability')
  })
})
