import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import EvidenceTableField from '../EvidenceTableField.vue'
import { normalizeField } from '../normalizeDefinition'

vi.mock('@/api/publications', () => ({
  publicationsAPI: { validatePMIDs: vi.fn().mockResolvedValue({ results: [] }) }
}))
const schema = normalizeField({
  type: 'array',
  ui_component: 'EvidenceTable',
  items: {
    properties: {
      variant_type: {
        type: 'select',
        title: 'Type',
        default: 'null_and_other',
        options: [
          { value: 'null_and_other', label: 'Null + Other' },
          { value: 'two_other', label: 'Two other' },
          { value: 'homozygous_other', label: 'Homozygous other' }
        ]
      },
      points: {
        type: 'number',
        title: 'Points',
        default: 1.5,
        default_by: {
          field: 'variant_type',
          values: { null_and_other: 1.5, two_other: 0.2, homozygous_other: 0.2 }
        }
      }
    }
  }
})
function render(rows: Array<Record<string, unknown>> = []) {
  const wrapper = mount(EvidenceTableField, {
    props: {
      fieldSchema: schema,
      label: 'AR other',
      modelValue: rows,
      'onUpdate:modelValue': (next: unknown) => wrapper.setProps({ modelValue: next })
    }
  })
  return wrapper
}
const current = (w: ReturnType<typeof render>) =>
  (w.props('modelValue') as Array<Record<string, unknown>>)[0]!
async function select(w: ReturnType<typeof render>, value: string) {
  w.findComponent({ name: 'VSelect' }).vm.$emit('update:modelValue', value)
  await flushPromises()
}
describe('selector-driven defaults', () => {
  it('resolves defaults only on newly added automatic rows', async () => {
    const w = render()
    await w.find('.add-row').trigger('click')
    expect(current(w).points).toBe(1.5)
    await select(w, 'two_other')
    expect(current(w).points).toBe(0.2)
    await select(w, 'homozygous_other')
    expect(current(w).points).toBe(0.2)
    await select(w, 'null_and_other')
    expect(current(w).points).toBe(1.5)
    w.unmount()
  })
  it.each(['0', '1', '', '1.5'])(
    'preserves manual input %j, including the suggested value',
    async value => {
      const w = render()
      await w.find('.add-row').trigger('click')
      const input = w.find<HTMLInputElement>('input[aria-label="Points, row 1"]')
      input.element.value = value
      await input.trigger('input')
      await input.trigger('change')
      await select(w, 'two_other')
      expect(current(w).points).toBe(value === '' ? null : Number(value))
      w.unmount()
    }
  )
  it('treats a same-value native change as manual before the equality early-return', async () => {
    const w = render()
    await w.find('.add-row').trigger('click')
    await w.find('input[aria-label="Points, row 1"]').trigger('change')
    await select(w, 'two_other')
    expect(current(w).points).toBe(1.5)
    w.unmount()
  })
  it('never manages loaded rows, including late data, or emits on mount', async () => {
    const w = render([{ id: 'saved', variant_type: 'null_and_other', points: 1.5 }])
    await flushPromises()
    expect(w.emitted('update:model-value')).toBeUndefined()
    await select(w, 'two_other')
    expect(current(w).points).toBe(1.5)
    await w.setProps({ modelValue: [{ id: 'reloaded', variant_type: 'two_other', points: 0 }] })
    await select(w, 'null_and_other')
    expect(current(w).points).toBe(0)
    w.unmount()
  })
  it('removal and a fresh row start fresh automatic tracking', async () => {
    const w = render()
    await w.find('.add-row').trigger('click')
    const previous = current(w).id
    await w.find('input[aria-label="Points, row 1"]').trigger('change')
    await w.find('[aria-label="Remove row 1"]').trigger('click')
    await w.find('.add-row').trigger('click')
    expect(current(w).id).not.toBe(previous)
    await select(w, 'two_other')
    expect(current(w).points).toBe(0.2)
    w.unmount()
  })
})

describe('segregation score assignment', () => {
  it.each([null, 0])(
    'keeps the pinned new-row default %j until a manual score edit',
    async value => {
      const w = render()
      await w.setProps({
        fieldSchema: normalizeField({
          type: 'array',
          ui_component: 'EvidenceTable',
          items: {
            properties: {
              lod_score: { type: 'number', title: 'LOD' },
              points: { type: 'number', title: 'Points', default: value }
            }
          }
        })
      })
      await w.find('.add-row').trigger('click')
      expect(current(w).points).toBe(value)
      const lod = w.find<HTMLInputElement>('input[aria-label="LOD, row 1"]')
      lod.element.value = '3.1'
      await lod.trigger('input')
      await lod.trigger('change')
      expect(current(w).points).toBe(value)
      const points = w.find<HTMLInputElement>('input[aria-label="Points, row 1"]')
      points.element.value = '0'
      await points.trigger('input')
      await points.trigger('change')
      expect(current(w).points).toBe(0)
      await w.setProps({ modelValue: [{ id: 'saved-without-points', lod_score: 3.1 }] })
      expect(current(w)).not.toHaveProperty('points')
      w.unmount()
    }
  )
})
