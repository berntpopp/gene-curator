import { describe, it, expect } from 'vitest'
import { mount, type DOMWrapper } from '@vue/test-utils'
import EvidenceTableField from '../EvidenceTableField.vue'
import { normalizeField } from '../normalizeDefinition'

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
})
