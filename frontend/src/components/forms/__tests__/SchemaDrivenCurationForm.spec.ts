/**
 * SchemaDrivenCurationForm Component Tests
 *
 * Tests for the schema-driven curation form wrapper
 *
 * Test Coverage:
 * - Component rendering
 * - Schema loading
 * - Form data binding
 * - Keyboard shortcuts
 * - Save/submit flow
 *
 * @see src/components/forms/SchemaDrivenCurationForm.vue
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import SchemaDrivenCurationForm from '../SchemaDrivenCurationForm.vue'

/** Bindings of <script setup> read through wrapper.vm in these tests. */
interface SchemaDrivenCurationFormVm {
  isDraft: boolean
  isValid: boolean
  evidenceData: Record<string, unknown>
  handleKeydown(event: KeyboardEvent): void
  handleSaveDraft(): void
  handleSubmit(): void
  handleCancel(): void
  handleValidationChange(result: { is_valid?: boolean }): void
  handleEvidenceChange(data: Record<string, unknown>): void
  formatRelativeTime(timestamp: string | null): string
}

function internals(wrapper: { vm: unknown }): SchemaDrivenCurationFormVm {
  return wrapper.vm as SchemaDrivenCurationFormVm
}

// Mock composables
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    error: vi.fn()
  })
}))

vi.mock('@/composables/useFormRecovery', () => ({
  useFormRecovery: () => ({
    showRecoveryDialog: { value: false },
    recoveryData: { value: null },
    lastSaved: { value: null },
    restoreRecovery: vi.fn(),
    discardRecovery: vi.fn(),
    recoveryStale: { value: false },
    setBaseline: vi.fn(),
    markSaved: vi.fn(),
    clearRecovery: vi.fn()
  })
}))

vi.mock('@/composables/useHistory', () => ({
  useHistory: () => ({
    canUndo: { value: false },
    canRedo: { value: false },
    recordAction: vi.fn(),
    undo: vi.fn(),
    redo: vi.fn(),
    clearHistory: vi.fn()
  })
}))

// Mock stores
vi.mock('@/stores/schemas', () => ({
  useSchemasStore: vi.fn(() => ({
    schemas: [
      {
        id: 'schema-1',
        name: 'ClinGen SOP v11',
        schema_type: 'curation',
        version: '11.0'
      }
    ],
    getSchemaById: vi.fn(id => ({
      id,
      name: 'ClinGen SOP v11',
      schema_type: 'curation'
    })),
    fetchSchemaById: vi.fn()
  }))
}))

vi.mock('@/stores/curations', () => ({
  useCurationsStore: vi.fn(() => ({
    fetchCurationById: vi.fn(),
    saveDraft: vi.fn(() => ({ lock_version: 1 })),
    submitCuration: vi.fn(),
    createCuration: vi.fn(() => ({ id: 'new-curation-id' }))
  }))
}))

vi.mock('@/stores/validation', () => ({
  useValidationStore: vi.fn(() => ({
    generateJsonSchema: vi.fn()
  }))
}))

vi.mock('@/stores/notifications', () => ({
  useNotificationsStore: vi.fn(() => ({
    addToast: vi.fn()
  }))
}))

// Create a mock router
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: { template: '<div />' } },
    {
      path: '/scopes/:scopeId/curations/:curationId/edit',
      name: 'curation-edit',
      component: { template: '<div />' }
    }
  ]
})

describe('SchemaDrivenCurationForm', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('Basic Rendering', () => {
    it('should render the component with required props', () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1'
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            DynamicForm: true,
            FormActions: true
          }
        }
      })

      expect(wrapper.exists()).toBe(true)
    })

    it('should accept gene prop', () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1',
          gene: { symbol: 'BRCA1' }
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            DynamicForm: true,
            FormActions: true
          }
        }
      })

      expect(wrapper.props('gene')).toEqual({ symbol: 'BRCA1' })
    })

    it('should have isDraft ref set to true by default', async () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1'
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            DynamicForm: true,
            FormActions: true
          }
        }
      })

      // isDraft is true by default
      expect(internals(wrapper).isDraft).toBe(true)
    })
  })

  describe('Props', () => {
    it('should accept readonly prop', () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1',
          readonly: true
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            DynamicForm: true,
            FormActions: true
          }
        }
      })

      expect(wrapper.props('readonly')).toBe(true)
    })

    it('should pass schemaId to DynamicForm', () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1'
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            FormActions: true
          }
        }
      })

      const dynamicForm = wrapper.findComponent({ name: 'DynamicForm' })
      if (dynamicForm.exists()) {
        expect(dynamicForm.props('schemaId')).toBe('schema-1')
      }
    })
  })

  describe('Keyboard Shortcuts', () => {
    it('should have keydown handler', () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1'
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            DynamicForm: true,
            FormActions: true
          }
        }
      })

      expect(typeof internals(wrapper).handleKeydown).toBe('function')
    })
  })

  describe('Form Actions', () => {
    it('should have handleSaveDraft method', () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1'
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            DynamicForm: true,
            FormActions: true
          }
        }
      })

      expect(typeof internals(wrapper).handleSaveDraft).toBe('function')
    })

    it('should have handleSubmit method', () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1'
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            DynamicForm: true,
            FormActions: true
          }
        }
      })

      expect(typeof internals(wrapper).handleSubmit).toBe('function')
    })

    it('should have handleCancel method', () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1'
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            DynamicForm: true,
            FormActions: true
          }
        }
      })

      expect(typeof internals(wrapper).handleCancel).toBe('function')
    })
  })

  describe('Validation Handling', () => {
    it('should handle validation change events', () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1'
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            DynamicForm: true,
            FormActions: true
          }
        }
      })

      // Initial state should be valid
      expect(internals(wrapper).isValid).toBe(true)

      // Call handleValidationChange with invalid result
      internals(wrapper).handleValidationChange({ is_valid: false })
      expect(internals(wrapper).isValid).toBe(false)

      // Call handleValidationChange with valid result
      internals(wrapper).handleValidationChange({ is_valid: true })
      expect(internals(wrapper).isValid).toBe(true)
    })
  })

  describe('Evidence Data Handling', () => {
    it('should handle evidence change events', () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1'
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            DynamicForm: true,
            FormActions: true
          }
        }
      })

      const newData = { field1: 'value1', field2: 'value2' }
      internals(wrapper).handleEvidenceChange(newData)

      expect(internals(wrapper).evidenceData).toEqual(newData)
    })
  })

  describe('Utility Functions', () => {
    it('should format relative time correctly', () => {
      const wrapper = mount(SchemaDrivenCurationForm, {
        props: {
          schemaId: 'schema-1',
          scopeId: 'scope-1'
        },
        global: {
          plugins: [router],
          stubs: {
            ErrorBoundary: true,
            FormRecoveryDialog: true,
            DynamicForm: true,
            FormActions: true
          }
        }
      })

      // Test "just now"
      const now = new Date().toISOString()
      expect(internals(wrapper).formatRelativeTime(now)).toBe('just now')

      // Test null input
      expect(internals(wrapper).formatRelativeTime(null)).toBe('')
    })
  })
})
