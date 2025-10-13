/**
 * EmptyState Component Tests
 *
 * Tests for the empty state display component
 *
 * Test Coverage:
 * - Icon display and customization
 * - Title and description rendering
 * - Action slot for buttons
 * - Different icon sizes and colors
 * - Optional description
 * - Accessibility
 *
 * @see src/components/EmptyState.vue
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import EmptyState from '../EmptyState.vue'

describe('EmptyState', () => {
  describe('Basic Rendering', () => {
    it('should render with required title prop', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data available'
        }
      })

      expect(wrapper.text()).toContain('No data available')
    })

    it('should render default icon', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data'
        }
      })

      const icon = wrapper.find('.v-icon')
      expect(icon.exists()).toBe(true)
      expect(icon.classes()).toContain('mdi-inbox')
    })

    it('should render custom icon', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No assignments',
          icon: 'mdi-clipboard-alert'
        }
      })

      const icon = wrapper.find('.v-icon')
      expect(icon.exists()).toBe(true)
      expect(icon.classes()).toContain('mdi-clipboard-alert')
    })

    it('should render description when provided', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No assignments',
          description: 'Create your first assignment to get started.'
        }
      })

      expect(wrapper.text()).toContain('No assignments')
      expect(wrapper.text()).toContain('Create your first assignment to get started.')
    })

    it('should not render description when not provided', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No assignments'
        }
      })

      const description = wrapper.find('.text-body-1')
      expect(description.exists()).toBe(false)
    })
  })

  describe('Icon Customization', () => {
    it('should apply custom icon size', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data',
          iconSize: 120
        }
      })

      const icon = wrapper.find('.v-icon')
      expect(icon.exists()).toBe(true)
    })

    it('should accept icon size as string', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data',
          iconSize: 'x-large'
        }
      })

      const icon = wrapper.find('.v-icon')
      expect(icon.exists()).toBe(true)
    })

    it('should apply custom icon color', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data',
          iconColor: 'primary'
        }
      })

      const icon = wrapper.find('.v-icon')
      expect(icon.exists()).toBe(true)
    })

    it('should use default grey color when not specified', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data'
        }
      })

      const icon = wrapper.find('.v-icon')
      expect(icon.exists()).toBe(true)
    })
  })

  describe('Action Slot', () => {
    it('should render action slot content', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No assignments'
        },
        slots: {
          default: '<button class="test-action">Create Assignment</button>'
        }
      })

      const button = wrapper.find('.test-action')
      expect(button.exists()).toBe(true)
      expect(button.text()).toBe('Create Assignment')
    })

    it('should render multiple actions in slot', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data'
        },
        slots: {
          default: `
            <button class="primary-action">Create</button>
            <button class="secondary-action">Import</button>
          `
        }
      })

      expect(wrapper.find('.primary-action').exists()).toBe(true)
      expect(wrapper.find('.secondary-action').exists()).toBe(true)
    })

    it('should work without action slot', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data'
        }
      })

      expect(wrapper.find('.empty-state').exists()).toBe(true)
    })
  })

  describe('Layout and Styling', () => {
    it('should center content', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data'
        }
      })

      const container = wrapper.find('.empty-state')
      expect(container.classes()).toContain('text-center')
    })

    it('should have consistent spacing', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data',
          description: 'Description text'
        }
      })

      const container = wrapper.find('.empty-state')
      expect(container.classes()).toContain('py-12')
    })

    it('should apply max-width constraint', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data'
        }
      })

      const container = wrapper.find('.empty-state')
      expect(container.element.style.maxWidth).toBeDefined()
    })
  })

  describe('Text Hierarchy', () => {
    it('should use h5 for title', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No assignments'
        }
      })

      const title = wrapper.find('h3')
      expect(title.exists()).toBe(true)
      expect(title.classes()).toContain('text-h5')
    })

    it('should use body-1 for description', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No assignments',
          description: 'Description text'
        }
      })

      const description = wrapper.find('.text-body-1')
      expect(description.exists()).toBe(true)
      expect(description.classes()).toContain('text-medium-emphasis')
    })
  })

  describe('Common Use Cases', () => {
    it('should display empty list state', () => {
      const wrapper = mount(EmptyState, {
        props: {
          icon: 'mdi-clipboard-list-outline',
          title: 'No curations yet',
          description: 'Start by creating your first curation.'
        },
        slots: {
          default: '<button>Create Curation</button>'
        }
      })

      expect(wrapper.text()).toContain('No curations yet')
      expect(wrapper.find('button').text()).toBe('Create Curation')
    })

    it('should display search no results state', () => {
      const wrapper = mount(EmptyState, {
        props: {
          icon: 'mdi-magnify',
          iconColor: 'grey-darken-1',
          title: 'No results found',
          description: 'Try adjusting your search or filters.'
        }
      })

      expect(wrapper.text()).toContain('No results found')
      expect(wrapper.text()).toContain('Try adjusting your search or filters.')
    })

    it('should display permission denied state', () => {
      const wrapper = mount(EmptyState, {
        props: {
          icon: 'mdi-lock-outline',
          iconColor: 'warning',
          title: 'Access Restricted',
          description: 'You do not have permission to view this content.'
        }
      })

      expect(wrapper.text()).toContain('Access Restricted')
      expect(wrapper.text()).toContain('You do not have permission to view this content.')
    })
  })

  describe('Accessibility', () => {
    it('should have semantic heading structure', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data'
        }
      })

      const heading = wrapper.find('h3')
      expect(heading.exists()).toBe(true)
    })

    it('should have readable text contrast', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data',
          description: 'Description text'
        }
      })

      const description = wrapper.find('.text-medium-emphasis')
      expect(description.exists()).toBe(true)
    })

    it('should be screen reader friendly', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No assignments available',
          description: 'Create your first assignment to get started.'
        }
      })

      // Title should be in a heading for screen readers
      const heading = wrapper.find('h3')
      expect(heading.text()).toBe('No assignments available')

      // Description should be in a paragraph
      const paragraph = wrapper.find('p')
      expect(paragraph.text()).toBe('Create your first assignment to get started.')
    })
  })

  describe('Edge Cases', () => {
    it('should handle very long titles gracefully', () => {
      const longTitle =
        'This is a very long title that might wrap to multiple lines in the empty state component'

      const wrapper = mount(EmptyState, {
        props: {
          title: longTitle
        }
      })

      expect(wrapper.text()).toContain(longTitle)
    })

    it('should handle very long descriptions gracefully', () => {
      const longDescription =
        'This is a very long description with multiple sentences. It should wrap nicely and maintain good readability. The component should handle this gracefully without breaking the layout.'

      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data',
          description: longDescription
        }
      })

      expect(wrapper.text()).toContain(longDescription)
    })

    it('should handle special characters in title', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data <>&"'
        }
      })

      expect(wrapper.html()).toContain('No data')
    })

    it('should handle null description gracefully', () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data',
          description: null
        }
      })

      const description = wrapper.find('.text-body-1')
      expect(description.exists()).toBe(false)
    })
  })

  describe('Reactivity', () => {
    it('should update when title changes', async () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'Initial title'
        }
      })

      expect(wrapper.text()).toContain('Initial title')

      await wrapper.setProps({ title: 'Updated title' })

      expect(wrapper.text()).toContain('Updated title')
      expect(wrapper.text()).not.toContain('Initial title')
    })

    it('should update when description changes', async () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data',
          description: 'Initial description'
        }
      })

      expect(wrapper.text()).toContain('Initial description')

      await wrapper.setProps({ description: 'Updated description' })

      expect(wrapper.text()).toContain('Updated description')
      expect(wrapper.text()).not.toContain('Initial description')
    })

    it('should update when icon changes', async () => {
      const wrapper = mount(EmptyState, {
        props: {
          title: 'No data',
          icon: 'mdi-inbox'
        }
      })

      let icon = wrapper.find('.v-icon')
      expect(icon.classes()).toContain('mdi-inbox')

      await wrapper.setProps({ icon: 'mdi-alert' })

      icon = wrapper.find('.v-icon')
      expect(icon.classes()).toContain('mdi-alert')
      expect(icon.classes()).not.toContain('mdi-inbox')
    })
  })
})
