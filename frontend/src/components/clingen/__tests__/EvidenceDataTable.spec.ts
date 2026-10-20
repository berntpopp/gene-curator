import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import EvidenceDataTable from '../EvidenceDataTable.vue'
import type { EvidenceColumn } from '../types'

const columns: EvidenceColumn[] = [
  { key: 'label', label: 'Label' },
  { key: 'pmid', label: 'PMID', type: 'pmid' },
  { key: 'points', label: 'Points', type: 'number', min: 0, max: 3, step: 0.5 }
]

describe('EvidenceDataTable', () => {
  it('shows the empty state when there are no items', () => {
    const wrapper = mount(EvidenceDataTable, { props: { items: [], columns } })
    expect(wrapper.find('table').exists()).toBe(false)
    expect(wrapper.text()).toContain('No evidence items added yet')
  })

  it('renders headers, an actions column and a PubMed link for filled PMIDs', () => {
    const wrapper = mount(EvidenceDataTable, {
      props: { items: [{ label: 'P1', pmid: '12345', points: 1 }], columns }
    })
    const headers = wrapper.findAll('th').map(th => th.text())
    expect(headers).toEqual(['Label', 'PMID', 'Points', 'Actions'])
    expect(wrapper.find('a[href="https://pubmed.ncbi.nlm.nih.gov/12345"]').exists()).toBe(true)
  })

  it('hides the actions column and makes inputs read-only when readonly', () => {
    const wrapper = mount(EvidenceDataTable, {
      props: { items: [{ label: 'P1' }], columns, readonly: true }
    })
    expect(wrapper.findAll('th').map(th => th.text())).not.toContain('Actions')
    expect(wrapper.find('button').exists()).toBe(false)
  })

  it('commits a text cell on change, not per keystroke', async () => {
    const items = [
      { label: 'P1', points: 1 },
      { label: 'P2', points: 2 }
    ]
    const wrapper = mount(EvidenceDataTable, { props: { items, columns } })
    const input = wrapper.findAll('input')[0]!
    input.element.value = 'Renamed'
    await input.trigger('input')
    expect(wrapper.emitted('update:items')).toBeUndefined()

    await input.trigger('change')
    const emitted = wrapper.emitted('update:items')?.[0]?.[0] as typeof items
    expect(emitted[0]).toEqual({ label: 'Renamed', points: 1 })
    expect(emitted[1]).toEqual({ label: 'P2', points: 2 })
    // Parent-owned array stays untouched.
    expect(items[0]).toEqual({ label: 'P1', points: 1 })
  })

  it('commits number-field input as a number on change', async () => {
    const wrapper = mount(EvidenceDataTable, { props: { items: [{ points: 1 }], columns } })
    const input = wrapper.find('input[type="number"]')
    input.element.value = '2.5'
    await input.trigger('change')
    expect(wrapper.emitted('update:items')?.[0]?.[0]).toEqual([{ points: 2.5 }])
  })

  it('labels every cell input with column and row', () => {
    const wrapper = mount(EvidenceDataTable, {
      props: { items: [{ label: 'P1' }, { label: 'P2' }], columns }
    })
    const labels = wrapper
      .findAll('tbody tr')[1]!
      .findAll('input')
      .map(i => i.attributes('aria-label'))
    expect(labels).toEqual(['Label, row 2', 'PMID, row 2', 'Points, row 2'])
  })

  it('shows an inline error for a non-numeric PMID and an out-of-range points value', async () => {
    const wrapper = mount(EvidenceDataTable, {
      props: { items: [{ pmid: 'abc-not-a-pmid', points: 9 }], columns },
      attachTo: document.body
    })
    const fields = wrapper.findAllComponents({ name: 'VTextField' })
    // Rules run on input; trigger validation explicitly
    for (const f of fields)
      await (f.vm as unknown as { validate: () => Promise<unknown> }).validate()
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('PMID must be digits only')
    expect(wrapper.text()).toContain('Enter a number from 0 to 3')
    wrapper.unmount()
  })

  it('keeps an out-of-range number instead of coercing it to zero', async () => {
    const wrapper = mount(EvidenceDataTable, { props: { items: [{ points: 1 }], columns } })
    const input = wrapper.find('input[type="number"]')
    input.element.value = '9'
    await input.trigger('change')
    expect(wrapper.emitted('update:items')?.[0]?.[0]).toEqual([{ points: 9 }])
  })

  it('emits remove with the row index when the delete button is pressed', async () => {
    const wrapper = mount(EvidenceDataTable, {
      props: { items: [{ label: 'P1' }, { label: 'P2' }], columns }
    })
    await wrapper.findAll('tbody tr')[1]?.find('button').trigger('click')
    expect(wrapper.emitted('remove')?.[0]).toEqual([1])
  })
})
