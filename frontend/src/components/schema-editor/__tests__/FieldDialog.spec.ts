import { describe, it, expect, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import FieldDialog from '../FieldDialog.vue'
import ColumnsEditor from '../ColumnsEditor.vue'
import type { FieldDef } from '../fieldModel'

type Vm = Record<string, unknown> & { save: () => Promise<void> }

const mountDialog = async (field: FieldDef, otherIds = ['other']) => {
  const wrapper = mount(FieldDialog, { props: { field, otherIds }, attachTo: document.body })
  await flushPromises()
  return { wrapper, vm: wrapper.vm as unknown as Vm }
}

const saved = (wrapper: { emitted: (e: string) => unknown[][] | undefined }) =>
  wrapper.emitted('save')?.[0]?.[0] as Record<string, unknown> | undefined

afterEach(() => {
  document.body.innerHTML = ''
})

describe('FieldDialog', () => {
  it('builds a new choice field with a condition and drops empty keys', async () => {
    const { wrapper, vm } = await mountDialog({ id: '', type: 'text', label: '' })
    expect(document.body.textContent).toContain('Add field')
    const draft = vm.draft as FieldDef
    draft.id = 'binning'
    draft.type = 'select'
    vm.label = 'Binning'
    draft.llm_share = true
    await nextTick()
    const options = vm.options as Array<{ value: string; label: string }>
    options.push({ value: 'isolated', label: 'Isolated' }, { value: ' ', label: '' })
    vm.conditionField = 'other'
    vm.conditionValues = 'AD, AR'
    await vm.save()
    expect(saved(wrapper)).toEqual({
      id: 'binning',
      type: 'select',
      label: 'Binning',
      llm_share: true,
      options: [{ value: 'isolated', label: 'Isolated' }],
      show_when: { other: ['AD', 'AR'] }
    })
  })

  it('refuses a duplicate or malformed id and a condition without values', async () => {
    const { wrapper, vm } = await mountDialog({ id: '', type: 'text' })
    const draft = vm.draft as FieldDef
    draft.id = 'other'
    await vm.save()
    draft.id = '1bad'
    await vm.save()
    expect(wrapper.emitted('save')).toBeUndefined()
    expect(document.body.textContent).toContain('Letters, digits and _ only')
    draft.id = 'ok'
    vm.conditionField = 'other'
    vm.conditionValues = ''
    await vm.save()
    expect(wrapper.emitted('save')).toBeUndefined()
    vm.conditionValues = 'true'
    await vm.save()
    expect(saved(wrapper)?.show_when).toEqual({ other: true })
  })

  it('keeps the keys a field already uses and leaves a multi-part condition alone', async () => {
    const field = {
      id: 'x',
      type: 'text',
      title: 'Old title',
      hint: 'Old hint',
      required: false,
      visible_when: { a: 1, b: 2 },
      custom: { kept: true }
    }
    const { wrapper, vm } = await mountDialog(field)
    expect(document.body.textContent).toContain('multi-part condition')
    vm.label = 'New title'
    await vm.save()
    expect(saved(wrapper)).toEqual({ ...field, title: 'New title' })
  })

  it('removes the condition when the target is cleared', async () => {
    const { wrapper, vm } = await mountDialog({ id: 'x', type: 'text', show_when: { other: 'Y' } })
    expect(vm.conditionField).toBe('other')
    expect(vm.conditionValues).toBe('Y')
    vm.conditionField = null
    await vm.save()
    expect(saved(wrapper)).toEqual({ id: 'x', type: 'text' })
  })

  it('edits evidence-table columns', async () => {
    const { wrapper, vm } = await mountDialog({
      id: 'probands',
      type: 'evidence_table',
      columns: { pmid: { type: 'text', label: 'PMID' } }
    })
    const columns = wrapper.findComponent(ColumnsEditor)
    type Row = { key: string; def: Record<string, unknown> }
    const cvm = columns.vm as unknown as {
      rows: Row[]
      add: () => void
      sync: () => void
      remove: (i: number) => void
      set: (row: Row, key: string, value: unknown) => void
      setOptions: (row: Row, text: string) => void
      keyRule: (i: number) => (v: string) => string | true
    }
    cvm.add()
    await nextTick()
    const row = cvm.rows[1]!
    cvm.set(row, 'type', 'select')
    cvm.setOptions(row, 'lof, missense')
    cvm.set(row, 'required', true)
    row.key = 'variant_class'
    cvm.sync()
    cvm.setOptions(row, 'missense, other') // existing labels survive
    await vm.save()
    expect(saved(wrapper)?.columns).toEqual({
      pmid: { type: 'text', label: 'PMID', order: 1 },
      variant_class: {
        type: 'select',
        label: '',
        order: 2,
        required: true,
        options: [
          { value: 'missense', label: 'missense' },
          { value: 'other', label: 'other' }
        ]
      }
    })
    expect(cvm.keyRule(0)('variant_class')).toBe('Column ids must be unique')
    expect(cvm.keyRule(0)(' ')).toBe('Column id is required')
    cvm.remove(1)
    await vm.save()
    expect(wrapper.emitted('save')?.[1]?.[0]).toMatchObject({
      columns: { pmid: { type: 'text', label: 'PMID', order: 1 } }
    })
  })

  it('lists columns in their stored order (monkey B10)', async () => {
    const { wrapper } = await mountDialog({
      id: 'probands',
      type: 'evidence_table',
      columns: { pmid: { type: 'text', order: 2 }, proband: { type: 'text', order: 1 } }
    })
    const cvm = wrapper.findComponent(ColumnsEditor).vm as unknown as { rows: { key: string }[] }
    expect(cvm.rows.map(r => r.key)).toEqual(['proband', 'pmid'])
  })

  it('closes on cancel', async () => {
    const { wrapper } = await mountDialog({ id: 'x', type: 'text' })
    const cancel = [...document.body.querySelectorAll('button')].find(b =>
      b.textContent?.includes('Cancel')
    )
    cancel?.click()
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})
