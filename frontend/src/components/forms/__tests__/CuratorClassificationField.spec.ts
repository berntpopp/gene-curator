import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import CuratorClassificationField from '../CuratorClassificationField.vue'

const mountField = (curator: string | null, rationale: string | null = null) =>
  mount(CuratorClassificationField, {
    props: {
      modelValue: { curator_classification: curator, curator_classification_rationale: rationale },
      calculated: 'Moderate'
    },
    global: { plugins: [createVuetify()] }
  })

describe('CuratorClassificationField', () => {
  it('offers the ClinGen classes as keys with their labels', () => {
    const items = mountField(null).findComponent({ name: 'VSelect' }).props('items')
    expect(items).toContainEqual({ title: 'No known disease relationship', value: 'no_known' })
  })

  it('needs no rationale when an agreeing key matches a stored label', () => {
    const w = mount(CuratorClassificationField, {
      props: {
        modelValue: { curator_classification: 'no_known', curator_classification_rationale: null },
        calculated: 'No Known Disease Relationship'
      },
      global: { plugins: [createVuetify()] }
    })
    expect(w.findComponent({ name: 'VTextarea' }).exists()).toBe(false)
  })

  it('shows the calculated class and asks no rationale without an override', () => {
    const w = mountField(null)
    expect(w.text()).toContain('Calculated: Moderate')
    expect(w.findComponent({ name: 'VTextarea' }).exists()).toBe(false)
  })

  it('requires a rationale only when the proposal differs (case-insensitive)', () => {
    expect(mountField('moderate').findComponent({ name: 'VTextarea' }).exists()).toBe(false)
    const area = mountField('strong').findComponent({ name: 'VTextarea' })
    expect(area.props('rules')).toHaveLength(1)
    const rule = area.props('rules')[0] as (v: string) => true | string
    expect(rule(' ')).toBe('A rationale is required')
    expect(rule('Replicated')).toBe(true)
  })

  it('emits the whole call on change; clearing sends null', async () => {
    const w = mountField('strong', 'why')
    w.findComponent({ name: 'VSelect' }).vm.$emit('update:modelValue', null)
    w.findComponent({ name: 'VTextarea' }).vm.$emit('update:modelValue', '')
    expect(w.emitted('update:modelValue')).toEqual([
      [{ curator_classification: null, curator_classification_rationale: 'why' }],
      [{ curator_classification: 'strong', curator_classification_rationale: null }]
    ])
  })
})
