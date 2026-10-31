/** UX: a wide evidence table edits one row at a time in a side sheet; narrow ones stay inline. */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import EvidenceTableField from '../EvidenceTableField.vue'
import { normalizeField } from '../normalizeDefinition'

vi.mock('@/api/publications', () => ({
  publicationsAPI: { validatePMIDs: vi.fn().mockResolvedValue({ results: [] }) }
}))

const columns = Object.fromEntries(
  ['label', 'variant', 'zygosity', 'phenotype', 'sex', 'age', 'notes'].map(k => [
    k,
    { type: 'text', label: k[0]!.toUpperCase() + k.slice(1) }
  ])
)
const wide = normalizeField({ type: 'evidence_table', columns })
const row = { id: 'r1', label: 'P1', variant: 'c.1A>G' }

afterEach(() => {
  document.body.innerHTML = ''
})

function mountWide(modelValue: unknown[] = [row]) {
  return mount(EvidenceTableField, {
    props: { fieldSchema: wide, label: 'Probands', modelValue },
    attachTo: document.body
  })
}

describe('wide evidence table row editor', () => {
  it('shows rows read-only with an Edit button instead of 7 inline inputs', () => {
    const w = mountWide()
    expect(w.findAll('tbody input')).toHaveLength(0)
    expect(w.text()).toContain('c.1A>G')
    expect(w.find('[aria-label="Edit row 1"]').exists()).toBe(true)
  })

  it('edits one row in the sheet and emits the whole table', async () => {
    const w = mountWide()
    await w.find('[aria-label="Edit row 1"]').trigger('click')
    await flushPromises()
    const sheet = document.body.querySelector('.row-editor')!
    expect(sheet.textContent).toContain('Probands · P1')
    const variant = sheet.querySelector<HTMLInputElement>('input[value="c.1A>G"]')!
    variant.value = 'c.2C>T'
    variant.dispatchEvent(new Event('input'))
    await flushPromises()
    expect(w.emitted('update:model-value')!.at(-1)![0]).toEqual([{ ...row, variant: 'c.2C>T' }])
  })

  it('opens the sheet for a new row', async () => {
    const w = mountWide([])
    await w.find('.add-row').trigger('click')
    const [rows] = w.emitted('update:model-value')!.at(-1)! as [Record<string, unknown>[]]
    await w.setProps({ modelValue: rows })
    await flushPromises()
    expect(document.body.querySelector('.row-editor')?.textContent).toContain('Probands · Row 1')
  })
})
