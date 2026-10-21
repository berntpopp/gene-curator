/** OMIMAutocomplete slot rendering with real Vuetify (Vuetify 4 slot `item` is the raw hit). */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { VAutocomplete } from 'vuetify/components'
import OMIMAutocomplete from '../OMIMAutocomplete.vue'

vi.mock('@/api', () => ({ ontologyAPI: { searchOMIM: vi.fn(), getOMIMDetails: vi.fn() } }))

const full = {
  omim_id: 'OMIM:300855',
  name: 'Fragile X syndrome',
  mondo_id: 'MONDO:0010383',
  gene_symbols: ['FMR1', 'FMR2'],
  displayText: 'Fragile X syndrome (OMIM:300855)'
}
const bare = { omim_id: 'OMIM:1', name: 'Bare disease', displayText: 'Bare disease (OMIM:1)' }

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('OMIMAutocomplete slots', () => {
  it('renders item fields in the open menu', async () => {
    wrapper = mount(OMIMAutocomplete, { attachTo: document.body })
    ;(wrapper.vm as unknown as { searchResults: unknown[] }).searchResults = [full, bare]
    await flushPromises()
    wrapper.findComponent(VAutocomplete).vm.menu = true
    await flushPromises()
    const text = document.body.textContent ?? ''
    expect(text).toContain('Fragile X syndrome')
    expect(text).toContain('OMIM:300855')
    expect(text).toContain('MONDO:0010383')
    expect(text).toContain('Genes: FMR1, FMR2')
    expect(text).toContain('Bare disease')
  })

  it('renders the chip slot from the selected items', async () => {
    wrapper = mount(OMIMAutocomplete, { props: { multiple: true }, attachTo: document.body })
    ;(wrapper.vm as unknown as { searchResults: unknown[] }).searchResults = [full]
    await flushPromises()
    wrapper.findComponent(VAutocomplete).vm.$emit('update:modelValue', [full])
    await flushPromises()
    expect(wrapper.text()).toContain('OMIM:300855')
  })
})
