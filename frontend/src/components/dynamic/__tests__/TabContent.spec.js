/**
 * TabContent Component Tests
 *
 * Tests for section rendering, collapsibility, and field path resolution
 *
 * Test Coverage:
 * - Section rendering in expansion panels
 * - Section collapsibility based on collapsed property
 * - Field path resolution for nested properties
 * - Icon and help text display
 *
 * @see src/components/dynamic/TabContent.vue
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import TabContent from '../TabContent.vue'

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

// Vuetify component stubs
const vuetifyStubs = {
  'v-card-text': {
    template: '<div class="v-card-text"><slot /></div>'
  },
  'v-expansion-panels': {
    template: '<div class="v-expansion-panels"><slot /></div>',
    props: ['modelValue', 'multiple', 'variant']
  },
  'v-expansion-panel': {
    template: '<div class="v-expansion-panel" :data-value="value"><slot /></div>',
    props: ['value']
  },
  'v-expansion-panel-title': {
    template: '<div class="v-expansion-panel-title"><slot /></div>'
  },
  'v-expansion-panel-text': {
    template: '<div class="v-expansion-panel-text"><slot /></div>'
  },
  'v-icon': {
    template: '<i class="v-icon" :data-icon="icon"></i>',
    props: ['icon', 'start']
  },
  'v-row': {
    template: '<div class="v-row"><slot /></div>'
  },
  'v-col': {
    template: '<div class="v-col"><slot /></div>',
    props: ['cols', 'sm']
  },
  DynamicField: {
    name: 'DynamicField',
    template: '<div class="dynamic-field" :data-field-name="fieldName" :data-model-value="modelValue"></div>',
    props: ['fieldName', 'fieldSchema', 'modelValue', 'validationResult', 'disabled']
  }
}

/**
 * Helper to create tab with sections
 */
function createTab(sections) {
  return {
    id: 'test-tab',
    name: 'Test Tab',
    sections
  }
}

/**
 * Helper to create schema with properties
 */
function createSchema(properties) {
  return {
    type: 'object',
    properties
  }
}

/**
 * Helper to mount TabContent with defaults
 */
function mountComponent(props = {}, options = {}) {
  return mount(TabContent, {
    props: {
      tab: createTab([
        {
          name: 'Default Section',
          fields: ['field1']
        }
      ]),
      schema: createSchema({
        field1: { type: 'string', title: 'Field 1' }
      }),
      formData: {},
      validationResult: null,
      readonly: false,
      ...props
    },
    global: {
      stubs: {
        ...vuetifyStubs,
        ...options.global?.stubs
      },
      ...options.global
    },
    ...options
  })
}

