/** CurationSchemaSelect item slot with real Vuetify (Vuetify 4 slot `item` is the raw schema). */
import { describe, it, expect, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { VSelect } from 'vuetify/components'
import CurationSchemaSelect from '../CurationSchemaSelect.vue'
import { useSchemasStore } from '@/stores/schemas'

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('CurationSchemaSelect slots', () => {
  it('shows schema type, version and field count per item', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const store = useSchemasStore()
    store.schemas = [
      {
        id: 's1',
        name: 'ClinGen SOP',
        schema_type: 'curation',
        version: '11',
        field_definitions: [{}, {}, {}]
      }
    ] as never
    wrapper = mount(CurationSchemaSelect, {
      props: { scopeId: 'scope-1' },
      global: { plugins: [pinia] },
      attachTo: document.body
    })
    await flushPromises()
    wrapper.findComponent(VSelect).vm.menu = true
    await flushPromises()
    const text = document.body.textContent ?? ''
    expect(text).toContain('ClinGen SOP')
    expect(text).toContain('curation | v11')
    expect(text).toContain('3 fields')
  })
})
