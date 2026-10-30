import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import FieldsEditor from '../FieldsEditor.vue'
import FieldDialog from '../FieldDialog.vue'
import type { FieldDef } from '../fieldModel'

const confirmMock = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))

const sectioned = () => ({
  sections: [
    {
      id: 'entity',
      label: 'Entity',
      description: 'The pair',
      fields: [
        { id: 'mondo_id', type: 'external_reference', label: 'Mondo', required: true },
        { id: 'notes', type: 'textarea', show_when: { mondo_id: 'x' }, llm_share: true }
      ]
    },
    { id: 'other', label: 'Other', fields: [] }
  ]
})

const mountEditor = async (modelValue: Record<string, unknown>, readonly = false) => {
  const wrapper = mount(FieldsEditor, {
    props: {
      modelValue,
      readonly,
      'onUpdate:modelValue': (v: Record<string, unknown>) => wrapper.setProps({ modelValue: v })
    },
    attachTo: document.body
  })
  await flushPromises()
  return wrapper
}

const click = async (wrapper: Awaited<ReturnType<typeof mountEditor>>, label: string) => {
  await wrapper.find(`[aria-label="${label}"]`).trigger('click')
  await flushPromises()
}

const last = (wrapper: Awaited<ReturnType<typeof mountEditor>>) => {
  const events = wrapper.emitted('update:modelValue') ?? []
  return events[events.length - 1]?.[0] as ReturnType<typeof sectioned>
}

beforeEach(() => confirmMock.mockReset())
afterEach(() => {
  document.body.innerHTML = ''
})

describe('FieldsEditor', () => {
  it('lists sections and fields read-only without edit controls', async () => {
    const wrapper = await mountEditor(sectioned(), true)
    const text = wrapper.text()
    expect(text).toContain('Entity')
    expect(text).toContain('The pair')
    expect(text).toContain('Mondo')
    expect(text).toContain('Ontology reference')
    expect(text).toContain('Required')
    expect(text).toContain('Conditional')
    expect(text).toContain('LLM')
    expect(wrapper.find('[aria-label="Edit mondo_id"]').exists()).toBe(false)
    expect(text).not.toContain('Add field')
  })

  it('says how to start when there are no fields', async () => {
    expect((await mountEditor({}, true)).text()).toContain('Edit the schema to add one.')
    expect((await mountEditor({})).text()).toContain('Add a section to start.')
  })

  it('adds a section, then a field to it', async () => {
    const wrapper = await mountEditor({})
    await wrapper.find('button.v-btn').trigger('click') // Add section
    await flushPromises()
    expect(last(wrapper)).toEqual({
      sections: [{ id: 'section_1', label: 'Section 1', fields: [] }]
    })
    const add = wrapper.findAll('button').find(b => b.text().includes('Add field'))!
    await add.trigger('click')
    await flushPromises()
    const dialog = wrapper.findComponent(FieldDialog)
    expect(dialog.props('field')).toEqual({ id: '', type: 'text', label: '' })
    dialog.vm.$emit('save', { id: 'cakut_subtype', type: 'select', label: 'CAKUT' } as FieldDef)
    await flushPromises()
    expect(last(wrapper).sections[0]!.fields).toEqual([
      { id: 'cakut_subtype', type: 'select', label: 'CAKUT' }
    ])
    expect(wrapper.findComponent(FieldDialog).props('field')).toBeNull()
  })

  it('edits, moves and removes fields', async () => {
    const wrapper = await mountEditor(sectioned())
    await click(wrapper, 'Edit notes')
    const dialog = wrapper.findComponent(FieldDialog)
    expect(dialog.props('otherIds')).toEqual(['mondo_id'])
    dialog.vm.$emit('save', { id: 'notes', type: 'text' } as FieldDef)
    await flushPromises()
    expect(last(wrapper).sections[0]!.fields[1]).toEqual({ id: 'notes', type: 'text' })

    await click(wrapper, 'Move notes up')
    expect(last(wrapper).sections[0]!.fields.map(f => f.id)).toEqual(['notes', 'mondo_id'])
    await click(wrapper, 'Move notes down')
    expect(last(wrapper).sections[0]!.fields.map(f => f.id)).toEqual(['mondo_id', 'notes'])

    confirmMock.mockResolvedValue(false)
    await click(wrapper, 'Remove notes')
    expect(last(wrapper).sections[0]!.fields).toHaveLength(2)
    confirmMock.mockResolvedValue(true)
    await click(wrapper, 'Remove notes')
    expect(last(wrapper).sections[0]!.fields.map(f => f.id)).toEqual(['mondo_id'])
    expect(wrapper.find('[aria-label="Move mondo_id up"]').attributes('disabled')).toBeDefined()
  })

  it('renames, moves and removes sections', async () => {
    const wrapper = await mountEditor(sectioned())
    const title = wrapper.findAll('input')[0]!
    await title.setValue('Disease entity')
    expect(last(wrapper).sections[0]!.label).toBe('Disease entity')
    await wrapper.findAll('input')[1]!.setValue('New description')
    expect(last(wrapper).sections[0]!.description).toBe('New description')

    await click(wrapper, 'Move section Other up')
    expect(last(wrapper).sections.map(s => s.id)).toEqual(['other', 'entity'])
    await click(wrapper, 'Move section Other down')
    expect(last(wrapper).sections.map(s => s.id)).toEqual(['entity', 'other'])

    await click(wrapper, 'Remove section Other') // empty: no confirmation
    expect(confirmMock).not.toHaveBeenCalled()
    expect(last(wrapper).sections.map(s => s.id)).toEqual(['entity'])
    confirmMock.mockResolvedValue(false)
    await click(wrapper, 'Remove section Disease entity')
    expect(last(wrapper).sections).toHaveLength(1)
    confirmMock.mockResolvedValue(true)
    await click(wrapper, 'Remove section Disease entity')
    expect(last(wrapper).sections).toEqual([])
  })

  it('edits a flat map in place, keeps it flat and writes the order', async () => {
    const wrapper = await mountEditor({ a: { type: 'text' }, b: { type: 'number' } })
    expect(wrapper.text()).toContain('stores its fields as one list')
    expect(wrapper.text()).not.toContain('Add section')
    await click(wrapper, 'Move b up')
    expect(last(wrapper)).toEqual({
      b: { type: 'number', order: 1 },
      a: { type: 'text', order: 2 }
    })
    const add = wrapper.findAll('button').find(b => b.text().includes('Add field'))!
    await add.trigger('click')
    wrapper.findComponent(FieldDialog).vm.$emit('save', { id: 'c', type: 'url' } as FieldDef)
    await flushPromises()
    expect(last(wrapper)).toMatchObject({ c: { type: 'url', order: 3 } })
    wrapper.findComponent(FieldDialog).vm.$emit('close')
  })
})
