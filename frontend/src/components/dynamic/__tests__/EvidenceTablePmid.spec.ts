/** PMID cells of an evidence table: Europe PMC lookup on blur, unknown PMIDs block submitting. */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import EvidenceTableField from '../EvidenceTableField.vue'
import { normalizeField } from '../normalizeDefinition'
import { WORKSPACE_FRAME, createWorkspaceFrame } from '@/components/workspace/useWorkspaceFrame'

const validatePMIDs = vi.hoisted(() => vi.fn())
vi.mock('@/api/publications', () => ({ publicationsAPI: { validatePMIDs } }))

const table = normalizeField({
  type: 'array',
  ui_component: 'EvidenceTable',
  items: {
    properties: {
      pmid: { type: 'string', label: 'PMID', validation: 'pmid_format' },
      points: { type: 'number', label: 'Points', default: 0.5 }
    }
  }
})

function mountTable(modelValue: unknown, frame = createWorkspaceFrame(), disabled = false) {
  const wrapper = mount(EvidenceTableField, {
    props: { fieldSchema: table, label: 'Function', modelValue, disabled },
    global: { provide: { [WORKSPACE_FRAME as symbol]: frame } }
  })
  return { wrapper, frame }
}

async function blurPmid(wrapper: ReturnType<typeof mountTable>['wrapper'], pmid: string) {
  const input = wrapper.find<HTMLInputElement>('input[aria-label="PMID, row 1"]')
  input.element.value = pmid
  await input.trigger('blur')
  await vi.advanceTimersByTimeAsync(300)
  await flushPromises()
}

beforeEach(() => {
  validatePMIDs.mockReset()
  vi.useFakeTimers()
  return () => vi.useRealTimers()
})

describe('EvidenceTableField PMID cells', () => {
  it('shows the citation and a PubMed link for a known PMID', async () => {
    validatePMIDs.mockResolvedValue({
      results: [
        { is_valid: true, publication: { title: 'T', authors: ['Smith J', 'Doe A'], year: 2020 } }
      ]
    })
    const { wrapper, frame } = mountTable([{ id: 'r1', pmid: '123' }])
    await blurPmid(wrapper, '123')
    expect(wrapper.find('.pmid-note').text()).toBe('Smith et al. 2020')
    expect(wrapper.find('a[href="https://pubmed.ncbi.nlm.nih.gov/123"]').exists()).toBe(true)
    expect(frame.blockers.value).toEqual([])
  })

  it('blocks submitting (not saving) while an unknown PMID is in the table, and frees it on unmount', async () => {
    validatePMIDs.mockResolvedValue({
      results: [{ is_valid: false, error: 'Publication not found in Europe PMC' }]
    })
    const { wrapper, frame } = mountTable([{ id: 'r1', pmid: '999' }])
    await blurPmid(wrapper, '999')
    expect(wrapper.find('.pmid-note--error').text()).toBe('PMID not found in Europe PMC')
    expect(frame.blockers.value).toEqual([
      'Fix 1 unknown PMID before submitting: PMID 999 not found in Europe PMC'
    ])

    await wrapper.setProps({ modelValue: [] })
    expect(frame.blockers.value).toEqual([])
    wrapper.unmount()
    expect(frame.blockers.value).toEqual([])
  })

  it('counts every unknown PMID in the submit blocker', async () => {
    validatePMIDs.mockResolvedValue({
      results: [{ is_valid: false, error: 'Publication not found in Europe PMC' }]
    })
    const { wrapper, frame } = mountTable([
      { id: 'r1', pmid: '998' },
      { id: 'r2', pmid: '999' }
    ])
    for (const [i, pmid] of ['998', '999'].entries()) {
      const input = wrapper.find<HTMLInputElement>(`input[aria-label="PMID, row ${i + 1}"]`)
      input.element.value = pmid
      await input.trigger('blur')
    }
    await vi.advanceTimersByTimeAsync(300)
    await flushPromises()
    expect(frame.blockers.value).toEqual([
      'Fix 2 unknown PMIDs before submitting: PMID 998, 999 not found in Europe PMC'
    ])
  })

  it('does not look up in a read-only table', async () => {
    const { wrapper } = mountTable([{ id: 'r1', pmid: '123' }], undefined, true)
    await blurPmid(wrapper, '123')
    expect(validatePMIDs).not.toHaveBeenCalled()
  })

  it('shows a legacy single-object value as one row and saves it back as a list', async () => {
    const { wrapper } = mountTable({ pmid: '1', points: 2 })
    expect(wrapper.findAll('tbody tr')).toHaveLength(1)
    await wrapper.find('.add-row').trigger('click')
    const rows = wrapper.emitted('update:model-value')!.at(-1)![0] as Record<string, unknown>[]
    expect(rows).toHaveLength(2)
    // A new row starts with the configured default points
    expect(rows[1]).toMatchObject({ pmid: '', points: 0.5 })
  })

  it('checks PMIDs loaded with a saved draft, without any blur (#267)', async () => {
    const notFound = { is_valid: false, error: 'Publication not found in Europe PMC' }
    const known = { is_valid: true, publication: { title: 'T', authors: ['Smith J'], year: 2020 } }
    validatePMIDs.mockResolvedValue({ results: [notFound, known] })
    const { wrapper, frame } = mountTable([
      { id: 'r1', pmid: '99999999' },
      { id: 'r2', pmid: '123' },
      { id: 'r3', pmid: 'PMID: 99999999' }
    ])
    await flushPromises()
    // A repeated PMID is looked up once, in one batch
    expect(validatePMIDs).toHaveBeenCalledTimes(1)
    expect(validatePMIDs.mock.calls[0]![0]).toEqual(['99999999', '123'])
    expect(frame.blockers.value).toEqual([
      'Fix 2 unknown PMIDs before submitting: PMID 99999999, PMID: 99999999 not found in Europe PMC'
    ])
    expect(wrapper.find('.pmid-note').exists()).toBe(true)

    // Rows replaced from outside: only the new PMID is looked up; known ones don't block
    validatePMIDs.mockResolvedValue({ results: [known] })
    await wrapper.setProps({
      modelValue: [
        { id: 'r2', pmid: '123' },
        { id: 'r4', pmid: '456' }
      ]
    })
    await flushPromises()
    expect(validatePMIDs).toHaveBeenCalledTimes(2)
    expect(validatePMIDs.mock.calls[1]![0]).toEqual(['456'])
    expect(frame.blockers.value).toEqual([])
  })
})
