import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DynamicForm from '../DynamicForm.vue'
import { vmOf } from './testHelpers'
import { getTabFieldPaths } from '../composables/useFormTabs'

// Default mock schema
const defaultMockSchema = {
  properties: {
    name: { type: 'string', required: true },
    email: { type: 'string', pattern: '^[^@]+@[^@]+$' }
  }
}

// Mock validation store with configurable schema
let mockSchema: Record<string, unknown> = defaultMockSchema

vi.mock('@/stores', () => ({
  useValidationStore: () => ({
    loading: false,
    error: null,
    getJsonSchema: () => mockSchema,
    getValidationResult: () => null,
    generateJsonSchema: vi.fn(),
    validateEvidence: vi.fn().mockResolvedValue({ is_valid: true }),
    clearValidationResult: vi.fn()
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

      expect(vmOf(wrapper).backendErrors).toEqual({})
      expect(vmOf(wrapper).nonFieldErrors).toEqual([])
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

      vmOf(wrapper).handleBackendValidation(mockResult)

      // Should take first error only per CONTEXT.md decision
      expect(vmOf(wrapper).backendErrors).toEqual({
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

      vmOf(wrapper).handleBackendValidation(mockResult)

      expect(vmOf(wrapper).nonFieldErrors).toContain('General form error')
      expect(vmOf(wrapper).nonFieldErrors).toContain('Unknown field error')
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
      vmOf(wrapper).backendErrors = { email: ['Invalid email'] }

      // Clear error
      vmOf(wrapper).clearFieldBackendError('email')

      expect(vmOf(wrapper).backendErrors.email).toBeUndefined()
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

      vmOf(wrapper).nonFieldErrors = ['General form error']
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
      await flushPromises() // the on-mount validation settles first
      vmOf(wrapper).backendErrors = { field1: ['Error message'] }
      await wrapper.vm.$nextTick()

      const tabErrors = vmOf(wrapper).tabValidationErrors

      expect(tabErrors.tab1).toBe(true)
      expect(tabErrors.tab2).toBe(false)
    })

    it('extracts all field paths from tab sections', () => {
      const tab = {
        id: 'test-tab',
        name: 'Test Tab',
        sections: [{ fields: ['field1', 'field2'] }, { fields: ['field3'] }]
      }

      const paths = getTabFieldPaths(tab)

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
      vmOf(wrapper).backendErrors = { email: ['Invalid email'] }

      expect(vmOf(wrapper).canSubmit).toBe(false)
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
      vmOf(wrapper).validationResult = { is_valid: false }

      expect(vmOf(wrapper).canSubmit).toBe(false)
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
      expect(vmOf(wrapper).hasChanges).toBe(false)
      expect(vmOf(wrapper).canSubmit).toBe(false)
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
      vmOf(wrapper).formData = { name: 'test-modified' }
      // No backend errors
      vmOf(wrapper).backendErrors = {}
      // Validation passed
      vmOf(wrapper).validationResult = { is_valid: true }

      expect(vmOf(wrapper).canSubmit).toBe(true)
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
      await flushPromises() // the on-mount validation settles first
      vmOf(wrapper).backendErrors = { field2: ['Error message'] }
      await wrapper.vm.$nextTick()

      const firstInvalidTab = vmOf(wrapper).findFirstInvalidTab()

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
      vmOf(wrapper).formData = { name: 'test-modified' }
      vmOf(wrapper).validationResult = { is_valid: true }

      await vmOf(wrapper).handleSubmit()

      expect(wrapper.emitted('submit')).toBeTruthy()
      expect(wrapper.emitted('submit')![0]).toEqual([{ name: 'test-modified' }])
    })
  })
})
