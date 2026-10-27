import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DynamicField from '../DynamicField.vue'
import { ontologyAPI } from '@/api'
vi.mock('@/api', () => ({ ontologyAPI: { searchMONDO: vi.fn() } }))

describe('stored MONDO identifiers through DynamicField', () => {
  it('restores a susceptibility label without an extra diseaseName prop or changing stored evidence', async () => {
    vi.mocked(ontologyAPI.searchMONDO).mockResolvedValue({
      query: 'MONDO:0009100',
      total_results: 1,
      results: [
        {
          mondo_id: 'MONDO:0009100',
          label: 'type 1 diabetes mellitus 1',
          definition: 'Stored susceptibility term',
          synonyms: [],
          xrefs: []
        }
      ]
    })
    const wrapper = mount(DynamicField, {
      props: {
        fieldName: 'mondo_id',
        modelValue: 'MONDO:0009100',
        fieldSchema: { type: 'string', component: 'MONDOAutocomplete', title: 'Disease' }
      }
    })
    await flushPromises()
    expect(ontologyAPI.searchMONDO).toHaveBeenCalledTimes(1)
    expect(ontologyAPI.searchMONDO).toHaveBeenCalledWith('MONDO:0009100', 1)
    expect(wrapper.text()).toContain('type 1 diabetes mellitus 1')
    expect(wrapper.findComponent({ name: 'MONDOAutocomplete' }).props('diseaseName')).toBe('')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    wrapper.unmount()
  })
})
