import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DynamicForm from '../DynamicForm.vue'

// Default mock schema
const defaultMockSchema = {
  properties: {
    name: { type: 'string', required: true },
    email: { type: 'string', pattern: '^[^@]+@[^@]+$' }
  }
}

// Mock validation store with configurable schema
let mockSchema = defaultMockSchema

vi.mock('@/stores', () => ({
  useValidationStore: () => ({
    loading: false,
    error: null,
    getJsonSchema: () => mockSchema,
    getValidationResult: () => null,
    generateJsonSchema: vi.fn(),
    validateEvidence: vi.fn()
  })
}))

// Mock logger
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn()
  })
}))

// Vuetify component stubs
const vuetifyStubs = {
  'v-form': {
    template: '<form ref="formRef"><slot /></form>',
    methods: { validate: () => ({ valid: true }) }
  },
  'v-card': { template: '<div><slot /></div>' },
  'v-card-title': { template: '<div><slot /></div>' },
  'v-card-text': { template: '<div><slot /></div>' },
  'v-card-actions': { template: '<div><slot /></div>' },
  'v-btn': { template: '<button :disabled="$attrs.disabled"><slot /></button>' },
  'v-alert': { template: '<div v-if="$attrs.modelValue !== false"><slot /></div>' },
  'v-icon': { template: '<span />' },
  'v-spacer': { template: '<span />' },
  'v-progress-circular': { template: '<span />' },
  'v-tabs': { template: '<div><slot /></div>' },
  'v-tab': { template: '<div><slot /></div>' },
  'v-window': { template: '<div><slot /></div>' },
  'v-window-item': { template: '<div><slot /></div>' },
  'v-badge': {
    template: '<span class="v-badge" :class="{ dot: $attrs.dot }"><slot /></span>'
  },
  'v-chip': { template: '<span><slot /></span>' },
  'v-row': { template: '<div><slot /></div>' },
  'v-col': { template: '<div><slot /></div>' }
}