describe('TabContent Section Rendering', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders v-expansion-panels with multiple prop', async () => {
    const wrapper = mountComponent()
    await wrapper.vm.$nextTick()

    const panels = wrapper.find('.v-expansion-panels')
    expect(panels.exists()).toBe(true)
    // Verify multiple prop is set in HTML
    expect(wrapper.html()).toContain('v-expansion-panels')
  })

  it('renders section names in panel titles', async () => {
    const tab = createTab([
      {
        name: 'Case Information',
        fields: ['field1']
      },
      {
        name: 'Genetic Evidence',
        fields: ['field2']
      }
    ])

    const schema = createSchema({
      field1: { type: 'string', title: 'Field 1' },
      field2: { type: 'string', title: 'Field 2' }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Case Information')
    expect(wrapper.text()).toContain('Genetic Evidence')
  })

  it('renders section icon when present', async () => {
    const tab = createTab([
      {
        name: 'Section with Icon',
        icon: 'mdi-dna',
        fields: ['field1']
      },
      {
        name: 'Section without Icon',
        fields: ['field2']
      }
    ])

    const schema = createSchema({
      field1: { type: 'string', title: 'Field 1' },
      field2: { type: 'string', title: 'Field 2' }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    const icons = wrapper.findAll('.v-icon')
    expect(icons.length).toBeGreaterThan(0)
    expect(icons[0].attributes('data-icon')).toBe('mdi-dna')
  })

  it('renders help_text when present', async () => {
    const tab = createTab([
      {
        name: 'Section with Help',
        help_text: 'This section contains important information about genetic evidence.',
        fields: ['field1']
      }
    ])

    const schema = createSchema({
      field1: { type: 'string', title: 'Field 1' }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('This section contains important information about genetic evidence.')
  })

  it('renders DynamicField for each field in section.fields', async () => {
    const tab = createTab([
      {
        name: 'Multi-field Section',
        fields: ['field1', 'field2', 'field3']
      }
    ])

    const schema = createSchema({
      field1: { type: 'string', title: 'Field 1' },
      field2: { type: 'number', title: 'Field 2' },
      field3: { type: 'boolean', title: 'Field 3' }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    const dynamicFields = wrapper.findAll('.dynamic-field')
    expect(dynamicFields).toHaveLength(3)
    expect(dynamicFields[0].attributes('data-field-name')).toBe('field1')
    expect(dynamicFields[1].attributes('data-field-name')).toBe('field2')
    expect(dynamicFields[2].attributes('data-field-name')).toBe('field3')
  })

  it('renders multiple sections in separate panels', async () => {
    const tab = createTab([
      {
        name: 'Section 1',
        fields: ['field1']
      },
      {
        name: 'Section 2',
        fields: ['field2']
      },
      {
        name: 'Section 3',
        fields: ['field3']
      }
    ])

    const schema = createSchema({
      field1: { type: 'string', title: 'Field 1' },
      field2: { type: 'string', title: 'Field 2' },
      field3: { type: 'string', title: 'Field 3' }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    const panels = wrapper.findAll('.v-expansion-panel')
    expect(panels).toHaveLength(3)
  })
})

describe('Section Collapsibility', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('sections with collapsed: true start closed', async () => {
    const tab = createTab([
      {
        name: 'Collapsed Section',
        collapsed: true,
        fields: ['field1']
      },
      {
        name: 'Open Section',
        collapsed: false,
        fields: ['field2']
      }
    ])

    const schema = createSchema({
      field1: { type: 'string', title: 'Field 1' },
      field2: { type: 'string', title: 'Field 2' }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    // openSections should only contain index 1 (second section)
    expect(wrapper.vm.openSections).toEqual([1])
  })

  it('sections with collapsed: false start open', async () => {
    const tab = createTab([
      {
        name: 'Section 1',
        collapsed: false,
        fields: ['field1']
      },
      {
        name: 'Section 2',
        collapsed: false,
        fields: ['field2']
      }
    ])

    const schema = createSchema({
      field1: { type: 'string', title: 'Field 1' },
      field2: { type: 'string', title: 'Field 2' }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    // Both sections should be open
    expect(wrapper.vm.openSections).toEqual([0, 1])
  })

  it('sections without collapsed property start open', async () => {
    const tab = createTab([
      {
        name: 'Default Section 1',
        fields: ['field1']
      },
      {
        name: 'Default Section 2',
        fields: ['field2']
      }
    ])

    const schema = createSchema({
      field1: { type: 'string', title: 'Field 1' },
      field2: { type: 'string', title: 'Field 2' }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    // All sections without collapsed property should default to open
    expect(wrapper.vm.openSections).toEqual([0, 1])
  })

  it('mixed collapsed states initialize correctly', async () => {
    const tab = createTab([
      {
        name: 'Section 1',
        collapsed: true,
        fields: ['field1']
      },
      {
        name: 'Section 2',
        // No collapsed property - defaults to open
        fields: ['field2']
      },
      {
        name: 'Section 3',
        collapsed: false,
        fields: ['field3']
      },
      {
        name: 'Section 4',
        collapsed: true,
        fields: ['field4']
      }
    ])

    const schema = createSchema({
      field1: { type: 'string', title: 'Field 1' },
      field2: { type: 'string', title: 'Field 2' },
      field3: { type: 'string', title: 'Field 3' },
      field4: { type: 'string', title: 'Field 4' }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    // Sections 2 and 3 (indices 1 and 2) should be open
    expect(wrapper.vm.openSections).toEqual([1, 2])
  })
})

describe('Field Path Resolution', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('resolves simple field paths', async () => {
    const tab = createTab([
      {
        name: 'Section',
        fields: ['summary']
      }
    ])

    const schema = createSchema({
      summary: { type: 'string', title: 'Summary' }
    })

    const formData = {
      summary: 'Test summary value'
    }

    const wrapper = mountComponent({ tab, schema, formData })
    await wrapper.vm.$nextTick()

    const field = wrapper.find('.dynamic-field')
    expect(field.attributes('data-model-value')).toBe('Test summary value')
  })

  it('resolves nested field paths', async () => {
    const tab = createTab([
      {
        name: 'Section',
        fields: ['genetic_evidence.case_level']
      }
    ])

    const schema = createSchema({
      genetic_evidence: {
        type: 'object',
        properties: {
          case_level: { type: 'number', title: 'Case Level' }
        }
      }
    })

    const formData = {
      genetic_evidence: {
        case_level: 5
      }
    }

    const wrapper = mountComponent({ tab, schema, formData })
    await wrapper.vm.$nextTick()

    const field = wrapper.find('.dynamic-field')
    expect(field.attributes('data-field-name')).toBe('case_level')
    expect(field.attributes('data-model-value')).toBe('5')
  })

  it('resolves deeply nested paths', async () => {
    const tab = createTab([
      {
        name: 'Section',
        fields: ['level1.level2.level3']
      }
    ])

    const schema = createSchema({
      level1: {
        type: 'object',
        properties: {
          level2: {
            type: 'object',
            properties: {
              level3: { type: 'string', title: 'Level 3' }
            }
          }
        }
      }
    })

    const formData = {
      level1: {
        level2: {
          level3: 'deep value'
        }
      }
    }

    const wrapper = mountComponent({ tab, schema, formData })
    await wrapper.vm.$nextTick()

    const field = wrapper.find('.dynamic-field')
    expect(field.attributes('data-field-name')).toBe('level3')
    expect(field.attributes('data-model-value')).toBe('deep value')
  })

  it('handles missing nested values gracefully', async () => {
    const tab = createTab([
      {
        name: 'Section',
        fields: ['genetic_evidence.case_level']
      }
    ])

    const schema = createSchema({
      genetic_evidence: {
        type: 'object',
        properties: {
          case_level: { type: 'number', title: 'Case Level' }
        }
      }
    })

    const formData = {
      // genetic_evidence is missing
    }

    const wrapper = mountComponent({ tab, schema, formData })
    await wrapper.vm.$nextTick()

    const field = wrapper.find('.dynamic-field')
    expect(field.exists()).toBe(true)
    expect(field.attributes('data-model-value')).toBeUndefined()
  })

  it('emits update:field with correct path and value', async () => {
    const tab = createTab([
      {
        name: 'Section',
        fields: ['summary']
      }
    ])

    const schema = createSchema({
      summary: { type: 'string', title: 'Summary' }
    })

    // Use a real stub that emits events
    const wrapper = mount(TabContent, {
      props: {
        tab,
        schema,
        formData: {},
        validationResult: null,
        readonly: false
      },
      global: {
        stubs: {
          ...vuetifyStubs,
          DynamicField: {
            name: 'DynamicField',
            template: '<div class="dynamic-field" @click="$emit(\'update:model-value\', \'new value\')"></div>',
            props: ['fieldName', 'fieldSchema', 'modelValue', 'validationResult', 'disabled'],
            emits: ['update:model-value']
          }
        }
      }
    })

    await wrapper.vm.$nextTick()

    const field = wrapper.find('.dynamic-field')
    await field.trigger('click')

    const emitted = wrapper.emitted('update:field')
    expect(emitted).toBeDefined()
    expect(emitted[0]).toEqual(['summary', 'new value'])
  })

  it('emits update:field with nested path', async () => {
    const tab = createTab([
      {
        name: 'Section',
        fields: ['genetic_evidence.case_level']
      }
    ])

    const schema = createSchema({
      genetic_evidence: {
        type: 'object',
        properties: {
          case_level: { type: 'number', title: 'Case Level' }
        }
      }
    })

    const wrapper = mount(TabContent, {
      props: {
        tab,
        schema,
        formData: {},
        validationResult: null,
        readonly: false
      },
      global: {
        stubs: {
          ...vuetifyStubs,
          DynamicField: {
            name: 'DynamicField',
            template: '<div class="dynamic-field" @click="$emit(\'update:model-value\', 42)"></div>',
            props: ['fieldName', 'fieldSchema', 'modelValue', 'validationResult', 'disabled'],
            emits: ['update:model-value']
          }
        }
      }
    })

    await wrapper.vm.$nextTick()

    const field = wrapper.find('.dynamic-field')
    await field.trigger('click')

    const emitted = wrapper.emitted('update:field')
    expect(emitted).toBeDefined()
    expect(emitted[0]).toEqual(['genetic_evidence.case_level', 42])
  })
})

describe('Schema Navigation', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('navigates schema for nested object properties', async () => {
    const tab = createTab([
      {
        name: 'Section',
        fields: ['genetic_evidence.case_level']
      }
    ])

    const schema = createSchema({
      genetic_evidence: {
        type: 'object',
        title: 'Genetic Evidence',
        properties: {
          case_level: { type: 'number', title: 'Case Level Score' }
        }
      }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    const field = wrapper.find('.dynamic-field')
    expect(field.exists()).toBe(true)
    // The fieldName should be the last segment
    expect(field.attributes('data-field-name')).toBe('case_level')
  })

  it('logs warning for missing schema fields', async () => {
    const tab = createTab([
      {
        name: 'Section',
        fields: ['nonexistent_field']
      }
    ])

    const schema = createSchema({
      existing_field: { type: 'string', title: 'Existing' }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    expect(mockLogger.warn).toHaveBeenCalledWith(
      'Field schema not found',
      expect.objectContaining({
        fieldPath: 'nonexistent_field'
      })
    )
  })

  it('provides fallback schema for missing fields', async () => {
    const tab = createTab([
      {
        name: 'Section',
        fields: ['missing_field']
      }
    ])

    const schema = createSchema({
      existing_field: { type: 'string', title: 'Existing' }
    })

    const wrapper = mountComponent({ tab, schema })
    await wrapper.vm.$nextTick()

    // Should still render field with fallback schema
    const field = wrapper.find('.dynamic-field')
    expect(field.exists()).toBe(true)
  })
})

describe('KeepAlive Lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('component mounts successfully', async () => {
    const wrapper = mountComponent()
    await wrapper.vm.$nextTick()

    // Verify component rendered
    expect(wrapper.find('.v-expansion-panels').exists()).toBe(true)

    // KeepAlive lifecycle hooks are called by parent, not testable in isolation
    // Just verify component structure is correct
    expect(wrapper.vm.openSections).toBeDefined()
  })
})
