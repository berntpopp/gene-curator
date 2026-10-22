import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount, type DOMWrapper } from '@vue/test-utils'
import EvidenceTableField from '../EvidenceTableField.vue'
import { normalizeField } from '../normalizeDefinition'
import { publicationsAPI } from '@/api/publications'

vi.mock('@/api/publications', () => ({
  publicationsAPI: { validatePMIDs: vi.fn().mockResolvedValue({ results: [] }) }
}))

// Seeded shape (020_complete_sop11_schema.sql, segregation), trimmed to one column per cell type
const segregation = normalizeField({
  type: 'array',
  ui_component: 'EvidenceTable',
  description: 'Segregation evidence based on LOD scores (max 3 points)',
  item_schema: {
    family_label: { type: 'string', required: true },
    pmid: { type: 'string', required: true, validation: 'pmid_format' },
    lod_score: { type: 'number', required: true, min: 0, max: 10, step: 0.1 },
    lod_score_method: {
      type: 'enum',
      options: [
        { value: 'calculated', label: 'Calculated from family data' },
        { value: 'published', label: 'Published LOD score' }
      ]
    },
    de_novo: { type: 'boolean', default: false }
  }
})

const row = { id: 'r1', family_label: 'F1', pmid: '123', lod_score: 1, lod_score_method: null }

function mountTable(props: Record<string, unknown> = {}) {
  return mount(EvidenceTableField, {
    props: { fieldSchema: segregation, label: 'Segregation', modelValue: [row], ...props },
    attachTo: document.body
  })
}

// Typing: input events only (VTU setValue also fires change, which is the commit)
async function type(input: DOMWrapper<HTMLInputElement>, text: string) {
  input.element.value = text
  await input.trigger('input')
}

const emitted = (w: ReturnType<typeof mountTable>) =>
  (w.emitted('update:model-value') ?? []) as Array<[Array<Record<string, unknown>>]>

