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

  it('emits update:items with the edited row merged into a copy of the list', async () => {
    const items = [
      { label: 'P1', points: 1 },
      { label: 'P2', points: 2 }
    ]
    const wrapper = mount(EvidenceDataTable, { props: { items, columns } })
    wrapper.findAllComponents({ name: 'VTextField' })[0]?.vm.$emit('update:modelValue', 'Renamed')

    const emitted = wrapper.emitted('update:items')?.[0]?.[0] as typeof items
    expect(emitted[0]).toEqual({ label: 'Renamed', points: 1 })
    expect(emitted[1]).toEqual({ label: 'P2', points: 2 })
    // Parent-owned array stays untouched.
    expect(items[0]).toEqual({ label: 'P1', points: 1 })
  })

  it('coerces number-field input with parseFloat, falling back to zero', () => {
    const wrapper = mount(EvidenceDataTable, { props: { items: [{ points: 1 }], columns } })
    const numberField = wrapper
      .findAllComponents({ name: 'VTextField' })
      .find(f => f.props('type') === 'number')
    numberField?.vm.$emit('update:modelValue', 'abc')
    expect(wrapper.emitted('update:items')?.[0]?.[0]).toEqual([{ points: 0 }])
  })

  it('emits remove with the row index when the delete button is pressed', async () => {
    const wrapper = mount(EvidenceDataTable, {
      props: { items: [{ label: 'P1' }, { label: 'P2' }], columns }
    })
    await wrapper.findAll('tbody tr')[1]?.find('button').trigger('click')
    expect(wrapper.emitted('remove')?.[0]).toEqual([1])
  })
})
