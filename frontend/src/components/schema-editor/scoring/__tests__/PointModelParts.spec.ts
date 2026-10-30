import { describe, it, expect, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick, reactive } from 'vue'
import PointModelTypes from '../PointModelTypes.vue'
import PointModelRowRules from '../PointModelRowRules.vue'
import PointModelSections from '../PointModelSections.vue'
import PointModelBands from '../PointModelBands.vue'
import PointModelReviewFlags from '../PointModelReviewFlags.vue'
import PointModelVocabulary from '../PointModelVocabulary.vue'
import PointModelTests from '../PointModelTests.vue'
import { call, vmOf } from '@/views/__tests__/vm'
import { keepTypes, setNumber, setText, type ItemType, type PointModel } from '../pointModel'

const diag = (path: string) => (path.endsWith('[0].path') ? ['Unknown evidence path'] : [])
const model = (): PointModel => ({
  sections: [
    { key: 'genetic', cap: 12, categories: [{ key: 'probands', types: [{ path: 'p' }] }] },
    { key: 'experimental', categories: [] }
  ],
  bands: [{ class: 'strong', min: 12 }, { class: 'moderate', min: 7 }, { class: 'no_known' }]
})

/** Mount with a v-model the component updates in place or by emit. */
function withModel<T>(component: unknown, value: T, props: Record<string, unknown> = {}) {
  const w = mount(component as never, {
    props: {
      modelValue: value,
      'onUpdate:modelValue': (v: T) => w.setProps({ modelValue: v } as never),
      ...props
    } as never,
    attachTo: document.body
  })
  return w
}
const current = <T>(w: { props: (k: string) => unknown }) => w.props('modelValue') as T

afterEach(() => {
  document.body.innerHTML = ''
})

describe('pointModel helpers', () => {
  it('blank removes optional keys, values are typed', () => {
    const node: Record<string, unknown> = { cap: 1, rule: 'x' }
    setNumber(node, 'cap', '')
    setText(node, 'rule', null)
    setNumber(node, 'min', '2.5')
    setText(node, 'label', 3)
    expect(node).toEqual({ min: 2.5, label: '3' })
    expect(keepTypes(undefined, ['true', 'false', '1'])).toEqual([true, false, '1'])
  })
})

describe('PointModelTypes', () => {
  it('edits range, variant flag and rule, shows diagnostics, adds and removes types', async () => {
    const types: ItemType[] = [{ path: 'p', range: [0, 3] }]
    const w = withModel(PointModelTypes, types, { base: 'x.types', diag })
    expect(w.text()).toContain('Unknown evidence path')
    const vm = vmOf(w)
    const cols = vm.NUMBER_COLS as {
      set: (i: ItemType, v: unknown) => void
      get: (i: ItemType) => unknown
    }[]
    cols[2]!.set(types[0]!, '2')
    expect(types[0]!.range).toEqual([0, 2])
    expect(cols[1]!.get(types[0]!)).toBe(0)
    cols[1]!.set(types[0]!, '')
    expect(types[0]!.range).toEqual([null, 2]) // the other bound stays; the validator flags the gap
    expect(cols[1]!.get(types[0]!)).toBe('')
    cols[1]!.set(types[0]!, '1')
    expect(types[0]!.range).toEqual([1, 2])
    cols[1]!.set(types[0]!, '')
    cols[2]!.set(types[0]!, '')
    expect('range' in types[0]!).toBe(false)
    cols[1]!.set(types[0]!, '0.5')
    expect(types[0]!.range).toEqual([0.5, null])
    cols[0]!.set(types[0]!, '1.5')
    expect(cols[0]!.get(types[0]!)).toBe(1.5)
    await call(vm, 'setFlag', types[0], true)
    expect(types[0]!.require_variant).toBe(true)
    await call(vm, 'setFlag', types[0], false)
    expect('require_variant' in types[0]!).toBe(false)

    await w.find('button[aria-label="Show row rules"]').trigger('click')
    expect(w.text()).toContain('Points when')
    await w
      .findAll('button')
      .find(b => b.text().includes('Evidence type'))!
      .trigger('click')
    expect(types).toHaveLength(2)
    await w.find('button[aria-label="Remove evidence type"]').trigger('click')
    expect(types).toEqual([{ path: '' }])
  })
})

