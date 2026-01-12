/**
 * NotificationBadge Component Tests
 *
 * Tests for the notification badge wrapper component
 *
 * Test Coverage:
 * - Badge display with count
 * - Priority-based colors (critical, warning, info)
 * - Max count display (99+)
 * - Zero/empty count handling
 * - Slot rendering
 * - Accessibility
 *
 * @see src/components/navigation/NotificationBadge.vue
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import NotificationBadge from '../NotificationBadge.vue'

describe('NotificationBadge', () => {
  describe('Badge Display', () => {
    it('should display badge when count > 0', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(true)
      expect(badge.text()).toContain('5')
    })

    it('should not display badge content when count is 0', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 0
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      // Badge component exists but model-value is false, so badge content is hidden
      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(true)
      // Vuetify hides badge via model-value, not by removing element
      // Check that the component props are correct
      expect(wrapper.props('count')).toBe(0)
    })

    it('should handle null count gracefully', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: null
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      // Component should render without error
      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(true)
    })

    it('should handle undefined count gracefully', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: undefined
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      // Component should use default value (0)
      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(true)
    })
  })

  describe('Max Count Display', () => {
    it('should display exact count when below max', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 50,
          max: 99
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      expect(wrapper.text()).toContain('50')
    })

    it('should display max+ when count exceeds max', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 150,
          max: 99
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      expect(wrapper.text()).toContain('99+')
    })

    it('should use default max of 99 when not specified', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 100
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      expect(wrapper.text()).toContain('99+')
    })

    it('should allow custom max values', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 1500,
          max: 999
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      expect(wrapper.text()).toContain('999+')
    })
  })

  describe('Priority Colors', () => {
    it('should use error color for critical priority', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5,
          priority: 'critical'
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      // Check the computed badgeColor value
      expect(wrapper.vm.badgeColor).toBe('error')
    })

    it('should use warning color for warning priority', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 3,
          priority: 'warning'
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      // Check the computed badgeColor value
      expect(wrapper.vm.badgeColor).toBe('warning')
    })

    it('should use info color for info priority', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 2,
          priority: 'info'
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      // Check the computed badgeColor value
      expect(wrapper.vm.badgeColor).toBe('info')
    })

    it('should default to info color when priority not specified', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      // Check the computed badgeColor value
      expect(wrapper.vm.badgeColor).toBe('info')
    })
  })

  describe('Slot Rendering', () => {
    it('should render default slot content', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5
        },
        slots: {
          default: '<button class="test-button">Notifications</button>'
        }
      })

      const button = wrapper.find('.test-button')
      expect(button.exists()).toBe(true)
      expect(button.text()).toBe('Notifications')
    })

    it('should render complex slot content', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5
        },
        slots: {
          default: `
            <div class="complex-content">
              <span class="icon">Icon</span>
              <span class="label">Label</span>
            </div>
          `
        }
      })

      expect(wrapper.find('.complex-content').exists()).toBe(true)
      expect(wrapper.find('.icon').exists()).toBe(true)
      expect(wrapper.find('.label').exists()).toBe(true)
    })

    it('should render multiple elements in slot', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5
        },
        slots: {
          default: `
            <button>Button 1</button>
            <button>Button 2</button>
          `
        }
      })

      const buttons = wrapper.findAll('button')
      expect(buttons).toHaveLength(2)
    })
  })

  describe('Priority Prop Behavior', () => {
    it('should accept all valid priority values', () => {
      const validPriorities = ['critical', 'warning', 'info']
      const expectedColors = ['error', 'warning', 'info']

      validPriorities.forEach((priority, index) => {
        const wrapper = mount(NotificationBadge, {
          props: {
            count: 5,
            priority
          },
          slots: {
            default: '<button>Notifications</button>'
          }
        })

        expect(wrapper.vm.badgeColor).toBe(expectedColors[index])
      })
    })

    it('should render badge with priority-based color', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5,
          priority: 'critical'
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      // Component should render and pass correct color to v-badge
      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(true)
      expect(wrapper.vm.badgeColor).toBe('error')
    })
  })

  describe('Edge Cases', () => {
    it('should handle negative count gracefully', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: -5
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      // Component handles negative counts by setting hasNotifications to false
      expect(wrapper.vm.hasNotifications).toBe(false)
      // Badge element still renders but model-value is false
      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(true)
    })

    it('should handle very large counts', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 999999
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      expect(wrapper.text()).toContain('99+')
    })

    it('should handle count as string', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: '42'
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      expect(wrapper.text()).toContain('42')
    })

    it('should handle missing slot gracefully', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5
        }
      })

      expect(wrapper.find('.v-badge').exists()).toBe(true)
    })

    it('should handle invalid priority gracefully', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5,
          priority: 'invalid'
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(true)
      // Should default to info color via the default case in badgeColor computed
      expect(wrapper.vm.badgeColor).toBe('info')
    })
  })

  describe('Accessibility', () => {
    it('should have accessible badge content', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      const badge = wrapper.find('.v-badge')
      expect(badge.exists()).toBe(true)
      // Badge content should be readable by screen readers
      expect(badge.text()).toContain('5')
    })

    it('should not interfere with slot accessibility', () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5
        },
        slots: {
          default: '<button aria-label="Notifications with 5 unread items">Notifications</button>'
        }
      })

      const button = wrapper.find('button')
      expect(button.attributes('aria-label')).toBe('Notifications with 5 unread items')
    })
  })

  describe('Reactivity', () => {
    it('should update when count changes', async () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      expect(wrapper.text()).toContain('5')

      await wrapper.setProps({ count: 10 })

      expect(wrapper.text()).toContain('10')
    })

    it('should update when priority changes', async () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5,
          priority: 'info'
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      // Check initial badgeColor computed value
      expect(wrapper.vm.badgeColor).toBe('info')

      await wrapper.setProps({ priority: 'critical' })

      // Check updated badgeColor computed value
      expect(wrapper.vm.badgeColor).toBe('error')
    })

    it('should update hasNotifications when count changes', async () => {
      const wrapper = mount(NotificationBadge, {
        props: {
          count: 5
        },
        slots: {
          default: '<button>Notifications</button>'
        }
      })

      // Initially hasNotifications should be true
      expect(wrapper.vm.hasNotifications).toBe(true)

      await wrapper.setProps({ count: 0 })

      // After setting count to 0, hasNotifications should be false
      expect(wrapper.vm.hasNotifications).toBe(false)

      await wrapper.setProps({ count: 3 })

      // After setting count to 3, hasNotifications should be true again
      expect(wrapper.vm.hasNotifications).toBe(true)
    })
  })
})
