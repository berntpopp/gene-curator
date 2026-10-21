import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DataTable from '../DataTable.vue'

const headers = [
  { title: 'Symbol', key: 'symbol' },
  { title: 'Status', key: 'status' }
]
const items = [
  { symbol: 'PKD1', status: 'active' },
  { symbol: 'HNF1B', status: 'draft' }
]

function mountTable(props: Record<string, unknown> = {}) {
  return mount(DataTable, {
    props: { headers, items, itemsLength: 120, ...props },
    attachTo: document.body
  })
}

describe('DataTable', () => {
  it('shows server totals in the footer, not the page size', () => {
    const w = mountTable()
    expect(w.text()).toContain('1-25 of 120')
    expect(w.findAll('tbody tr')).toHaveLength(2)
  })

  it('emits the search term', async () => {
    const w = mountTable()
    await w.find('input[type="text"]').setValue('pkd')
    expect(w.emitted('update:search')?.at(-1)).toEqual(['pkd'])
  })

  it('applies density as a class and toggles it', async () => {
    const w = mountTable({ density: 'compact' })
    expect(w.find('.data-table').classes()).toContain('data-table--compact')
    await w.find('[data-testid="density-toggle"]').trigger('click')
    expect(w.emitted('update:density')?.at(-1)).toEqual(['comfortable'])
  })

  it('shows an empty state distinct from the error state', () => {
    const empty = mountTable({ items: [], itemsLength: 0 })
    expect(empty.find('[data-testid="table-empty"]').exists()).toBe(true)
    expect(empty.find('[data-testid="table-error"]').exists()).toBe(false)
  })

  it('shows the error with retry and no empty message', async () => {
    const w = mountTable({ items: [], itemsLength: 0, error: 'Server down' })
    expect(w.find('[data-testid="table-error"]').text()).toContain('Server down')
    expect(w.find('[data-testid="table-empty"]').exists()).toBe(false)
    await w.find('[data-testid="table-retry"]').trigger('click')
    expect(w.emitted('retry')).toHaveLength(1)
  })

  it('renders filter chips and emits the chosen value', async () => {
    const w = mountTable({
      filterDefs: [
        {
          key: 'status',
          label: 'Status',
          options: [
            { value: 'active', title: 'Active' },
            { value: 'draft', title: 'Draft' }
          ]
        }
      ],
      filters: { status: 'active' }
    })
    expect(w.find('[data-testid="filter-status"]').text()).toContain('Active')
    await w.find('[data-testid="filter-status-clear"]').trigger('click')
    expect(w.emitted('update:filters')?.at(-1)).toEqual([{}])
  })

  it('hides columns unticked in the picker', async () => {
    const w = mountTable()
    await w.find('[data-testid="column-picker"]').trigger('click')
    await new Promise(r => setTimeout(r))
    const box = document.body.querySelector(
      '[data-testid="column-status"] input'
    ) as HTMLInputElement
    box.click()
    await new Promise(r => setTimeout(r))
    expect(w.findAll('thead th').map(h => h.text())).toEqual(['Symbol'])
    w.unmount()
  })
})