describe('PointModelRowRules', () => {
  it('adds and removes points_when conditions and steps', async () => {
    const item: ItemType = { path: 'segregation', rule: 'step' }
    const w = mount(PointModelRowRules, { props: { item, base: 'b', diag: () => [] } })
    const vm = vmOf(w)
    await call(vm, 'addCondition')
    await call(vm, 'addStep')
    await call(vm, 'addStep')
    expect(item.points_when).toEqual([{ field: '', in: [], points: 0 }])
    expect(item.steps).toHaveLength(2)
    await call(vm, 'remove', 'steps', 0)
    expect(item.steps).toHaveLength(1)
    await call(vm, 'remove', 'steps', 0)
    await call(vm, 'remove', 'points_when', 0)
    expect(item).toEqual({ path: 'segregation', rule: 'step' })
    await nextTick()
    expect(w.text()).toContain('Step field')
  })
})

describe('PointModelRowRules comparisons', () => {
  it('switches a condition between a value list and a numeric bound', async () => {
    const item = reactive<ItemType>({
      path: 'probands',
      points_when: [{ field: 'allele_frequency', in: ['x'], points: 0 }]
    })
    const cond = item.points_when![0]!
    const w = mount(PointModelRowRules, { props: { item, base: 'b', diag: () => [] } })
    const vm = vmOf(w)
    await call(vm, 'setOp', cond, 'in', 'gt')
    expect(cond).toEqual({ field: 'allele_frequency', gt: 0, points: 0 })
    await call(vm, 'setValue', cond, 'gt', '0.0001')
    await call(vm, 'addBound', cond)
    expect(cond).toEqual({ field: 'allele_frequency', gt: 0.0001, lte: 0, points: 0 })
    await call(vm, 'setOp', cond, 'gt', 'gte') // the other bound stays
    expect(cond).toEqual({ field: 'allele_frequency', gte: 0.0001, lte: 0, points: 0 })
    expect((vm.bounds as (c: unknown) => string[])(cond)).toEqual(['gte', 'lte'])
    await nextTick()
    expect(w.findAll('input[type="number"]').length).toBeGreaterThanOrEqual(3) // 2 bounds + points
    await call(vm, 'setOp', cond, 'gte', 'gte')
    expect(cond.gte).toBe(0.0001)
    ;(cond as Record<string, unknown>).and = [{ field: 'moi', in: ['AD'] }]
    await nextTick()
    expect(w.text()).toContain('and 1 more (edit in Code)')
    await call(vm, 'setOp', cond, 'lte', 'in')
    expect(cond).toMatchObject({ in: [] })
    expect('gte' in cond || 'lte' in cond).toBe(false)
    await call(vm, 'addBound', { field: 'x', lt: 1, points: 0 })
    await call(vm, 'setOp', cond, 'in', 'present')
    expect(cond).toEqual({ field: 'allele_frequency', present: true, points: 0, and: cond.and })
    expect((vm.listOp as (c: unknown) => string)(cond)).toBe('present')
    await nextTick()
    expect(w.findAllComponents({ name: 'VCombobox' })).toHaveLength(0) // no values to list
    expect(w.text()).toContain('0 points always wins')
    await call(vm, 'setOp', cond, 'present', 'gte')
    expect(cond).toMatchObject({ gte: 0 })
    expect('present' in cond).toBe(false)
    await call(vm, 'setOp', cond, 'gte', 'present')
    expect(cond).toMatchObject({ present: true })
    expect('gte' in cond).toBe(false)
  })
})

