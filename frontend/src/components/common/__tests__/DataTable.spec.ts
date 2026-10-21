import { describe, it, expect } from 'vitest'
import { defineComponent, h, ref } from 'vue'
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
    await w.find('[data-testid="density-comfortable"]').trigger('click')
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
    await w.find('[data-testid="filter-status"] .v-chip__close').trigger('click')
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

  it('picks a filter option from the chip menu', async () => {
    const w = mountTable({
      filterDefs: [
        { key: 'status', label: 'Status', options: [{ value: 'draft', title: 'Draft' }] }
      ]
    })
    await w.find('[data-testid="filter-status"]').trigger('click')
    await new Promise(r => setTimeout(r, 50))
    const opt = document.body.querySelector('.v-list-item') as HTMLElement
    opt.click()
    expect(w.emitted('update:filters')?.at(-1)).toEqual([{ status: 'draft' }])
    w.unmount()
  })

  it('emits paging and sorting', async () => {
    const w = mountTable()
    await w.find('thead th').trigger('click')
    expect(w.emitted('update:sortBy')?.at(-1)).toEqual([[{ key: 'symbol', order: 'asc' }]])
    await w.find('button[aria-label*="Next page"]').trigger('click')
    expect(w.emitted('update:page')?.at(-1)).toEqual([2])
  })

  it('renders a multi-select chip and toggles values', async () => {
    const w = mountTable({
      filterDefs: [
        {
          key: 'cls',
          label: 'Classification',
          multiple: true,
          options: [
            { value: 'd', title: 'Definitive' },
            { value: 's', title: 'Strong' }
          ]
        }
      ],
      filters: { cls: ['d', 's'] }
    })
    expect(w.find('[data-testid="filter-cls"]').text()).toContain(
      'Classification: Definitive, Strong'
    )
    await w.find('[data-testid="filter-cls"]').trigger('click')
    await new Promise(r => setTimeout(r, 50))
    ;(document.body.querySelector('.v-list-item') as HTMLElement).click()
    expect(w.emitted('update:filters')?.at(-1)).toEqual([{ cls: ['s'] }])
    ;(document.body.querySelector('.v-list-item') as HTMLElement).click()
    w.unmount()
  })

  it('renders the toolbar actions slot and typed item slots', () => {
    const w = mount(DataTable, {
      props: { headers, items, itemsLength: 2 },
      slots: {
        'toolbar-actions': '<button data-testid="export">Export</button>',
        'item.symbol': (p: { item: Record<string, unknown> }) =>
          h('b', { class: 'sym' }, String(p.item.symbol))
      }
    })
    expect(w.find('[data-testid="export"]').exists()).toBe(true)
    expect(w.findAll('b.sym').map(b => b.text())).toEqual(['PKD1', 'HNF1B'])
  })

  it('renders item slots that appear after mount (columns that arrive with data)', async () => {
    const extra = ref<string[]>([])
    const Host = defineComponent({
      setup: () => () =>
        h(
          DataTable,
          { headers: [...headers, { title: 'Late', key: 'late' }], items, itemsLength: 2 },
          Object.fromEntries(
            extra.value.map(k => [`item.${k}`, () => h('i', { class: 'late' }, 'cell')])
          )
        )
    })
    const w = mount(Host)
    expect(w.findAll('i.late')).toHaveLength(0)
    extra.value = ['late']
    await w.vm.$nextTick()
    expect(w.findAll('i.late')).toHaveLength(2)
  })
})
