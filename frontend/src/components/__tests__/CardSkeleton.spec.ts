/**
 * CardSkeleton Component Tests
 *
 * @see src/components/skeletons/CardSkeleton.vue
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { h } from 'vue'
import CardSkeleton from '../skeletons/CardSkeleton.vue'

describe('CardSkeleton', () => {
  it('renders one skeleton card per requested count while loading', () => {
    const wrapper = mount(CardSkeleton, { props: { loading: true, count: 3 } })

    expect(wrapper.findAll('.v-skeleton-loader')).toHaveLength(3)
  })

  it('renders the default slot once loading is done', () => {
    const wrapper = mount(CardSkeleton, {
      props: { loading: false },
      slots: { default: () => h('p', { class: 'content' }, 'Loaded') }
    })

    expect(wrapper.find('.content').text()).toBe('Loaded')
    expect(wrapper.findAll('.v-skeleton-loader')).toHaveLength(0)
  })
})