describe('value lists keep their option types', () => {
  it('numbers and booleans stay typed when a list is edited', async () => {
    const item = reactive<ItemType>({
      path: 'probands',
      points_when: [{ field: 'n', in: [2, true, 'AD'], points: 0 }]
    })
    const w = mount(PointModelRowRules, { props: { item, base: 'b', diag: () => [] } })
    const list = w.findAllComponents({ name: 'VCombobox' })[0]!
    list.vm.$emit('update:modelValue', ['2', 'true', 'AD', 'XL'])
    expect(item.points_when![0]!.in).toEqual([2, true, 'AD', 'XL'])

    const value = model()
    value.overrides = [
      { when: 'contradictory', field: 'impact', in: [3, 'refuted'], class: 'disputed' }
    ]
    const b = withModel(PointModelBands, value, { diag: () => [], classKeys: [] })
    await call(vmOf(b), 'setIn', value.overrides[0], ['3', 'refuted', 'disputed'])
    expect(value.overrides[0]!.in).toEqual([3, 'refuted', 'disputed'])
  })
})

describe('PointModelSections', () => {
  it('adds sections and categories and stores combine only when it is max', async () => {
    const value = model()
    const w = withModel(PointModelSections, value, { diag, count: () => 2 })
    const vm = vmOf(w)
    await call(vm, 'addSection')
    expect(value.sections).toHaveLength(3)
    expect(vm.openSections).toEqual([2])
    const category = value.sections[0]!.categories[0]!
    await call(vm, 'setCombine', category, 'max')
    expect(category.combine).toBe('max')
    await call(vm, 'setCombine', category, 'sum')
    expect('combine' in category).toBe(false)
    expect(w.text()).toContain('cap 12')
    await w.findAll('.v-expansion-panel-title')[0]!.trigger('click')
    await w
      .findAll('button')
      .find(b => b.text().includes('Category'))!
      .trigger('click')
    expect(value.sections[0]!.categories).toHaveLength(2)
  })
})

describe('PointModelBands', () => {
  it('sets section minimums, reorders bands and edits overrides', async () => {
    const value = model()
    const w = withModel(PointModelBands, value, { diag: () => [], classKeys: ['strong'] })
    const vm = vmOf(w)
    expect(w.text()).toContain('Min genetic')
    const band = value.bands[1]!
    await call(vm, 'setSectionMin', band, 'genetic', '4')
    expect(band.section_min).toEqual({ genetic: 4 })
    await call(vm, 'setSectionMin', band, 'genetic', '')
    expect('section_min' in band).toBe(false)
    await call(vm, 'move', 1, -1)
    expect(value.bands.map(b => b.class)).toEqual(['moderate', 'strong', 'no_known'])
    await call(vm, 'addOverride')
    await call(vm, 'addOverride')
    const o = value.overrides![0]!
    await call(vm, 'setIn', o, ['disputed'])
    expect(o.in).toEqual(['disputed'])
    await call(vm, 'setIn', o, [])
    expect('in' in o).toBe(false)
    await call(vm, 'removeOverride', 0)
    expect(value.overrides).toHaveLength(1)
    await call(vm, 'removeOverride', 0)
    expect('overrides' in value).toBe(false)
  })
})

describe('PointModelReviewFlags', () => {
  it('writes each flag and drops review_flags when all are blank', async () => {
    const value = model()
    const w = withModel(PointModelReviewFlags, value, { diag: () => [] })
    const vm = vmOf(w)
    await call(vm, 'setHotspot', 'max_variants', '2')
    await call(vm, 'setHotspot', 'min_share', '0.5')
    await call(vm, 'setPair', 0, 'experimental')
    await call(vm, 'setPair', 1, 'genetic')
    await call(vm, 'update', (f: Record<string, unknown>) => setNumber(f, 'band_margin', '2'))
    expect(value.review_flags).toEqual({
      hotspot: { max_variants: 2, min_share: 0.5 },
      experimental_over_genetic: ['experimental', 'genetic'],
      band_margin: 2
    })
    await call(vm, 'setHotspot', 'max_variants', '')
    await call(vm, 'setHotspot', 'min_share', '')
    await call(vm, 'setPair', 0, null)
    await call(vm, 'setPair', 1, null)
    await call(vm, 'update', (f: Record<string, unknown>) => setNumber(f, 'band_margin', ''))
    expect('review_flags' in value).toBe(false)
  })
})

