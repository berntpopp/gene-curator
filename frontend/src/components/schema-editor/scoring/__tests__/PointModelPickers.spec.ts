/** Point-model pickers read the schema's own tables and columns (Wave 10 polish). */
import { describe, it, expect, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick, reactive } from 'vue'
import FieldPicker from '../FieldPicker.vue'
import PointModelRowRules from '../PointModelRowRules.vue'
import PointModelSections from '../PointModelSections.vue'
import PointModelTypes from '../PointModelTypes.vue'
import RuleCondition from '../RuleCondition.vue'
import { readsInside, sectionOptions, tableOptions, topFields } from '../evidenceFields'
import { call, vmOf } from '@/views/__tests__/vm'
import type { ItemType, PointModel, PointsWhen } from '../pointModel'

// A UI-built flat form, a nested ClinGen-style object and the seeded sections shape
const flat = {
  probands: {
    type: 'evidence_table',
    label: 'Probands',
    columns: {
      variant: { type: 'text', label: 'Variant' },
      variant_class: { type: 'select', options: [{ value: 'lof', label: 'LoF' }, 'missense'] },
      points: { type: 'number' }
    }
  },
  notes: { type: 'text' },
  genetic: {
    type: 'object',
    label: 'Genetic evidence',
    properties: {
      case_level: {
        type: 'object',
        properties: { ad: { type: 'array', items: { properties: { lod: { type: 'number' } } } } }
      }
    }
  }
}
const seeded = {
  sections: [{ fields: [{ id: 'segregation', type: 'array', item_schema: { lod: {} } }] }]
}

afterEach(() => {
  document.body.innerHTML = ''
})

describe('evidenceFields', () => {
  it('lists object fields as sections and resolves tables as the scorer reads them', () => {
    expect(sectionOptions(flat)).toEqual([
      { title: 'Genetic evidence', value: 'genetic', subtitle: 'genetic' }
    ])
    // a section naming an object field reads inside it
    expect(tableOptions(flat, 'genetic').map(t => t.value)).toEqual(['case_level.ad'])
    // any other key reads the top level (flat UI forms)
    const top = tableOptions(flat, 'anything')
    expect(top.map(t => t.value)).toEqual(['probands', 'genetic.case_level.ad'])
    expect(top[0]).toMatchObject({ title: 'Probands', subtitle: 'probands' })
    expect(top[0]!.columns.map(c => c.value)).toEqual(['variant', 'variant_class', 'points'])
    expect(top[0]!.columns[1]).toMatchObject({
      title: 'variant_class',
      options: ['lof', 'missense']
    })
    expect(top[0]!.columns[1]!.subtitle).toBeUndefined()
    expect(tableOptions(seeded, '')[0]).toMatchObject({ value: 'segregation' })
    expect(topFields({ sections: [{ fields: [{ id: 'a' }, { id: 'a' }, null] }], a2: 1 })).toEqual({
      a2: 1,
      a: { id: 'a' }
    })
    expect(tableOptions(null, 'x')).toEqual([])
    // a key naming a top-level table is read inside it, as the scorer does: no top-level tables
    expect(readsInside(flat, 'probands')).toBe(true)
    expect(tableOptions(flat, 'probands')).toEqual([])
    expect(readsInside(flat, 'genetic')).toBe(true)
    expect(readsInside(flat, 'anything')).toBe(false)
  })
})

describe('FieldPicker', () => {
  it('emits the stored value as a string and blank when cleared', async () => {
    const w = mount(FieldPicker, { props: { modelValue: '', items: [{ title: 'P', value: 'p' }] } })
    const box = w.findComponent({ name: 'VCombobox' })
    box.vm.$emit('update:modelValue', 'p')
    box.vm.$emit('update:modelValue', null)
    expect(w.emitted('update:modelValue')).toEqual([['p'], ['']])
  })
})

describe('pickers in the point model', () => {
  it('feeds sections, tables and columns down from the field definitions', async () => {
    const model = reactive<PointModel>({
      sections: [{ key: 'x', categories: [{ key: 'c', types: [{ path: 'probands' }] }] }],
      bands: []
    })
    const w = mount(PointModelSections, {
      props: { modelValue: model, diag: () => [], count: () => 0, fieldDefinitions: flat }
    })
    expect(vmOf(w).sections).toEqual(sectionOptions(flat))
    vmOf(w).openSections = [0]
    await nextTick()
    const types = w.findComponent(PointModelTypes)
    expect((types.props('tables') as { value: string }[]).map(t => t.value)).toEqual([
      'probands',
      'genetic.case_level.ad'
    ])
    const cols = vmOf(types).columnsOf as (i: ItemType) => { value: string }[]
    expect(cols({ path: 'probands' }).map(c => c.value)).toContain('variant_class')
    expect(cols({ path: 'nowhere' })).toEqual([])
    expect(w.text()).toContain("Types read the form's tables from the top level")
    model.sections[0]!.key = 'probands'
    await nextTick()
    expect(w.text()).toContain('Types read inside this form field')
  })

  it('offers the values of a choice column and tests a blank field', async () => {
    const item = reactive<ItemType>({
      path: 'probands',
      points_when: [{ field: 'variant_class', in: [], points: 1 }]
    })
    const columns = tableOptions(flat, '')[0]!.columns
    const w = mount(PointModelRowRules, { props: { item, base: 'b', diag: () => [], columns } })
    const vm = vmOf(w.findComponent(RuleCondition))
    const cond = item.points_when![0]!
    expect((vm.choicesOf as (c: PointsWhen) => string[])(cond)).toEqual(['lof', 'missense'])
    await call(vm, 'setOp', cond, 'in', 'absent')
    expect(cond).toEqual({ field: 'variant_class', present: false, points: 1 })
    expect((vm.listOp as (c: PointsWhen) => string)(cond)).toBe('absent')
    await call(vm, 'setOp', cond, 'absent', 'gte')
    expect(cond).toEqual({ field: 'variant_class', gte: 0, points: 1 })
  })

  it('clearing a bound removes it instead of writing 0', async () => {
    const item = reactive<ItemType>({
      path: 'p',
      points_when: [{ field: 'af', gte: 0.1, lte: 0.5, points: 0 }]
    })
    const w = mount(PointModelRowRules, { props: { item, base: 'b', diag: () => [] } })
    const vm = vmOf(w.findComponent(RuleCondition))
    const cond = item.points_when![0]!
    await call(vm, 'setValue', cond, 'lte', '')
    expect(cond).toEqual({ field: 'af', gte: 0.1, points: 0 })
    await call(vm, 'setValue', cond, 'gte', '0.2')
    expect(cond.gte).toBe(0.2)
  })
})
