/**
 * TableSkeleton Component Tests
 *
 * @see src/components/skeletons/TableSkeleton.vue
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import TableSkeleton from '../skeletons/TableSkeleton.vue'

const headers = [
  { key: 'id', title: 'ID' },
  { key: 'status', title: 'Status' },
  { key: 'description', title: 'Description' },
  { key: 'created_date', title: 'Created' },
  { key: 'actions', title: 'Actions' },
  { key: 'name', title: 'Name' }
]

describe('TableSkeleton', () => {
  it('renders skeleton cells for every header and row while loading', () => {
    const wrapper = mount(TableSkeleton, {
      props: { loading: true, items: [], headers, skeletonCount: 2 }
    })

    expect(wrapper.findAll('td.skeleton-cell')).toHaveLength(2 * headers.length)
  })

  it('sizes skeleton bones by column type', () => {
    const wrapper = mount(TableSkeleton, {
      props: { loading: true, items: [], headers: headers.slice(0, 1), skeletonCount: 1 }
    })

    expect(wrapper.html()).toContain('120px')
  })

  it('renders real rows through the item slot when not loading', () => {
    const wrapper = mount(TableSkeleton, {
      props: {
        loading: false,
        items: [{ id: '1', name: 'Alpha' }],
        headers: [{ key: 'name', title: 'Name' }]
      },
      slots: {
        item: (scope: unknown) =>
          h('tr', { class: 'real-row' }, [h('td', (scope as { item: { name: string } }).item.name)])
      }
    })

    expect(wrapper.find('.real-row').text()).toBe('Alpha')
    expect(wrapper.findAll('td.skeleton-cell')).toHaveLength(0)
  })
})