describe('PointModelVocabulary', () => {
  it('adds classes in order and drops the list when the last one goes', async () => {
    const w = withModel(PointModelVocabulary, undefined, { diag: () => [] })
    const vm = vmOf(w)
    await call(vm, 'add')
    await call(vm, 'add')
    expect(current<{ order: number }[]>(w).map(c => c.order)).toEqual([1, 2])
    await call(vm, 'remove', 0)
    expect(current<unknown[]>(w)).toHaveLength(1)
    await call(vm, 'remove', 0)
    expect(current(w)).toBeUndefined()
  })
})

describe('PointModelTests', () => {
  it('edits evidence as JSON with a parse error and adds and removes tests', async () => {
    const w = withModel(PointModelTests, undefined, {
      results: [{ name: 'a', total: 1, verdict: 'Limited', failures: ['expected class'] }],
      running: false,
      classKeys: []
    })
    const vm = vmOf(w)
    await call(vm, 'add')
    const tests = current<{ evidence_data: unknown }[]>(w)
    await call(vm, 'setEvidence', 0, '{"genetic": {}}')
    expect(tests[0]!.evidence_data).toEqual({ genetic: {} })
    await call(vm, 'setEvidence', 0, '[]')
    expect((vm.parseErrors as Record<number, string>)[0]).toContain('JSON object')
    await nextTick()
    expect(w.text()).toContain('Failed')
    await call(vm, 'remove', 0)
    expect(current(w)).toBeUndefined()
    expect(vm.parseErrors).toEqual({})
  })
})

/** Emit an edit from every input, so each binding writes into the model. */
async function touchAll(w: ReturnType<typeof mount>) {
  for (const name of ['VTextField', 'VTextarea', 'VSelect', 'VCombobox', 'VCheckboxBtn']) {
    for (const field of w.findAllComponents({ name })) {
      const multiple = (field.props() as { multiple?: boolean }).multiple
      const value =
        name === 'VCheckboxBtn'
          ? true
          : multiple
            ? ['true', 'x']
            : name === 'VTextarea'
              ? '{}'
              : '1'
      field.vm.$emit('update:modelValue', value)
    }
  }
  await nextTick()
}

/** Click every button once, newest DOM first (removals shift rows). */
async function clickAll(w: ReturnType<typeof mount>) {
  for (const button of w.findAll('button').reverse()) await button.trigger('click')
}

describe('every field binding', () => {
  it('writes edits into the model in each part', async () => {
    const value = model()
    value.overrides = [{ when: 'contradictory', class: 'disputed' }]
    value.review_flags = { hotspot: { max_variants: 2, min_share: 0.5 } }
    const item: ItemType = { path: 'p', rule: 'step', steps: [{ min: 2, points: 1 }] }
    item.points_when = [{ field: 'de_novo', in: ['confirmed'], points: 1.5 }]
    const parts = [
      withModel(PointModelBands, value, { diag: () => [], classKeys: [] }),
      withModel(PointModelReviewFlags, value, { diag: () => [] }),
      mount(PointModelRowRules, { props: { item, base: 'b', diag: () => [] } }),
      withModel(PointModelTypes, [item], { base: 'b', diag: () => [] }),
      withModel(PointModelVocabulary, [{ key: 'a', label: 'A', order: 1, tone: 'strong' }], {
        diag: () => []
      }),
      withModel(PointModelTests, [{ evidence_data: {}, expect: {} }], {
        results: [],
        running: false,
        classKeys: []
      })
    ]
    const sections = withModel(PointModelSections, value, { diag: () => [], count: () => 0 })
    await sections.findAll('.v-expansion-panel-title')[0]!.trigger('click')
    await nextTick()
    for (const w of [...parts, sections]) await touchAll(w as never)
    expect(value.total_cap).toBe(1)
    expect(value.bands[0]!.min).toBe(1)
    expect(value.overrides![0]!.in).toEqual([true, 'x'])
    expect(value.review_flags!.band_margin).toBe(1)
    expect(item.points_when![0]!.in).toEqual([true, 'x'])
    expect(item.steps![0]).toEqual({ min: 1, points: 1 })
    expect(item.require_variant).toBe(true)
    for (const w of [...parts, sections]) await clickAll(w as never)
    expect(value.sections.length).toBeGreaterThan(0)
  })
})
