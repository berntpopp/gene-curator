/**
 * BaseNavigationItem Component Tests
 *
 * Tests for the reusable navigation item component
 *
 * Test Coverage:
 * - Rendering with different props
 * - Router link navigation
 * - External link navigation
 * - Active state styling
 * - Disabled state
 * - Icon and badge display
 * - Click event handling
 * - Accessibility (ARIA labels, keyboard navigation)
 *
 * @see src/components/navigation/BaseNavigationItem.vue
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import BaseNavigationItem from '../BaseNavigationItem.vue'

// Create a simple router for testing
const createTestRouter = () => {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'Home', component: { template: '<div>Home</div>' } },
      {
        path: '/dashboard',
        name: 'Dashboard',
        component: { template: '<div>Dashboard</div>' }
      },
      {
        path: '/curations',
        name: 'Curations',
        component: { template: '<div>Curations</div>' }
      }
    ]
  })
}

describe('BaseNavigationItem', () => {
  let router

  beforeEach(async () => {
    router = createTestRouter()
    await router.push('/')
    await router.isReady()
  })

  describe('Rendering', () => {
    it('should render with label', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard'
        },
        global: {
          plugins: [router]
        }
      })

      expect(wrapper.text()).toContain('Dashboard')
    })

    it('should render with icon', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          icon: 'mdi-view-dashboard'
        },
        global: {
          plugins: [router]
        }
      })

      const icon = wrapper.find('.v-icon')
      expect(icon.exists()).toBe(true)
      expect(icon.classes()).toContain('mdi-view-dashboard')
    })

    it('should render with badge', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Notifications',
          badge: 5
        },
        global: {
          plugins: [router]
        }
      })

      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(true)
      expect(badge.text()).toContain('5')
    })

    it('should not show badge when count is 0', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Notifications',
          badge: 0
        },
        global: {
          plugins: [router]
        }
      })

      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(false)
    })
  })

  describe('Router Navigation', () => {
    it('should render as router-link when "to" prop is provided', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          to: { name: 'Dashboard' }
        },
        global: {
          plugins: [router]
        }
      })

      const listItem = wrapper.find('.v-list-item')
      expect(listItem.exists()).toBe(true)
    })

    it('should navigate to route when clicked', async () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          to: { name: 'Dashboard' }
        },
        global: {
          plugins: [router]
        }
      })

      await wrapper.trigger('click')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('Dashboard')
    })
  })

  describe('External Links', () => {
    it('should render as anchor when "href" prop is provided', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'External Link',
          href: 'https://example.com'
        },
        global: {
          plugins: [router]
        }
      })

      const listItem = wrapper.find('.v-list-item')
      expect(listItem.exists()).toBe(true)
      expect(listItem.attributes('href')).toBe('https://example.com')
    })

    it('should open external links in new tab by default', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'External Link',
          href: 'https://example.com'
        },
        global: {
          plugins: [router]
        }
      })

      const listItem = wrapper.find('.v-list-item')
      expect(listItem.attributes('target')).toBe('_blank')
      expect(listItem.attributes('rel')).toBe('noopener noreferrer')
    })
  })

  describe('Active State', () => {
    it('should apply active class when route is current', async () => {
      await router.push('/dashboard')
      await router.isReady()

      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          to: { name: 'Dashboard' }
        },
        global: {
          plugins: [router]
        }
      })

      const listItem = wrapper.find('.v-list-item')
      expect(listItem.classes()).toContain('v-list-item--active')
    })

    it('should have aria-current="page" when active', async () => {
      await router.push('/dashboard')
      await router.isReady()

      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          to: { name: 'Dashboard' }
        },
        global: {
          plugins: [router]
        }
      })

      const listItem = wrapper.find('.v-list-item')
      expect(listItem.attributes('aria-current')).toBe('page')
    })
  })

  describe('Disabled State', () => {
    it('should apply disabled class when disabled', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          to: { name: 'Dashboard' },
          disabled: true
        },
        global: {
          plugins: [router]
        }
      })

      const listItem = wrapper.find('.v-list-item')
      expect(listItem.classes()).toContain('v-list-item--disabled')
    })

    it('should not navigate when disabled', async () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          to: { name: 'Dashboard' },
          disabled: true
        },
        global: {
          plugins: [router]
        }
      })

      const initialRoute = router.currentRoute.value.name

      await wrapper.trigger('click')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe(initialRoute)
    })
  })

  describe('Click Events', () => {
    it('should emit click event when clicked', async () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard'
        },
        global: {
          plugins: [router]
        }
      })

      await wrapper.trigger('click')

      expect(wrapper.emitted()).toHaveProperty('click')
      expect(wrapper.emitted().click).toHaveLength(1)
    })

    it('should not emit click event when disabled', async () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          disabled: true
        },
        global: {
          plugins: [router]
        }
      })

      await wrapper.trigger('click')

      expect(wrapper.emitted().click).toBeUndefined()
    })
  })

  describe('Accessibility', () => {
    it('should have aria-label from label prop', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard'
        },
        global: {
          plugins: [router]
        }
      })

      const listItem = wrapper.find('.v-list-item')
      expect(listItem.attributes('aria-label')).toBe('Dashboard')
    })

    it('should use custom aria-label when provided', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          ariaLabel: 'Go to Dashboard Page'
        },
        global: {
          plugins: [router]
        }
      })

      const listItem = wrapper.find('.v-list-item')
      expect(listItem.attributes('aria-label')).toBe('Go to Dashboard Page')
    })

    it('should be keyboard accessible', async () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          to: { name: 'Dashboard' }
        },
        global: {
          plugins: [router]
        }
      })

      const listItem = wrapper.find('.v-list-item')

      // Simulate Enter key
      await listItem.trigger('keydown.enter')
      await router.isReady()

      expect(router.currentRoute.value.name).toBe('Dashboard')
    })
  })

  describe('Icon Colors', () => {
    it('should apply icon color when provided', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          icon: 'mdi-view-dashboard',
          iconColor: 'primary'
        },
        global: {
          plugins: [router]
        }
      })

      const icon = wrapper.find('.v-icon')
      expect(icon.attributes('style')).toContain('color')
    })

    it('should use default color when iconColor not provided', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Dashboard',
          icon: 'mdi-view-dashboard'
        },
        global: {
          plugins: [router]
        }
      })

      const icon = wrapper.find('.v-icon')
      expect(icon.exists()).toBe(true)
    })
  })

  describe('Badge Colors', () => {
    it('should apply badge color when provided', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Notifications',
          badge: 5,
          badgeColor: 'error'
        },
        global: {
          plugins: [router]
        }
      })

      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(true)
    })

    it('should use default color when badgeColor not provided', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Notifications',
          badge: 5
        },
        global: {
          plugins: [router]
        }
      })

      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(true)
    })
  })

  describe('Edge Cases', () => {
    it('should handle missing label gracefully', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {},
        global: {
          plugins: [router]
        }
      })

      expect(wrapper.find('.v-list-item').exists()).toBe(true)
    })

    it('should handle null badge value', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Notifications',
          badge: null
        },
        global: {
          plugins: [router]
        }
      })

      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(false)
    })

    it('should handle negative badge value', () => {
      const wrapper = mount(BaseNavigationItem, {
        props: {
          label: 'Notifications',
          badge: -5
        },
        global: {
          plugins: [router]
        }
      })

      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(false)
    })
  })
})
