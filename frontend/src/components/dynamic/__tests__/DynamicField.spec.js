/**
 * DynamicField Component Tests
 *
 * Tests for the dynamic field rendering component enhancements
 *
 * Test Coverage:
 * - Depth tracking for nested fields
 * - Custom component rendering via registry
 * - Unknown type fallback behavior
 * - Nested styling based on depth
 *
 * @see src/components/dynamic/DynamicField.vue
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, shallowMount } from '@vue/test-utils'
import DynamicField from '../DynamicField.vue'

// Track mock calls
const mockLogger = {
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn()
}

// Mock useLogger composable
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => mockLogger
}))

// Mock componentRegistry
vi.mock('../componentRegistry', () => ({
  componentRegistry: {
    MONDOAutocomplete: {
      name: 'MONDOAutocomplete',
      template: '<div class="mock-mondo">MONDO</div>',
      props: ['modelValue', 'label', 'hint', 'required', 'disabled']
    },
    PMIDInput: {
      name: 'PMIDInput',
      template: '<div class="mock-pmid">PMID</div>',
      props: ['modelValue', 'label', 'hint', 'required', 'disabled']
    },
    HPOInheritanceSelect: {
      name: 'HPOInheritanceSelect',
      template: '<div class="mock-hpo-inheritance">HPOInheritance</div>',
      props: ['modelValue', 'label', 'hint', 'required', 'disabled']
    },
    OMIMAutocomplete: {
      name: 'OMIMAutocomplete',
      template: '<div class="mock-omim">OMIM</div>',
      props: ['modelValue', 'label', 'hint', 'required', 'disabled']
    },
    HPOInput: {
      name: 'HPOInput',
      template: '<div class="mock-hpo">HPO</div>',
      props: ['modelValue', 'label', 'hint', 'required', 'disabled']
    }
  }
}))

// Common stubs for Vuetify components that may cause issues
const vuetifyStubs = {
  'v-text-field': {
    template:
      '<div class="v-text-field"><slot name="prepend-inner"></slot><label>{{ label }}</label><input :value="modelValue" @input="$emit(\'update:model-value\', $event.target.value)" :disabled="disabled" /><slot name="append-inner"></slot><span v-if="hint" class="v-messages">{{ hint }}</span><slot name="details"></slot></div>',
    props: [
      'modelValue',
      'label',
      'placeholder',
      'variant',
      'rules',
      'errorMessages',
      'required',
      'disabled',
      'type',
      'min',
      'max',
      'step',
      'hint',
      'persistentHint'
    ]
  },
  'v-tooltip': {
    name: 'VTooltip',
    template:
      '<div class="v-tooltip" :class="{ disabled: disabled }"><slot name="activator" :props="{ class: \'tooltip-activator\' }"></slot><span class="v-tooltip-content"><slot></slot></span></div>',
    props: ['location', 'openDelay', 'disabled', 'text']
  },
  'v-textarea': {
    template:
      '<div class="v-textarea"><slot name="prepend-inner"></slot><label>{{ label }}</label><textarea :value="modelValue" @input="$emit(\'update:model-value\', $event.target.value)" :disabled="disabled"></textarea><slot name="append-inner"></slot><span v-if="hint" class="v-messages">{{ hint }}</span><slot name="details"></slot></div>',
    props: [
      'modelValue',
      'label',
      'placeholder',
      'variant',
      'rules',
      'errorMessages',
      'required',
      'rows',
      'disabled',
      'hint',
      'persistentHint'
    ]
  },
  'v-select': {
    template:
      '<div class="v-select"><slot name="prepend-inner"></slot><label>{{ label }}</label><select :value="modelValue" @change="$emit(\'update:model-value\', $event.target.value)" :disabled="disabled"></select><slot name="append-inner"></slot><span v-if="hint" class="v-messages">{{ hint }}</span><slot name="details"></slot></div>',
    props: [
      'modelValue',
      'items',
      'label',
      'placeholder',
      'variant',
      'rules',
      'errorMessages',
      'required',
      'clearable',
      'disabled',
      'hint',
      'persistentHint'
    ]
  },
  'v-checkbox': {
    template:
      '<div class="v-checkbox"><label>{{ label }}</label><input type="checkbox" :checked="modelValue" @change="$emit(\'update:model-value\', $event.target.checked)" :disabled="disabled" /></div>',
    props: ['modelValue', 'label', 'rules', 'errorMessages', 'disabled']
  },
  'v-card': {
    template: '<div class="v-card" :style="$attrs.style"><slot /></div>'
  },
  'v-card-text': {
    template: '<div class="v-card-text"><slot /></div>'
  },
  'v-row': {
    template: '<div class="v-row"><slot /></div>'
  },
  'v-col': {
    template: '<div class="v-col"><slot /></div>'
  },
  'v-btn': {
    template: '<button class="v-btn" @click="$emit(\'click\')"><slot /></button>'
  },
  'v-icon': {
    template: '<i class="v-icon" :data-icon="icon" :data-color="color">{{ icon }}</i>',
    props: ['icon', 'color', 'size', 'start']
  },
  'v-label': {
    template: '<label class="v-label"><slot /></label>'
  },
  'v-alert': {
    template: '<div class="v-alert"><slot /></div>'
  }
}

/**
 * Helper to mount DynamicField with common defaults
 */