describe('DynamicForm Validation', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    // Reset to default schema
    mockSchema = defaultMockSchema
  })

  describe('backend error display', () => {
    it('initializes with empty backend errors', () => {
      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema'
        },
        global: {
          stubs: vuetifyStubs
        }
      })

      expect(wrapper.vm.backendErrors).toEqual({})
      expect(wrapper.vm.nonFieldErrors).toEqual([])
    })

    it('maps backend field errors to backendErrors state', () => {
      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema'
        },
        global: {
          stubs: vuetifyStubs
        }
      })

      const mockResult = {
        is_valid: false,
        field_validations: {
          email: {
            errors: [{ message: 'Invalid email format' }, { message: 'Second error' }]
          },
          name: {
            errors: [{ message: 'Name is required' }]
          }
        }
      }

      wrapper.vm.handleBackendValidation(mockResult)

      // Should take first error only per CONTEXT.md decision
      expect(wrapper.vm.backendErrors).toEqual({
        email: ['Invalid email format'],
        name: ['Name is required']
      })
    })

    it('collects non-field errors separately', () => {
      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema'
        },
        global: {
          stubs: vuetifyStubs
        }
      })

      const mockResult = {
        is_valid: false,
        errors: [
          { message: 'General form error' },
          { field: 'unknown_field', message: 'Unknown field error' }
        ]
      }

      wrapper.vm.handleBackendValidation(mockResult)

      expect(wrapper.vm.nonFieldErrors).toContain('General form error')
      expect(wrapper.vm.nonFieldErrors).toContain('Unknown field error')
    })

    it('clears backend error when field value changes', () => {
      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema'
        },
        global: {
          stubs: vuetifyStubs
        }
      })

      // Set initial error
      wrapper.vm.backendErrors = { email: ['Invalid email'] }

      // Clear error
      wrapper.vm.clearFieldBackendError('email')

      expect(wrapper.vm.backendErrors.email).toBeUndefined()
    })

    it('shows non-field errors in alert', async () => {
      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema'
        },
        global: {
          stubs: vuetifyStubs
        }
      })

      wrapper.vm.nonFieldErrors = ['General form error']
      await wrapper.vm.$nextTick()

      expect(wrapper.html()).toContain('General form error')
    })
  })

  describe('tab error badges', () => {
    it('computes tab validation errors correctly', async () => {
      // Setup mock schema with tabs BEFORE mounting
      mockSchema = {
        properties: {},
        ui_configuration: {
          layout: {
            type: 'tabs',
            tabs: [
              {
                id: 'tab1',
                name: 'Tab 1',
                sections: [{ name: 'Section 1', fields: ['field1', 'field2'] }]
              },
              {
                id: 'tab2',
                name: 'Tab 2',
                sections: [{ name: 'Section 2', fields: ['field3'] }]
              }
            ]
          }
        }
      }

      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema'
        },
        global: {
          stubs: vuetifyStubs
        }
      })

      // Set backend error on field1
      wrapper.vm.backendErrors = { field1: ['Error message'] }
      await wrapper.vm.$nextTick()

      const tabErrors = wrapper.vm.tabValidationErrors

      expect(tabErrors.tab1).toBe(true)
      expect(tabErrors.tab2).toBe(false)
    })

    it('extracts all field paths from tab sections', () => {
      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema'
        },
        global: {
          stubs: vuetifyStubs
        }
      })

      const tab = {
        id: 'test-tab',
        sections: [
          { fields: ['field1', 'field2'] },
          { fields: ['field3'] }
        ]
      }

      const paths = wrapper.vm.getTabFieldPaths(tab)

      expect(paths).toEqual(['field1', 'field2', 'field3'])
    })
  })

  describe('form submission', () => {
    it('blocks submission when backend errors present', () => {
      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema',
          initialData: { name: 'test' }
        },
        global: {
          stubs: vuetifyStubs
        }
      })

      // Set backend errors
      wrapper.vm.backendErrors = { email: ['Invalid email'] }

      expect(wrapper.vm.canSubmit).toBe(false)
    })

    it('blocks submission when validation fails', () => {
      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema',
          initialData: { name: 'test' }
        },
        global: {
          stubs: {
            ...vuetifyStubs
          }
        }
      })

      // Mock validation result
      wrapper.vm.validationResult = { is_valid: false }

      expect(wrapper.vm.canSubmit).toBe(false)
    })

    it('blocks submission when no changes made', () => {
      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema',
          initialData: { name: 'test' }
        },
        global: {
          stubs: vuetifyStubs
        }
      })

      // No changes made (formData equals initialData)
      expect(wrapper.vm.hasChanges).toBe(false)
      expect(wrapper.vm.canSubmit).toBe(false)
    })

    it('allows submission when validation passes and has changes', () => {
      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema',
          initialData: { name: 'test' }
        },
        global: {
          stubs: vuetifyStubs
        }
      })

      // Make changes
      wrapper.vm.formData = { name: 'test-modified' }
      // No backend errors
      wrapper.vm.backendErrors = {}
      // Validation passed
      wrapper.vm.validationResult = { is_valid: true }

      expect(wrapper.vm.canSubmit).toBe(true)
    })

    it('finds first invalid tab', async () => {
      // Setup mock schema with tabs BEFORE mounting
      mockSchema = {
        properties: {},
        ui_configuration: {
          layout: {
            type: 'tabs',
            tabs: [
              {
                id: 'tab1',
                name: 'Tab 1',
                sections: [{ name: 'Section 1', fields: ['field1'] }]
              },
              {
                id: 'tab2',
                name: 'Tab 2',
                sections: [{ name: 'Section 2', fields: ['field2'] }]
              },
              {
                id: 'tab3',
                name: 'Tab 3',
                sections: [{ name: 'Section 3', fields: ['field3'] }]
              }
            ]
          }
        }
      }

      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema'
        },
        global: {
          stubs: vuetifyStubs
        }
      })

      // Set up backend errors for tab2 field
      wrapper.vm.backendErrors = { field2: ['Error message'] }
      await wrapper.vm.$nextTick()

      const firstInvalidTab = wrapper.vm.findFirstInvalidTab()

      expect(firstInvalidTab).toBe('tab2')
    })

    it('emits submit event when validation passes', async () => {
      const wrapper = mount(DynamicForm, {
        props: {
          schemaId: 'test-schema',
          initialData: { name: 'test' }
        },
        global: {
          stubs: {
            ...vuetifyStubs,
            'v-form': {
              template: '<form ref="formRef"><slot /></form>',
              methods: {
                validate: vi.fn().mockResolvedValue({ valid: true })
              }
            }
          }
        }
      })

      // Make changes
      wrapper.vm.formData = { name: 'test-modified' }
      wrapper.vm.validationResult = { is_valid: true }

      await wrapper.vm.handleSubmit()

      expect(wrapper.emitted('submit')).toBeTruthy()
      expect(wrapper.emitted('submit')[0]).toEqual([{ name: 'test-modified' }])
    })
  })
})
