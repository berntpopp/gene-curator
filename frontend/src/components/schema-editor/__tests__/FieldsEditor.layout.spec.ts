/** FieldsEditor keeps a flat schema's ui_configuration layout and references in step (#219) */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import FieldsEditor from '../FieldsEditor.vue'
import FieldDialog from '../FieldDialog.vue'
import type { FieldDef } from '../fieldModel'

const confirmMock = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))

type Ui = { layout: { tabs: Array<{ sections: Array<{ fields?: string[] }> }> } }

const defs = () => ({
  evidence_summary: { type: 'textarea', label: 'Summary' },
  moi: { type: 'select', label: 'MOI' },
  notes: { type: 'text', show_when: { moi: 'AD' } },
  genetic: { type: 'object', label: 'Genetic' }
})
const ui = (): Ui => ({
  layout: {
    tabs: [
      { sections: [{ fields: ['evidence_summary', 'moi', 'notes'] }, {}] },
      { sections: [{ fields: ['genetic.case_level', 'genetic.segregation'] }] }
    ]
  }
})

const mountEditor = async (extra: Record<string, unknown> = {}) => {
  const wrapper = mount(FieldsEditor, {
    props: {
      modelValue: defs(),
      uiConfiguration: ui(),
      'onUpdate:modelValue': (v: Record<string, unknown>) => wrapper.setProps({ modelValue: v }),
      'onUpdate:uiConfiguration': (v: unknown) => wrapper.setProps({ uiConfiguration: v }),
      ...extra
    },
    attachTo: document.body
  })
  await flushPromises()
  return wrapper
}
type W = Awaited<ReturnType<typeof mountEditor>>

const click = async (wrapper: W, label: string) => {
  await wrapper.find(`[aria-label="${label}"]`).trigger('click')
  await flushPromises()
}
const uiNow = (wrapper: W) => wrapper.props('uiConfiguration') as Ui
const defsNow = (wrapper: W) =>
  wrapper.props('modelValue') as Record<string, Record<string, unknown>>
const fields = (wrapper: W, tab: number) => uiNow(wrapper).layout.tabs[tab]!.sections[0]!.fields

const addVia = async (wrapper: W, section: number, field: FieldDef) => {
  await wrapper
    .findAll('[data-testid^="section-"]')
    [section]!.findAll('button')
    .at(-1)!
    .trigger('click')
  await flushPromises()
  wrapper.findComponent(FieldDialog).vm.$emit('save', field)
  await flushPromises()
}

const editVia = async (wrapper: W, id: string, field: FieldDef) => {
  await click(wrapper, `Edit ${id}`)
  wrapper.findComponent(FieldDialog).vm.$emit('save', field)
  await flushPromises()
}

beforeEach(() => confirmMock.mockReset())
afterEach(() => {
  document.body.innerHTML = ''
})

describe('FieldsEditor with a tab layout', () => {
  it('groups fields by layout section', async () => {
    const wrapper = await mountEditor()
    const sections = wrapper.findAll('[data-testid^="section-"]')
    expect(sections).toHaveLength(2)
    expect(sections[1]!.text()).toContain('Genetic')
  })

  it('adds a new field to the layout section it was added in', async () => {
    const wrapper = await mountEditor()
    await addVia(wrapper, 1, { id: 'kidney', type: 'text' })
    expect(defsNow(wrapper).kidney).toMatchObject({ type: 'text' })
    expect(fields(wrapper, 1)).toEqual(['genetic.case_level', 'genetic.segregation', 'kidney'])
    expect(fields(wrapper, 0)).toEqual(['evidence_summary', 'moi', 'notes'])
  })

  it('adds a field from "Not in the layout" to the last layout section', async () => {
    const wrapper = await mountEditor({ modelValue: { ...defs(), loose: { type: 'text' } } })
    expect(wrapper.text()).toContain('Not in the layout')
    await addVia(wrapper, 2, { id: 'extra', type: 'url' })
    expect(fields(wrapper, 1)?.at(-1)).toBe('extra')
  })

  it('removes a deleted field and its nested paths from the layout', async () => {
    const wrapper = await mountEditor()
    confirmMock.mockResolvedValue(true)
    await click(wrapper, 'Remove genetic')
    expect(defsNow(wrapper).genetic).toBeUndefined()
    expect(fields(wrapper, 1)).toEqual([])
  })

  it('reorders the layout section with the field list', async () => {
    const wrapper = await mountEditor()
    await click(wrapper, 'Move notes up')
    expect(fields(wrapper, 0)).toEqual(['evidence_summary', 'notes', 'moi'])
  })

  it('renames in the layout and in conditions without asking when nothing else refers to it', async () => {
    const wrapper = await mountEditor()
    await editVia(wrapper, 'moi', { id: 'inheritance', type: 'select', label: 'MOI' })
    expect(confirmMock).not.toHaveBeenCalled()
    expect(defsNow(wrapper).moi).toBeUndefined()
    expect(defsNow(wrapper).notes!.show_when).toEqual({ inheritance: 'AD' })
    expect(fields(wrapper, 0)).toEqual(['evidence_summary', 'inheritance', 'notes'])
  })

  it('asks before a rename that scoring or rules still refer to, and cancels on no', async () => {
    const wrapper = await mountEditor({
      references: {
        scoring_configuration: { types: [{ path: 'genetic.case_level' }] },
        validation_rules: {}
      },
      published: true
    })
    confirmMock.mockResolvedValue(false)
    await editVia(wrapper, 'genetic', { id: 'gen', type: 'object' })
    const asked = confirmMock.mock.calls[0]![0] as { title: string; text: string }
    expect(asked.title).toBe('Rename field "genetic" to "gen"?')
    expect(asked.text).toContain('still used in scoring_configuration')
    expect(asked.text).toContain('published version')
    expect(defsNow(wrapper).genetic).toBeDefined()
    confirmMock.mockResolvedValue(true)
    await editVia(wrapper, 'genetic', { id: 'gen', type: 'object' })
    expect(fields(wrapper, 1)).toEqual(['gen.case_level', 'gen.segregation'])
  })

  it('warns on any rename once the schema is published', async () => {
    const wrapper = await mountEditor({ published: true })
    confirmMock.mockResolvedValue(true)
    await editVia(wrapper, 'notes', { id: 'comment', type: 'text' })
    const asked = confirmMock.mock.calls[0]![0] as { text: string }
    expect(asked.text).not.toContain('still used')
    expect(asked.text).toContain('no longer shown')
  })

  it('emits no UI change for an edit that keeps the id', async () => {
    const wrapper = await mountEditor()
    await editVia(wrapper, 'notes', { id: 'notes', type: 'textarea' })
    expect(wrapper.emitted('update:uiConfiguration')).toBeUndefined()
  })
})
