/** Review #602 item 5: list items show who added and changed them, like table rows. */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { ref } from 'vue'
import DynamicNestedField from '../DynamicNestedField.vue'
import { FIELD_PATH, ROW_PROVENANCE } from '../rowAuthorship'

const STAMP = {
  added_by: { name: 'Alice', agent: { model: 'm', agent: 'Claude Code' } },
  added_at: '2026-10-02T09:00:00Z'
}

describe('DynamicNestedField authorship', () => {
  it('captions each item from the row provenance map', () => {
    const w = mount(DynamicNestedField, {
      props: {
        fieldName: 'models',
        fieldSchema: { type: 'array', items: { properties: { label: { type: 'string' } } } },
        label: 'Models',
        modelValue: [{ id: 'm1', label: 'mouse' }, { label: 'fish' }],
        depth: 0,
        errorMessages: [],
        readonly: true
      },
      global: {
        provide: {
          [ROW_PROVENANCE as symbol]: ref({ 'experimental.models#m1': STAMP }),
          [FIELD_PATH as symbol]: 'experimental.'
        }
      }
    })
    const captions = w.findAll('[data-testid="item-authorship"]')
    expect(captions).toHaveLength(1)
    expect(captions[0]!.text()).toMatch(/^Added by Alice via Claude Code \(m\), /)
  })
})
