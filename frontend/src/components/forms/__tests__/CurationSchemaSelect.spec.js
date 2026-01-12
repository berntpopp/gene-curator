/**
 * CurationSchemaSelect Component Tests
 *
 * Tests for the single-schema selector component
 *
 * Test Coverage:
 * - Basic rendering
 * - Schema filtering by type
 * - v-model binding
 * - Selection confirmation
 * - Loading states
 *
 * @see src/components/forms/CurationSchemaSelect.vue
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import CurationSchemaSelect from '../CurationSchemaSelect.vue'

// Mock the schemas store
vi.mock('@/stores/schemas', () => ({
  useSchemasStore: vi.fn(() => ({
    schemas: [
      {
        id: 'schema-1',
        name: 'ClinGen SOP v11',
        schema_type: 'curation',
        version: '11.0',
        description: 'Clinical Genome Resource standard',
        field_definitions: [{ name: 'field1' }, { name: 'field2' }]
      },
      {
        id: 'schema-2',
        name: 'GenCC Standard',
        schema_type: 'curation',
        version: '1.0',
        description: 'GenCC curation standard',
        field_definitions: [{ name: 'field1' }]
      },
      {
        id: 'schema-3',
        name: 'Combined Schema',
        schema_type: 'combined',
        version: '1.0',
        description: 'Combined precuration and curation',
        field_definitions: []
      },
      {
        id: 'schema-4',
        name: 'Precuration Only',
        schema_type: 'precuration',
        version: '1.0',
        description: 'Precuration schema',
        field_definitions: []
      }
    ],
    loading: false,
    fetchSchemas: vi.fn()
  }))
}))

describe('CurationSchemaSelect', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('Basic Rendering', () => {
    it('should render the component', () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1'
        }
      })

      expect(wrapper.text()).toContain('Select Curation Methodology')
    })

    it('should render schema selection dropdown', () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1'
        }
      })

      expect(wrapper.find('.v-select').exists()).toBe(true)
    })

    it('should render continue button', () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1'
        }
      })

      expect(wrapper.text()).toContain('Continue')
    })
  })

  describe('Schema Filtering', () => {
    it('should filter schemas by curation type by default', () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1'
        }
      })

      // The component should show curation and combined schemas, not precuration
      const vm = wrapper.vm
      const available = vm.availableSchemas
      expect(available.length).toBe(3) // 2 curation + 1 combined
      expect(available.every(s => s.schema_type !== 'precuration')).toBe(true)
    })

    it('should include combined schemas in available list', () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1'
        }
      })

      const vm = wrapper.vm
      const combined = vm.availableSchemas.find(s => s.schema_type === 'combined')
      expect(combined).toBeDefined()
    })
  })

  describe('Selection', () => {
    it('should disable continue button when no schema selected', () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1'
        }
      })

      const continueButton = wrapper.find('[aria-label="Continue to curation form"]')
      expect(continueButton.attributes('disabled')).toBeDefined()
    })

    it('should emit update:modelValue when selection is confirmed', async () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1',
          modelValue: null
        }
      })

      // Set internal selection
      await wrapper.vm.handleSelection('schema-1')

      // Click continue button
      const continueButton = wrapper.find('[aria-label="Continue to curation form"]')
      await continueButton.trigger('click')

      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')[0]).toEqual(['schema-1'])
    })
  })

  describe('v-model Binding', () => {
    it('should sync with external modelValue changes', async () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1',
          modelValue: null
        }
      })

      await wrapper.setProps({ modelValue: 'schema-2' })

      expect(wrapper.vm.selectedSchemaId).toBe('schema-2')
    })
  })

  describe('Field Count Display', () => {
    it('should return correct field count for schema', () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1'
        }
      })

      const schema = {
        field_definitions: [{ name: 'f1' }, { name: 'f2' }, { name: 'f3' }]
      }
      expect(wrapper.vm.getFieldCount(schema)).toBe(3)
    })

    it('should return 0 for schema without field_definitions', () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1'
        }
      })

      const schema = {}
      expect(wrapper.vm.getFieldCount(schema)).toBe(0)
    })
  })

  describe('Selected Schema Display', () => {
    it('should show schema info when selected', async () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1'
        }
      })

      await wrapper.vm.handleSelection('schema-1')

      // Should show selected schema info
      expect(wrapper.vm.selectedSchema).toBeDefined()
      expect(wrapper.vm.selectedSchema.name).toBe('ClinGen SOP v11')
    })
  })

  describe('Props Validation', () => {
    it('should accept valid schemaType values', () => {
      const wrapper = mount(CurationSchemaSelect, {
        props: {
          scopeId: 'scope-1',
          schemaType: 'precuration'
        }
      })

      expect(wrapper.props('schemaType')).toBe('precuration')
    })
  })
})
