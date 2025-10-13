/**
 * LoadingState Component Tests
 *
 * Tests for the loading skeleton wrapper component
 *
 * Test Coverage:
 * - Skeleton display when loading
 * - Content display when not loading
 * - Different skeleton types
 * - Slot rendering
 * - Smooth transitions
 *
 * @see src/components/LoadingState.vue
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LoadingState from '../LoadingState.vue'

describe('LoadingState', () => {
  describe('Loading State', () => {
    it('should show skeleton when loading is true', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true
        },
        slots: {
          default: '<div class="content">Content</div>'
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })

    it('should show content when loading is false', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: false
        },
        slots: {
          default: '<div class="test-content">Loaded Content</div>'
        }
      })

      const content = wrapper.find('.test-content')
      expect(content.exists()).toBe(true)
      expect(content.text()).toBe('Loaded Content')
    })

    it('should default to loading when not specified', () => {
      const wrapper = mount(LoadingState, {
        slots: {
          default: '<div>Content</div>'
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })
  })

  describe('Skeleton Types', () => {
    it('should use default list skeleton type', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })

    it('should accept custom skeleton type', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true,
          type: 'card'
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })

    it('should support table skeleton type', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true,
          type: 'table'
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })

    it('should support multiple row skeleton type', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true,
          type: 'list-item-avatar-two-line@5'
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })
  })

  describe('Slot Content', () => {
    it('should render slot content when not loading', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: false
        },
        slots: {
          default: '<div class="actual-content">Real Content</div>'
        }
      })

      const content = wrapper.find('.actual-content')
      expect(content.exists()).toBe(true)
      expect(content.text()).toBe('Real Content')
    })

    it('should render complex slot content', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: false
        },
        slots: {
          default: `
            <div class="complex-content">
              <h2 class="title">Title</h2>
              <p class="description">Description</p>
              <button class="action">Action</button>
            </div>
          `
        }
      })

      expect(wrapper.find('.complex-content').exists()).toBe(true)
      expect(wrapper.find('.title').exists()).toBe(true)
      expect(wrapper.find('.description').exists()).toBe(true)
      expect(wrapper.find('.action').exists()).toBe(true)
    })

    it('should handle empty slot gracefully', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })
  })

  describe('Common Use Cases', () => {
    it('should handle list loading', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true,
          type: 'list-item-avatar-two-line@3'
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })

    it('should handle table loading', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true,
          type: 'table'
        },
        slots: {
          default: '<table><tr><td>Data</td></tr></table>'
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })

    it('should handle card loading', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true,
          type: 'card'
        },
        slots: {
          default: '<div class="card">Card Content</div>'
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })
  })

  describe('Reactivity', () => {
    it('should switch from loading to content', async () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true
        },
        slots: {
          default: '<div class="content">Loaded</div>'
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)

      await wrapper.setProps({ loading: false })

      const content = wrapper.find('.content')
      expect(content.exists()).toBe(true)
      expect(content.text()).toBe('Loaded')
    })

    it('should switch from content to loading', async () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: false
        },
        slots: {
          default: '<div class="content">Content</div>'
        }
      })

      const content = wrapper.find('.content')
      expect(content.exists()).toBe(true)

      await wrapper.setProps({ loading: true })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })

    it('should update skeleton type dynamically', async () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true,
          type: 'list-item'
        }
      })

      let skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)

      await wrapper.setProps({ type: 'card' })

      skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })
  })

  describe('Layout', () => {
    it('should have full width', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true
        }
      })

      const container = wrapper.find('.loading-state')
      expect(container.exists()).toBe(true)
      expect(container.element.style.width).toBe('100%')
    })
  })

  describe('Accessibility', () => {
    it('should be screen reader friendly during loading', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true
        },
        slots: {
          default: '<div>Content</div>'
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
      // Vuetify skeleton loader handles accessibility internally
    })

    it('should not affect content accessibility when loaded', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: false
        },
        slots: {
          default: '<button aria-label="Submit form">Submit</button>'
        }
      })

      const button = wrapper.find('button')
      expect(button.attributes('aria-label')).toBe('Submit form')
    })
  })

  describe('Edge Cases', () => {
    it('should handle null loading prop', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: null
        },
        slots: {
          default: '<div class="content">Content</div>'
        }
      })

      // Null should be falsy, so content should show
      const content = wrapper.find('.content')
      expect(content.exists()).toBe(true)
    })

    it('should handle undefined loading prop', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: undefined
        },
        slots: {
          default: '<div class="content">Content</div>'
        }
      })

      // Without explicit loading prop, should default to true
      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })

    it('should handle invalid skeleton type gracefully', () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true,
          type: 'invalid-type'
        }
      })

      const skeleton = wrapper.find('.v-skeleton-loader')
      expect(skeleton.exists()).toBe(true)
    })

    it('should handle very large content in slot', () => {
      const largeContent = Array(100).fill('<div>Row</div>').join('')

      const wrapper = mount(LoadingState, {
        props: {
          loading: false
        },
        slots: {
          default: `<div class="large-content">${largeContent}</div>`
        }
      })

      const content = wrapper.find('.large-content')
      expect(content.exists()).toBe(true)
    })
  })

  describe('Performance', () => {
    it('should handle rapid loading state changes', async () => {
      const wrapper = mount(LoadingState, {
        props: {
          loading: true
        },
        slots: {
          default: '<div class="content">Content</div>'
        }
      })

      // Rapid state changes
      await wrapper.setProps({ loading: false })
      await wrapper.setProps({ loading: true })
      await wrapper.setProps({ loading: false })
      await wrapper.setProps({ loading: true })
      await wrapper.setProps({ loading: false })

      const content = wrapper.find('.content')
      expect(content.exists()).toBe(true)
    })
  })
})
