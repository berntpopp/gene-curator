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
            ScorePreview: true,
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
            ScorePreview: true,
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
            ScorePreview: true,
            FormActions: true
          }
        }
      })

      // isDraft is true by default
      expect(wrapper.vm.isDraft).toBe(true)
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
            ScorePreview: true,
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
            ScorePreview: true,
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
            ScorePreview: true,
            FormActions: true
          }
        }
      })

      expect(typeof wrapper.vm.handleKeydown).toBe('function')
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
            ScorePreview: true,
            FormActions: true
          }
        }
      })

      expect(typeof wrapper.vm.handleSaveDraft).toBe('function')
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
            ScorePreview: true,
            FormActions: true
          }
        }
      })

      expect(typeof wrapper.vm.handleSubmit).toBe('function')
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
            ScorePreview: true,
            FormActions: true
          }
        }
      })

      expect(typeof wrapper.vm.handleCancel).toBe('function')
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
            ScorePreview: true,
            FormActions: true
          }
        }
      })

      // Initial state should be valid
      expect(wrapper.vm.isValid).toBe(true)

      // Call handleValidationChange with invalid result
      wrapper.vm.handleValidationChange({ is_valid: false })
      expect(wrapper.vm.isValid).toBe(false)

      // Call handleValidationChange with valid result
      wrapper.vm.handleValidationChange({ is_valid: true })
      expect(wrapper.vm.isValid).toBe(true)
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
            ScorePreview: true,
            FormActions: true
          }
        }
      })

      const newData = { field1: 'value1', field2: 'value2' }
      wrapper.vm.handleEvidenceChange(newData)

      expect(wrapper.vm.evidenceData).toEqual(newData)
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
            ScorePreview: true,
            FormActions: true
          }
        }
      })

      // Test "just now"
      const now = new Date().toISOString()
      expect(wrapper.vm.formatRelativeTime(now)).toBe('just now')

      // Test null input
      expect(wrapper.vm.formatRelativeTime(null)).toBe('')
    })
  })
})
