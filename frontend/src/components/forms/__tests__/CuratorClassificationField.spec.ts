import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import CuratorClassificationField from '../CuratorClassificationField.vue'
import { registerClassifications } from '@/config/classification'

const mountField = (curator: string | null, rationale: string | null = null) =>
  mount(CuratorClassificationField, {
    props: {
      modelValue: { curator_classification: curator, curator_classification_rationale: rationale },
      calculated: 'Moderate'
    },
    global: { plugins: [createVuetify()] }
  })

describe('CuratorClassificationField', () => {
  const pick = (choices: { key: string; label: string }[], calculated: string, curator: string) =>
    mount(CuratorClassificationField, {
      props: {
        modelValue: { curator_classification: curator, curator_classification_rationale: null },
        calculated,
        choices
      },
      global: { plugins: [createVuetify()] }
    })

  it('offers a declared vocabulary with its labels (#539)', () => {
    registerClassifications([
      { key: 'established_risk', label: 'Established association', order: 1, tone: 'strong' }
    ])
    const w = pick(
      [
        { key: 'established_risk', label: 'established_risk' },
        { key: 'uncertain_risk', label: 'Uncertain' }
      ],
      'established_risk',
      'uncertain_risk'
    )
    expect(w.findComponent({ name: 'VSelect' }).props('items')).toEqual([
      { title: 'Established association', value: 'established_risk' },
      { title: 'Uncertain', value: 'uncertain_risk' }
    ])
    expect(w.findComponent({ name: 'VTextarea' }).exists()).toBe(true)
  })

  it('offers a qualitative schema its own classes, not the ClinGen ones', () => {
    const choices = [
      { key: 'strong_association', label: 'Strong Association' },
      { key: 'weak_association', label: 'Weak Association' }
    ]
    const w = pick(choices, 'Strong Association', 'weak_association')
    expect(w.findComponent({ name: 'VSelect' }).props('items')).toEqual([
      { title: 'Strong Association', value: 'strong_association' },
      { title: 'Weak Association', value: 'weak_association' }
    ])
    expect(w.findComponent({ name: 'VTextarea' }).exists()).toBe(true) // differs
    const same = pick(choices, 'Strong Association', 'strong_association')
    expect(same.findComponent({ name: 'VTextarea' }).exists()).toBe(false)
  })

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
