import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { VCombobox } from 'vuetify/components/VCombobox'
import { VSelect } from 'vuetify/components/VSelect'
import EvidenceTableField from '../EvidenceTableField.vue'
import { normalizeField } from '../normalizeDefinition'

vi.mock('@/api/publications', () => ({
  publicationsAPI: { validatePMIDs: vi.fn().mockResolvedValue({ results: [] }) }
}))

// KGDB diagnostics shape: list cells inside a row (#577)
const diagnostics = normalizeField({
  type: 'evidence_table',
  columns: {
    tools: { type: 'array', title: 'Tools', required: true },
    audiences: {
      type: 'multiselect',
      title: 'Audiences',
      required: true,
      options: [
        { value: 'clinician', label: 'Clinician' },
        { value: 'lab', label: 'Laboratory' }
      ]
    },
    note: { type: 'string' }
  }
})

const row = { id: 'r1', tools: ['WES'], audiences: ['clinician'], note: '' }

const mountTable = (props: Record<string, unknown> = {}) =>
  mount(EvidenceTableField, {
    props: { fieldSchema: diagnostics, label: 'Diagnostics', modelValue: [row], ...props }
  })

const emitted = (w: ReturnType<typeof mountTable>) =>
  (w.emitted('update:model-value') ?? []) as Array<[Array<Record<string, unknown>>]>

describe('EvidenceTableField list cells (#577)', () => {
  it('reloads saved lists into multiple-choice cells without rule errors', async () => {
    const wrapper = mountTable()
    await flushPromises()
    const select = wrapper.findComponent(VSelect)
    const combo = wrapper.findComponent(VCombobox)
    expect(select.props('multiple')).toBe(true)
    expect(select.props('modelValue')).toEqual(['clinician'])
    expect(combo.props('multiple')).toBe(true)
    expect(combo.props('modelValue')).toEqual(['WES'])
    const rules = select.props('rules') as Array<(v: unknown) => unknown>
    expect(rules.map(r => r(['clinician', 'lab']))).toEqual(rules.map(() => true))
    expect(rules.some(r => r([]) !== true)).toBe(true)
  })

  it('commits picked and typed entries as lists', async () => {
    const wrapper = mountTable()
    wrapper.findComponent(VSelect).vm.$emit('update:modelValue', ['clinician', 'lab'])
    wrapper.findComponent(VCombobox).vm.$emit('update:modelValue', ['WES', 'CNV array'])
    const [first, second] = emitted(wrapper).map(([rows]) => rows[0])
    expect(first).toEqual({ ...row, audiences: ['clinician', 'lab'] })
    expect(second).toEqual({ ...row, tools: ['WES', 'CNV array'] })
  })

  it('starts new rows with empty lists and shows lists read-only', async () => {
    const wrapper = mountTable({ modelValue: [] })
    await wrapper.find('.add-row').trigger('click')
    expect(emitted(wrapper)[0]![0][0]).toMatchObject({ tools: [], audiences: [], note: '' })

    const readonly = mountTable({ readonly: true })
    expect(readonly.text()).toContain('WES')
    expect(readonly.text()).toContain('Clinician')
  })
})
