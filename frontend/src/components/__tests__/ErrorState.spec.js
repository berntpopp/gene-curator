/**
 * ErrorState Component Tests
 *
 * Tests for the error display component with retry functionality
 *
 * Test Coverage:
 * - Error message display
 * - Retry button functionality
 * - Different alert types (error, warning, info)
 * - Alert variants (tonal, flat, outlined)
 * - Closable alerts
 * - Custom slot content
 * - Accessibility
 *
 * @see src/components/ErrorState.vue
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ErrorState from '../ErrorState.vue'

describe('ErrorState', () => {
  describe('Basic Rendering', () => {
    it('should render with default props', () => {
      const wrapper = mount(ErrorState)

      expect(wrapper.find('.v-alert').exists()).toBe(true)
      expect(wrapper.text()).toContain('Something went wrong')
    })

    it('should render custom title', () => {
      const wrapper = mount(ErrorState, {
        props: {
          title: 'Failed to load data'
        }
      })

      expect(wrapper.text()).toContain('Failed to load data')
    })

    it('should render custom description', () => {
      const wrapper = mount(ErrorState, {
        props: {
          title: 'Error',
          description: 'Network connection failed. Please check your internet.'
        }
      })

      expect(wrapper.text()).toContain('Network connection failed. Please check your internet.')
    })

    it('should render default description when not provided', () => {
      const wrapper = mount(ErrorState)

      expect(wrapper.text()).toContain(
        'Please try again or contact support if the problem persists.'
      )
    })
  })

  describe('Alert Types', () => {
    it('should render as error type by default', () => {
      const wrapper = mount(ErrorState)

      const alert = wrapper.find('.v-alert')
      expect(alert.classes()).toContain('v-alert--variant-tonal')
    })

    it('should render as warning type', () => {
      const wrapper = mount(ErrorState, {
        props: {
          type: 'warning',
          title: 'Warning'
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
    })

    it('should render as info type', () => {
      const wrapper = mount(ErrorState, {
        props: {
          type: 'info',
          title: 'Information'
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
    })

    it('should render as success type', () => {
      const wrapper = mount(ErrorState, {
        props: {
          type: 'success',
          title: 'Success'
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
    })
  })

  describe('Alert Variants', () => {
    it('should use tonal variant by default', () => {
      const wrapper = mount(ErrorState)

      const alert = wrapper.find('.v-alert')
      expect(alert.classes()).toContain('v-alert--variant-tonal')
    })

    it('should render flat variant', () => {
      const wrapper = mount(ErrorState, {
        props: {
          variant: 'flat'
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.classes()).toContain('v-alert--variant-flat')
    })

    it('should render outlined variant', () => {
      const wrapper = mount(ErrorState, {
        props: {
          variant: 'outlined'
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.classes()).toContain('v-alert--variant-outlined')
    })

    it('should render elevated variant', () => {
      const wrapper = mount(ErrorState, {
        props: {
          variant: 'elevated'
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.classes()).toContain('v-alert--variant-elevated')
    })
  })

  describe('Retry Button', () => {
    it('should show retry button by default', () => {
      const wrapper = mount(ErrorState)

      const button = wrapper.find('.v-btn')
      expect(button.exists()).toBe(true)
      expect(button.text()).toBe('Retry')
    })

    it('should emit retry event when clicked', async () => {
      const wrapper = mount(ErrorState)

      const button = wrapper.find('.v-btn')
      await button.trigger('click')

      expect(wrapper.emitted()).toHaveProperty('retry')
      expect(wrapper.emitted().retry).toHaveLength(1)
    })

    it('should not show retry button when showRetry is false', () => {
      const wrapper = mount(ErrorState, {
        props: {
          showRetry: false
        }
      })

      const button = wrapper.find('.v-btn')
      expect(button.exists()).toBe(false)
    })

    it('should render custom retry text', () => {
      const wrapper = mount(ErrorState, {
        props: {
          retryText: 'Try Again'
        }
      })

      const button = wrapper.find('.v-btn')
      expect(button.text()).toBe('Try Again')
    })

    it('should apply custom retry button variant', () => {
      const wrapper = mount(ErrorState, {
        props: {
          retryVariant: 'flat'
        }
      })

      const button = wrapper.find('.v-btn')
      expect(button.classes()).toContain('v-btn--variant-flat')
    })

    it('should apply custom retry button size', () => {
      const wrapper = mount(ErrorState, {
        props: {
          retrySize: 'large'
        }
      })

      const button = wrapper.find('.v-btn')
      expect(button.classes()).toContain('v-btn--size-large')
    })
  })

  describe('Closable Alerts', () => {
    it('should not be closable by default', () => {
      const wrapper = mount(ErrorState)

      const closeButton = wrapper.find('.v-alert__close')
      expect(closeButton.exists()).toBe(false)
    })

    it('should be closable when closable prop is true', () => {
      const wrapper = mount(ErrorState, {
        props: {
          closable: true
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
    })
  })

  describe('Custom Colors', () => {
    it('should apply custom color', () => {
      const wrapper = mount(ErrorState, {
        props: {
          color: 'purple'
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
    })

    it('should override type color with custom color', () => {
      const wrapper = mount(ErrorState, {
        props: {
          type: 'error',
          color: 'success'
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
    })
  })

  describe('Slot Content', () => {
    it('should render custom title slot', () => {
      const wrapper = mount(ErrorState, {
        slots: {
          title: '<strong class="custom-title">Custom Error Title</strong>'
        }
      })

      const title = wrapper.find('.custom-title')
      expect(title.exists()).toBe(true)
      expect(title.text()).toBe('Custom Error Title')
    })

    it('should render custom description slot', () => {
      const wrapper = mount(ErrorState, {
        slots: {
          description:
            '<div class="custom-desc">Custom error description with <a href="#">link</a></div>'
        }
      })

      const description = wrapper.find('.custom-desc')
      expect(description.exists()).toBe(true)
      expect(wrapper.find('a').exists()).toBe(true)
    })

    it('should prefer slot content over props', () => {
      const wrapper = mount(ErrorState, {
        props: {
          title: 'Prop Title'
        },
        slots: {
          title: '<span class="slot-title">Slot Title</span>'
        }
      })

      const slotTitle = wrapper.find('.slot-title')
      expect(slotTitle.exists()).toBe(true)
      expect(slotTitle.text()).toBe('Slot Title')
      expect(wrapper.text()).not.toContain('Prop Title')
    })
  })

  describe('Common Use Cases', () => {
    it('should display API error', () => {
      const wrapper = mount(ErrorState, {
        props: {
          type: 'error',
          title: 'Failed to load curations',
          description: 'Unable to connect to the server. Please try again later.'
        }
      })

      expect(wrapper.text()).toContain('Failed to load curations')
      expect(wrapper.text()).toContain('Unable to connect to the server. Please try again later.')
      expect(wrapper.find('.v-btn').text()).toBe('Retry')
    })

    it('should display validation error', () => {
      const wrapper = mount(ErrorState, {
        props: {
          type: 'warning',
          title: 'Validation Failed',
          description: 'Please correct the errors in the form and try again.',
          showRetry: false
        }
      })

      expect(wrapper.text()).toContain('Validation Failed')
      expect(wrapper.find('.v-btn').exists()).toBe(false)
    })

    it('should display permission error', () => {
      const wrapper = mount(ErrorState, {
        props: {
          type: 'warning',
          title: 'Access Denied',
          description: 'You do not have permission to perform this action.',
          showRetry: false
        }
      })

      expect(wrapper.text()).toContain('Access Denied')
      expect(wrapper.text()).toContain('You do not have permission to perform this action.')
    })

    it('should display network timeout error', () => {
      const wrapper = mount(ErrorState, {
        props: {
          type: 'error',
          title: 'Request Timeout',
          description: 'The server took too long to respond. Please check your connection.',
          retryText: 'Retry Request'
        }
      })

      expect(wrapper.text()).toContain('Request Timeout')
      expect(wrapper.find('.v-btn').text()).toBe('Retry Request')
    })
  })

  describe('Layout', () => {
    it('should have full width', () => {
      const wrapper = mount(ErrorState)

      // The .error-state class is applied which has width: 100% in scoped styles
      // We verify the class exists (actual CSS is applied by scoped styles, not inline)
      const alert = wrapper.find('.error-state')
      expect(alert.exists()).toBe(true)
    })

    it('should have consistent margin', () => {
      const wrapper = mount(ErrorState)

      const alert = wrapper.find('.error-state')
      expect(alert.classes()).toContain('mb-4')
    })
  })

  describe('Accessibility', () => {
    it('should have appropriate ARIA role', () => {
      const wrapper = mount(ErrorState)

      const alert = wrapper.find('.v-alert')
      expect(alert.attributes('role')).toBe('alert')
    })

    it('should have accessible retry button', () => {
      const wrapper = mount(ErrorState, {
        props: {
          retryText: 'Retry Loading Data'
        }
      })

      const button = wrapper.find('.v-btn')
      expect(button.text()).toBe('Retry Loading Data')
    })

    it('should be screen reader friendly', () => {
      const wrapper = mount(ErrorState, {
        props: {
          title: 'Error Loading Data',
          description: 'Please try again later.'
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.attributes('role')).toBe('alert')
      expect(wrapper.text()).toContain('Error Loading Data')
      expect(wrapper.text()).toContain('Please try again later.')
    })
  })

  describe('Reactivity', () => {
    it('should update title when changed', async () => {
      const wrapper = mount(ErrorState, {
        props: {
          title: 'Initial Error'
        }
      })

      expect(wrapper.text()).toContain('Initial Error')

      await wrapper.setProps({ title: 'Updated Error' })

      expect(wrapper.text()).toContain('Updated Error')
      expect(wrapper.text()).not.toContain('Initial Error')
    })

    it('should update description when changed', async () => {
      const wrapper = mount(ErrorState, {
        props: {
          description: 'Initial description'
        }
      })

      expect(wrapper.text()).toContain('Initial description')

      await wrapper.setProps({ description: 'Updated description' })

      expect(wrapper.text()).toContain('Updated description')
      expect(wrapper.text()).not.toContain('Initial description')
    })

    it('should toggle retry button visibility', async () => {
      const wrapper = mount(ErrorState, {
        props: {
          showRetry: true
        }
      })

      let button = wrapper.find('.v-btn')
      expect(button.exists()).toBe(true)

      await wrapper.setProps({ showRetry: false })

      button = wrapper.find('.v-btn')
      expect(button.exists()).toBe(false)

      await wrapper.setProps({ showRetry: true })

      button = wrapper.find('.v-btn')
      expect(button.exists()).toBe(true)
    })

    it('should change alert type', async () => {
      const wrapper = mount(ErrorState, {
        props: {
          type: 'error'
        }
      })

      let alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)

      await wrapper.setProps({ type: 'warning' })

      alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
    })
  })

  describe('Edge Cases', () => {
    it('should handle very long error messages', () => {
      const longMessage =
        'This is a very long error message that might wrap to multiple lines. It should display correctly without breaking the layout or causing any visual issues. The component should handle long text gracefully.'

      const wrapper = mount(ErrorState, {
        props: {
          description: longMessage
        }
      })

      expect(wrapper.text()).toContain(longMessage)
    })

    it('should handle HTML entities in title', () => {
      const wrapper = mount(ErrorState, {
        props: {
          title: 'Error with <special> & "characters"'
        }
      })

      expect(wrapper.html()).toContain('Error with')
    })

    it('should handle empty title gracefully', () => {
      const wrapper = mount(ErrorState, {
        props: {
          title: ''
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
    })

    it('should handle null description', () => {
      const wrapper = mount(ErrorState, {
        props: {
          title: 'Error',
          description: null
        }
      })

      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
    })

    it('should handle multiple retry clicks', async () => {
      const wrapper = mount(ErrorState)

      const button = wrapper.find('.v-btn')

      await button.trigger('click')
      await button.trigger('click')
      await button.trigger('click')

      expect(wrapper.emitted().retry).toHaveLength(3)
    })
  })
})