describe('EvidenceTableField', () => {
  it('renders true readonly cells as labelled values with links, then restores editable PMID checks', async () => {
    vi.mocked(publicationsAPI.validatePMIDs).mockClear()
    const wrapper = mountTable({
      readonly: true,
      modelValue: [{ ...row, lod_score: 0, de_novo: false, lod_score_method: 'published' }]
    })
    await flushPromises()
    expect(wrapper.findAll('input, textarea, select')).toHaveLength(0)
    expect(wrapper.text()).toContain('Published LOD score')
    expect(wrapper.text()).toContain('No')
    expect(wrapper.find('a[href="https://pubmed.ncbi.nlm.nih.gov/123"]').exists()).toBe(true)
    expect(wrapper.find('.add-row').exists()).toBe(false)
    expect(wrapper.emitted('update:model-value')).toBeUndefined()
    expect(publicationsAPI.validatePMIDs).not.toHaveBeenCalled()
    await wrapper.setProps({ readonly: false })
    await flushPromises()
    expect(wrapper.find('input[aria-label="Pmid, row 1"]').exists()).toBe(true)
    expect(publicationsAPI.validatePMIDs).toHaveBeenCalledOnce()
    wrapper.unmount()
  })
  it('checks saved PMIDs when a read-only table becomes editable', async () => {
    vi.mocked(publicationsAPI.validatePMIDs).mockClear()
    const wrapper = mountTable({ disabled: true })
    await flushPromises()
    expect(publicationsAPI.validatePMIDs).not.toHaveBeenCalled()
    await wrapper.setProps({ disabled: false })
    await flushPromises()
    expect(publicationsAPI.validatePMIDs).toHaveBeenCalledWith(['123'], expect.any(AbortSignal))
    wrapper.unmount()
  })

  it('labels the table, the column headers and every cell', () => {
    const wrapper = mountTable()
    expect(wrapper.find('caption').text()).toContain('Segregation')
    expect(wrapper.findAll('th[scope="col"]').map(th => th.text())).toEqual(
      expect.arrayContaining(['Family label *', 'Pmid *', 'Lod score *', 'De novo'])
    )
    const labels = wrapper.findAll('input').map(i => i.attributes('aria-label'))
    expect(labels).toEqual(
      expect.arrayContaining([
        'Family label, row 1',
        'Pmid, row 1',
        'Lod score, row 1',
        'Lod score method, row 1',
        'De novo, row 1'
      ])
    )
    expect(wrapper.find('[aria-label="Remove row 1"]').exists()).toBe(true)
  })

  it('does not emit while typing and commits on change (blur/Enter)', async () => {
    const wrapper = mountTable()
    const input = wrapper.find<HTMLInputElement>('input[aria-label="Family label, row 1"]')
    await type(input, 'F12')
    await type(input, 'F123')
    expect(emitted(wrapper)).toHaveLength(0)

    await input.trigger('change')
    expect(emitted(wrapper)).toHaveLength(1)
    expect(emitted(wrapper)[0]![0][0]).toMatchObject({ id: 'r1', family_label: 'F123' })
  })

  it('commits numbers as numbers and a cleared number as null', async () => {
    const wrapper = mountTable()
    const input = wrapper.find<HTMLInputElement>('input[aria-label="Lod score, row 1"]')
    await type(input, '2.5')
    await input.trigger('change')
    await type(input, '')
    await input.trigger('change')
    expect(emitted(wrapper).map(([rows]) => rows[0]!.lod_score)).toEqual([2.5, null])
  })

  it('does not emit when a change leaves the value unchanged', async () => {
    const wrapper = mountTable()
    await wrapper.find('input[aria-label="Family label, row 1"]').trigger('change')
    expect(emitted(wrapper)).toHaveLength(0)
  })

  it('commits a checkbox immediately', async () => {
    const wrapper = mountTable()
    await wrapper.find('input[aria-label="De novo, row 1"]').setValue(true)
    expect(emitted(wrapper).at(-1)![0][0]!.de_novo).toBe(true)
  })

  it('adds a row with empty values and defaults, and removes rows', async () => {
    const wrapper = mountTable()
    await wrapper
      .findAll('button')
      .find(b => b.text().includes('Add row'))!
      .trigger('click')
    const added = emitted(wrapper)[0]![0][1]!
    expect(added).toMatchObject({ family_label: '', lod_score: null, de_novo: false })
    expect(typeof added.id).toBe('string')

    await wrapper.find('[aria-label="Remove row 1"]').trigger('click')
    expect(emitted(wrapper)[1]![0]).toEqual([])
  })

  it('is read-only without row actions when disabled', () => {
    const wrapper = mountTable({ disabled: true })
    expect(wrapper.find('[aria-label="Remove row 1"]').exists()).toBe(false)
    expect(wrapper.text()).not.toContain('Add row')
    expect(wrapper.find('input[aria-label="Family label, row 1"]').attributes()).toHaveProperty(
      'readonly'
    )
  })

  it('shows an empty state and field errors', () => {
    const wrapper = mountTable({ modelValue: undefined, errorMessages: ['Add at least one row'] })
    expect(wrapper.text()).toContain('No rows yet')
    expect(wrapper.find('[role="alert"]').text()).toBe('Add at least one row')
  })

  it('keeps typed text when the rows are replaced mid-edit and commits it on blur', async () => {
    const wrapper = mountTable()
    const input = wrapper.find<HTMLInputElement>('input[aria-label="Family label, row 1"]')
    await type(input, 'F-typed')
    await wrapper.setProps({ modelValue: [{ ...row, family_label: 'F-server', pmid: '456' }] })
    expect(input.element.value).toBe('F-typed')

    await input.trigger('change')
    expect(emitted(wrapper).at(-1)![0][0]).toMatchObject({ family_label: 'F-typed', pmid: '456' })
  })

  it('drops the draft on Escape without committing', async () => {
    const wrapper = mountTable()
    const input = wrapper.find<HTMLInputElement>('input[aria-label="Family label, row 1"]')
    await type(input, 'oops')
    await input.trigger('keydown', { key: 'Escape' })
    expect(input.element.value).toBe('F1')
    expect(emitted(wrapper)).toHaveLength(0)
  })

  describe('focus after row changes', () => {
    // v-model harness: the parent writes emitted rows back
    function mountBound(rows: Array<Record<string, unknown>>) {
      const wrapper = mountTable({
        modelValue: rows,
        'onUpdate:modelValue': (next: unknown) => wrapper.setProps({ modelValue: next })
      })
      return wrapper
    }
    const active = () => document.activeElement?.getAttribute('aria-label')

    it("moves focus to the new row's first cell after adding", async () => {
      const wrapper = mountBound([row])
      await wrapper.find('.add-row').trigger('click')
      await flushPromises()
      expect(active()).toBe('Family label, row 2')
    })

    it('escapes quoted and bracketed column titles when focusing a new row', async () => {
      const label = 'Variant "kind" [test]'
      const schema = normalizeField({
        type: 'array',
        ui_component: 'EvidenceTable',
        item_schema: { variant: { type: 'string', title: label } }
      })
      const wrapper = mountTable({
        fieldSchema: schema,
        modelValue: [],
        'onUpdate:modelValue': (next: unknown) => wrapper.setProps({ modelValue: next })
      })
      await wrapper.find('.add-row').trigger('click')
      await flushPromises()
      expect(active()).toBe(`${label}, row 1`)
      wrapper.unmount()
    })

    it("moves focus to the next row's remove button, or Add row after the last", async () => {
      const wrapper = mountBound([row, { ...row, id: 'r2' }])
      await wrapper.find('[aria-label="Remove row 1"]').trigger('click')
      await flushPromises()
      expect(active()).toBe('Remove row 1')
      expect(wrapper.findAll('tbody tr')).toHaveLength(1)

      await wrapper.find('[aria-label="Remove row 1"]').trigger('click')
      await flushPromises()
      expect(document.activeElement?.classList.contains('add-row')).toBe(true)
    })
  })
})