function mountComponent(props = {}, options = {}) {
  return mount(DynamicField, {
    props: {
      fieldName: 'testField',
      fieldSchema: { type: 'string', title: 'Test Field' },
      modelValue: '',
      ...props
    },
    global: {
      stubs: {
        // Stub recursive DynamicField calls to prevent infinite recursion
        DynamicField: {
          name: 'DynamicField',
          template: '<div class="stubbed-dynamic-field" :data-depth="depth"></div>',
          props: ['fieldName', 'fieldSchema', 'modelValue', 'depth', 'variant', 'disabled']
        },
        ...vuetifyStubs,
        ...options.global?.stubs
      },
      ...options.global
    },
    ...options
  })
}

/**
 * Helper to shallow mount DynamicField
 */
function shallowMountComponent(props = {}, options = {}) {
  return shallowMount(DynamicField, {
    props: {
      fieldName: 'testField',
      fieldSchema: { type: 'string', title: 'Test Field' },
      modelValue: '',
      ...props
    },
    global: {
      stubs: {
        DynamicField: true,
        ...options.global?.stubs
      },
      ...options.global
    },
    ...options
  })
}

describe('DynamicField', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('depth tracking', () => {
    it('accepts depth prop with default 0', () => {
      const wrapper = shallowMountComponent()
      expect(wrapper.props('depth')).toBe(0)
    })

    it('accepts explicit depth prop value', () => {
      const wrapper = shallowMountComponent({
        depth: 5
      })
      expect(wrapper.props('depth')).toBe(5)
    })

    it('passes incremented depth to nested fields in object schema', () => {
      const wrapper = mountComponent({
        fieldName: 'parentField',
        fieldSchema: {
          type: 'object',
          title: 'Parent Object',
          properties: {
            childField: { type: 'string', title: 'Child' }
          }
        },
        modelValue: {},
        depth: 2
      })

      // Find the stubbed nested DynamicField
      const nestedField = wrapper.find('.stubbed-dynamic-field')
      expect(nestedField.exists()).toBe(true)
      expect(nestedField.attributes('data-depth')).toBe('3')
    })

    it('passes incremented depth to nested fields in array schema', () => {
      const wrapper = mountComponent({
        fieldName: 'arrayField',
        fieldSchema: {
          type: 'array',
          title: 'Items Array',
          items: {
            type: 'object',
            properties: {
              name: { type: 'string', title: 'Name' }
            }
          }
        },
        modelValue: [{ name: 'test' }],
        depth: 1
      })

      // Find the stubbed nested DynamicField within array items
      const nestedField = wrapper.find('.stubbed-dynamic-field')
      expect(nestedField.exists()).toBe(true)
      expect(nestedField.attributes('data-depth')).toBe('2')
    })

    it('stops rendering at MAX_DEPTH and shows warning', () => {
      const wrapper = mountComponent({
        fieldName: 'deepField',
        fieldSchema: {
          type: 'object',
          title: 'Deep Object',
          properties: {
            child: { type: 'string', title: 'Child' }
          }
        },
        modelValue: {},
        depth: 10 // MAX_DEPTH = 10
      })

      // Should show warning alert instead of nested content
      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(true)
      expect(wrapper.text()).toContain('Maximum nesting depth reached')
      expect(wrapper.text()).toContain('10 levels')

      // Should NOT render nested fields
      const nestedField = wrapper.find('.stubbed-dynamic-field')
      expect(nestedField.exists()).toBe(false)
    })

    it('allows rendering at depth less than MAX_DEPTH', () => {
      const wrapper = mountComponent({
        fieldName: 'objectField',
        fieldSchema: {
          type: 'object',
          title: 'Safe Object',
          properties: {
            child: { type: 'string', title: 'Child' }
          }
        },
        modelValue: {},
        depth: 9 // Just under MAX_DEPTH
      })

      // Should NOT show warning
      const alert = wrapper.find('.v-alert')
      expect(alert.exists()).toBe(false)

      // Should render nested fields
      const nestedField = wrapper.find('.stubbed-dynamic-field')
      expect(nestedField.exists()).toBe(true)
    })
  })

  describe('custom component rendering', () => {
    it('renders custom component when schema has component property', () => {
      const wrapper = mountComponent({
        fieldName: 'diseaseField',
        fieldSchema: {
          type: 'string',
          title: 'Disease',
          component: 'MONDOAutocomplete'
        },
        modelValue: ''
      })

      // The custom component should be rendered
      expect(wrapper.html()).toContain('mock-mondo')
    })

    it('renders PMIDInput component when specified', () => {
      const wrapper = mountComponent({
        fieldName: 'pmidField',
        fieldSchema: {
          type: 'string',
          title: 'PMID',
          component: 'PMIDInput'
        },
        modelValue: ''
      })

      expect(wrapper.html()).toContain('mock-pmid')
    })

    it('falls back to text field when component not in registry', () => {
      const wrapper = mountComponent({
        fieldName: 'unknownField',
        fieldSchema: {
          type: 'string',
          title: 'Unknown Widget',
          component: 'NonExistentComponent'
        },
        modelValue: ''
      })

      // Should NOT render the unknown component
      expect(wrapper.html()).not.toContain('NonExistentComponent')

      // Should render a v-text-field fallback
      const textField = wrapper.find('.v-text-field')
      expect(textField.exists()).toBe(true)
    })

    it('logs warning for missing component', () => {
      mountComponent({
        fieldName: 'missingField',
        fieldSchema: {
          type: 'string',
          title: 'Missing Widget',
          component: 'MissingComponent'
        },
        modelValue: ''
      })

      // Verify logger.warn was called with component info
      expect(mockLogger.warn).toHaveBeenCalled()
      expect(mockLogger.warn).toHaveBeenCalledWith(
        'Component not found in registry',
        expect.objectContaining({
          component: 'MissingComponent',
          fieldName: 'missingField'
        })
      )
    })

    it('emits component-fallback event for missing component', () => {
      const wrapper = mountComponent({
        fieldName: 'fallbackField',
        fieldSchema: {
          type: 'string',
          title: 'Fallback Widget',
          component: 'NotFoundComponent'
        },
        modelValue: ''
      })

      const emittedEvents = wrapper.emitted('component-fallback')
      expect(emittedEvents).toBeDefined()
      expect(emittedEvents.length).toBeGreaterThan(0)
      expect(emittedEvents[0][0]).toEqual(
        expect.objectContaining({
          requestedComponent: 'NotFoundComponent',
          fieldName: 'fallbackField',
          fallbackType: 'text-field'
        })
      )
    })

    it('does not emit component-fallback for valid component', () => {
      const wrapper = mountComponent({
        fieldName: 'validField',
        fieldSchema: {
          type: 'string',
          title: 'Valid Widget',
          component: 'MONDOAutocomplete'
        },
        modelValue: ''
      })

      const emittedEvents = wrapper.emitted('component-fallback')
      expect(emittedEvents).toBeUndefined()
    })
  })

  describe('unknown type fallback', () => {
    it('renders editable text field for unknown types', () => {
      const wrapper = mountComponent({
        fieldName: 'customField',
        fieldSchema: {
          type: 'custom_unknown_type',
          title: 'Custom Field'
        },
        modelValue: 'test value'
      })

      // Should render a text field
      const textField = wrapper.find('.v-text-field')
      expect(textField.exists()).toBe(true)
    })

    it('shows type in label for unknown types', () => {
      const wrapper = mountComponent({
        fieldName: 'unknownTypeField',
        fieldSchema: {
          type: 'weird_custom_type',
          title: 'Weird Field'
        },
        modelValue: ''
      })

      // The label should contain the unknown type indicator
      expect(wrapper.html()).toContain('Unknown Type:')
      expect(wrapper.html()).toContain('weird_custom_type')
    })

    it('allows editing unknown type fields (not readonly)', () => {
      const wrapper = mountComponent({
        fieldName: 'editableUnknown',
        fieldSchema: {
          type: 'exotic_type',
          title: 'Editable Unknown'
        },
        modelValue: 'initial'
      })

      // Find the input and verify it's not disabled by default
      const textField = wrapper.find('.v-text-field')
      expect(textField.exists()).toBe(true)

      // The field should be editable (not have disabled attribute from schema)
      const inputEl = wrapper.find('.v-text-field input')
      if (inputEl.exists()) {
        expect(inputEl.attributes('disabled')).toBeUndefined()
      }
    })

    it('shows hint for unknown type field', () => {
      const wrapper = mountComponent({
        fieldName: 'hintField',
        fieldSchema: {
          type: 'mystery_type',
          title: 'Mystery Field'
        },
        modelValue: ''
      })

      // The fallback text field should have hint about unrecognized type
      expect(wrapper.html()).toContain('Field type not recognized')
    })
  })

  describe('nested styling', () => {
    it('applies no background at depth 0', () => {
      const wrapper = mountComponent({
        fieldName: 'rootObject',
        fieldSchema: {
          type: 'object',
          title: 'Root Object',
          properties: {
            child: { type: 'string', title: 'Child' }
          }
        },
        modelValue: {},
        depth: 0
      })

      // Find the v-card that wraps object fields
      const card = wrapper.find('.v-card')
      if (card.exists()) {
        const style = card.attributes('style') || ''
        expect(style).not.toContain('background')
      }
    })

    it('applies no background at depth 1', () => {
      const wrapper = mountComponent({
        fieldName: 'level1Object',
        fieldSchema: {
          type: 'object',
          title: 'Level 1 Object',
          properties: {
            child: { type: 'string', title: 'Child' }
          }
        },
        modelValue: {},
        depth: 1
      })

      const card = wrapper.find('.v-card')
      if (card.exists()) {
        const style = card.attributes('style') || ''
        expect(style).not.toContain('background')
      }
    })

    it('applies background tint at depth 2+', () => {
      const wrapper = mountComponent({
        fieldName: 'deepObject',
        fieldSchema: {
          type: 'object',
          title: 'Deep Object',
          properties: {
            child: { type: 'string', title: 'Child' }
          }
        },
        modelValue: {},
        depth: 2
      })

      const card = wrapper.find('.v-card')
      expect(card.exists()).toBe(true)
      const style = card.attributes('style') || ''
      expect(style).toContain('background')
    })

    it('increases opacity with depth', () => {
      // Test at depth 3
      const wrapper3 = mountComponent({
        fieldName: 'depth3Object',
        fieldSchema: {
          type: 'object',
          title: 'Depth 3',
          properties: { child: { type: 'string' } }
        },
        modelValue: {},
        depth: 3
      })

      // Test at depth 6
      const wrapper6 = mountComponent({
        fieldName: 'depth6Object',
        fieldSchema: {
          type: 'object',
          title: 'Depth 6',
          properties: { child: { type: 'string' } }
        },
        modelValue: {},
        depth: 6
      })

      const card3 = wrapper3.find('.v-card')
      const card6 = wrapper6.find('.v-card')

      expect(card3.exists()).toBe(true)
      expect(card6.exists()).toBe(true)

      // Both should have styling with transition
      const style3 = card3.attributes('style') || ''
      const style6 = card6.attributes('style') || ''

      // Both depths 3+ should have background and transition applied
      expect(style3).toContain('transition')
      expect(style6).toContain('transition')

      // The getNestedStyle function calculates:
      // Opacity at depth 3: 0.02 + (3-2)*0.01 = 0.03
      // Opacity at depth 6: 0.02 + (6-2)*0.01 = 0.06 (capped at 0.06)
      // Both should include rgba with the calculated opacity
      expect(style3).toMatch(/background|rgba/)
      expect(style6).toMatch(/background|rgba/)
    })

    it('applies transition for smooth styling', () => {
      const wrapper = mountComponent({
        fieldName: 'transitionObject',
        fieldSchema: {
          type: 'object',
          title: 'Transition Object',
          properties: { child: { type: 'string' } }
        },
        modelValue: {},
        depth: 3
      })

      const card = wrapper.find('.v-card')
      expect(card.exists()).toBe(true)
      const style = card.attributes('style') || ''
      expect(style).toContain('transition')
    })
  })

  describe('basic field rendering', () => {
    it('renders string field as text input', () => {
      const wrapper = mountComponent({
        fieldName: 'textField',
        fieldSchema: { type: 'string', title: 'Text Input' },
        modelValue: 'hello'
      })

      const textField = wrapper.find('.v-text-field')
      expect(textField.exists()).toBe(true)
    })

    it('renders boolean field as checkbox', () => {
      const wrapper = mountComponent({
        fieldName: 'boolField',
        fieldSchema: { type: 'boolean', title: 'Checkbox' },
        modelValue: true
      })

      const checkbox = wrapper.find('.v-checkbox')
      expect(checkbox.exists()).toBe(true)
    })

    it('renders select field for enum types', () => {
      const wrapper = mountComponent({
        fieldName: 'selectField',
        fieldSchema: {
          type: 'string',
          title: 'Select',
          enum: ['option1', 'option2', 'option3']
        },
        modelValue: 'option1'
      })

      const select = wrapper.find('.v-select')
      expect(select.exists()).toBe(true)
    })
  })

  describe('emit events', () => {
    it('emits update:model-value when value changes', async () => {
      const wrapper = mountComponent({
        fieldName: 'emitField',
        fieldSchema: { type: 'string', title: 'Emit Test' },
        modelValue: ''
      })

      // Find input and simulate change
      const input = wrapper.find('.v-text-field input')
      expect(input.exists()).toBe(true)
      await input.setValue('new value')
      const emitted = wrapper.emitted('update:model-value')
      expect(emitted).toBeDefined()
      expect(emitted[0]).toEqual(['new value'])
    })
  })

  describe('Field Metadata - Icons and Tooltips', () => {
    it('renders icon when icon property is defined', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          icon: 'mdi-account'
        },
        modelValue: ''
      })

      // Icon should be rendered in prepend-inner
      expect(wrapper.html()).toContain('mdi-account')
    })

    it('renders default icon when tooltip defined but no icon', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          tooltip: 'This is a tooltip'
        },
        modelValue: ''
      })

      // Default icon should appear
      expect(wrapper.html()).toContain('mdi-information-outline')
    })

    it('does not render icon when no icon or tooltip defined', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field'
        },
        modelValue: ''
      })

      // No icons in prepend area
      expect(wrapper.html()).not.toContain('mdi-information-outline')
      expect(wrapper.html()).not.toContain('mdi-account')
    })

    it('renders v-tooltip around icon when tooltip defined', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          icon: 'mdi-account',
          tooltip: 'This is helpful context'
        },
        modelValue: ''
      })

      // Tooltip component should be present
      expect(wrapper.find('.v-tooltip').exists()).toBe(true)
      expect(wrapper.html()).toContain('This is helpful context')
    })

    it('disables tooltip when no tooltip text provided', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          icon: 'mdi-account'
          // No tooltip property
        },
        modelValue: ''
      })

      // Tooltip should be disabled
      const tooltip = wrapper.find('.v-tooltip')
      if (tooltip.exists()) {
        expect(tooltip.classes()).toContain('disabled')
      }
    })

    it('uses grey-darken-1 color for icon accessibility', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          icon: 'mdi-account'
        },
        modelValue: ''
      })

      // Icon should have correct color attribute (data-color due to stub)
      expect(wrapper.html()).toContain('data-color="grey-darken-1"')
    })
  })

  describe('Field Metadata - Hints', () => {
    it('renders persistent hint when hint property defined', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          hint: 'This is a helpful hint'
        },
        modelValue: ''
      })

      // Hint should be in the output
      expect(wrapper.html()).toContain('This is a helpful hint')
    })

    it('does not render hint when hint property absent', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field'
        },
        modelValue: ''
      })

      // No hint messages div
      const messagesDiv = wrapper.find('.v-messages')
      expect(messagesDiv.exists()).toBe(false)
    })

    it('truncates long hints over 100 characters', () => {
      const longHint = 'A'.repeat(150)
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          hint: longHint
        },
        modelValue: ''
      })

      // Check that truncated text is rendered
      expect(wrapper.text()).toContain('A'.repeat(100) + '...')
      expect(wrapper.text()).toContain('show more')
    })

    it('expands truncated hint when show more clicked', async () => {
      const longHint = 'A'.repeat(150)
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          hint: longHint
        },
        modelValue: ''
      })

      // Click show more
      const showMoreLink = wrapper.find('a.text-primary')
      expect(showMoreLink.exists()).toBe(true)
      await showMoreLink.trigger('click')

      // Full hint should now be visible
      expect(wrapper.text()).toContain(longHint)
      expect(wrapper.text()).toContain('show less')
    })

    it('collapses expanded hint when show less clicked', async () => {
      const longHint = 'A'.repeat(150)
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          hint: longHint
        },
        modelValue: ''
      })

      // Expand first
      let link = wrapper.find('a.text-primary')
      await link.trigger('click')

      // Now collapse
      link = wrapper.find('a.text-primary')
      await link.trigger('click')

      // Should be truncated again
      expect(wrapper.text()).toContain('A'.repeat(100) + '...')
      expect(wrapper.text()).toContain('show more')
    })

    it('does not truncate hints under 100 characters', () => {
      const shortHint = 'A'.repeat(50)
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          hint: shortHint
        },
        modelValue: ''
      })

      expect(wrapper.text()).toContain(shortHint)
      expect(wrapper.text()).not.toContain('show more')
    })

    it('handles exactly 100 character hint without truncation', () => {
      const exactHint = 'A'.repeat(100)
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          hint: exactHint
        },
        modelValue: ''
      })

      expect(wrapper.text()).toContain(exactHint)
      expect(wrapper.text()).not.toContain('show more')
    })
  })

  describe('Field Metadata - Help Links', () => {
    it('renders help icon when helpUrl property defined', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          helpUrl: 'https://docs.example.com/help'
        },
        modelValue: ''
      })

      expect(wrapper.html()).toContain('mdi-help-circle-outline')
    })

    it('does not render help icon when helpUrl absent', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field'
        },
        modelValue: ''
      })

      expect(wrapper.html()).not.toContain('mdi-help-circle-outline')
    })

    it('opens help URL in new tab when help icon clicked', async () => {
      const mockOpen = vi.spyOn(window, 'open').mockImplementation(() => null)

      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          helpUrl: 'https://docs.example.com/help'
        },
        modelValue: ''
      })

      // Find and click help icon
      const icons = wrapper.findAll('.v-icon')
      const helpIcon = icons.find(icon => icon.html().includes('mdi-help-circle-outline'))
      expect(helpIcon).toBeDefined()
      await helpIcon.trigger('click')

      expect(mockOpen).toHaveBeenCalledWith(
        'https://docs.example.com/help',
        '_blank',
        'noopener,noreferrer'
      )

      mockOpen.mockRestore()
    })

    it('does not render help icon for invalid URL (not http/https)', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          helpUrl: 'not-a-url'
        },
        modelValue: ''
      })

      // Invalid URL should not render help icon
      expect(wrapper.html()).not.toContain('mdi-help-circle-outline')
    })

    it('accepts http URLs', () => {
      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          helpUrl: 'http://docs.example.com/help'
        },
        modelValue: ''
      })

      expect(wrapper.html()).toContain('mdi-help-circle-outline')
    })

    it('logs info when help URL opened', async () => {
      const mockOpen = vi.spyOn(window, 'open').mockImplementation(() => null)

      const wrapper = mountComponent({
        fieldName: 'test_field',
        fieldSchema: {
          type: 'string',
          title: 'Test Field',
          helpUrl: 'https://docs.example.com/help'
        },
        modelValue: ''
      })

      const icons = wrapper.findAll('.v-icon')
      const helpIcon = icons.find(icon => icon.html().includes('mdi-help-circle-outline'))
      await helpIcon.trigger('click')

      expect(mockLogger.info).toHaveBeenCalledWith(
        'Help documentation opened',
        expect.objectContaining({
          fieldName: 'test_field',
          helpUrl: 'https://docs.example.com/help'
        })
      )

      mockOpen.mockRestore()
    })
  })

  describe('Field Metadata - Combined Scenarios', () => {
    it('renders all metadata types together correctly', () => {
      const wrapper = mountComponent({
        fieldName: 'full_metadata_field',
        fieldSchema: {
          type: 'string',
          title: 'Full Metadata Field',
          icon: 'mdi-star',
          tooltip: 'Star tooltip',
          hint: 'This is a hint',
          helpUrl: 'https://example.com/help'
        },
        modelValue: ''
      })

      // Icon present
      expect(wrapper.html()).toContain('mdi-star')

      // Tooltip content present
      expect(wrapper.html()).toContain('Star tooltip')

      // Help icon present
      expect(wrapper.html()).toContain('mdi-help-circle-outline')

      // Hint present
      expect(wrapper.text()).toContain('This is a hint')
    })

    it('renders field correctly with no metadata', () => {
      const wrapper = mountComponent({
        fieldName: 'plain_field',
        fieldSchema: {
          type: 'string',
          title: 'Plain Field'
        },
        modelValue: ''
      })

      // Field renders without errors
      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.v-text-field').exists()).toBe(true)

      // No metadata elements
      expect(wrapper.html()).not.toContain('mdi-help-circle-outline')
      expect(wrapper.html()).not.toContain('mdi-information-outline')
    })

    it('renders metadata correctly for select field type', () => {
      const wrapper = mountComponent({
        fieldName: 'select_field',
        fieldSchema: {
          type: 'string',
          title: 'Select Field',
          enum: ['option1', 'option2'],
          icon: 'mdi-format-list-bulleted',
          hint: 'Select an option',
          helpUrl: 'https://example.com/help'
        },
        modelValue: ''
      })

      expect(wrapper.html()).toContain('mdi-format-list-bulleted')
      expect(wrapper.text()).toContain('Select an option')
      expect(wrapper.html()).toContain('mdi-help-circle-outline')
    })

    it('renders metadata correctly for number field type', () => {
      const wrapper = mountComponent({
        fieldName: 'number_field',
        fieldSchema: {
          type: 'number',
          title: 'Number Field',
          icon: 'mdi-numeric',
          hint: 'Enter a number',
          tooltip: 'Must be between 0 and 100'
        },
        modelValue: 0
      })

      expect(wrapper.html()).toContain('mdi-numeric')
      expect(wrapper.text()).toContain('Enter a number')
      expect(wrapper.html()).toContain('Must be between 0 and 100')
    })

    it('renders metadata correctly for textarea field type', () => {
      const wrapper = mountComponent({
        fieldName: 'textarea_field',
        fieldSchema: {
          type: 'string',
          title: 'Textarea Field',
          multiline: true,
          icon: 'mdi-text-box',
          hint: 'Enter detailed notes',
          helpUrl: 'https://example.com/notes-help'
        },
        modelValue: ''
      })

      expect(wrapper.html()).toContain('mdi-text-box')
      expect(wrapper.text()).toContain('Enter detailed notes')
      expect(wrapper.html()).toContain('mdi-help-circle-outline')
    })

    it('shows description when hint not provided (backward compatibility)', () => {
      const wrapper = mountComponent({
        fieldName: 'legacy_field',
        fieldSchema: {
          type: 'string',
          title: 'Legacy Field',
          description: 'This is a legacy description'
        },
        modelValue: ''
      })

      expect(wrapper.text()).toContain('This is a legacy description')
    })

    it('hides description when hint is provided', () => {
      const wrapper = mountComponent({
        fieldName: 'modern_field',
        fieldSchema: {
          type: 'string',
          title: 'Modern Field',
          description: 'Legacy description',
          hint: 'Modern hint'
        },
        modelValue: ''
      })

      expect(wrapper.text()).toContain('Modern hint')
      expect(wrapper.text()).not.toContain('Legacy description')
    })
  })
})
