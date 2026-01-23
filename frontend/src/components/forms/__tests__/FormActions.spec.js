/**
 * FormActions Component Tests
 *
 * Tests for the reusable form action bar component
 *
 * Test Coverage:
 * - Button rendering
 * - Disabled states
 * - Loading states
 * - Event emissions
 * - Accessibility
 *
 * @see src/components/forms/FormActions.vue
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import FormActions from '../FormActions.vue'

describe('FormActions', () => {
  describe('Basic Rendering', () => {
    it('should render all action buttons', () => {
      const wrapper = mount(FormActions)

      expect(wrapper.text()).toContain('Cancel')
      expect(wrapper.text()).toContain('Save Draft')
      expect(wrapper.text()).toContain('Submit for Review')
    })

    it('should render undo/redo buttons', () => {
      const wrapper = mount(FormActions)

      const buttons = wrapper.findAll('.v-btn')
      expect(buttons.length).toBeGreaterThanOrEqual(5) // Cancel, Undo, Redo, Save, Submit
    })
  })

  describe('Disabled States', () => {
    it('should disable undo button when canUndo is false', () => {
      const wrapper = mount(FormActions, {
        props: {
          canUndo: false
        }
      })

      const undoButton = wrapper.find('[aria-label="Undo (Ctrl+Z)"]')
      expect(undoButton.attributes('disabled')).toBeDefined()
    })

    it('should enable undo button when canUndo is true', () => {
      const wrapper = mount(FormActions, {
        props: {
          canUndo: true
        }
      })

      const undoButton = wrapper.find('[aria-label="Undo (Ctrl+Z)"]')
      expect(undoButton.attributes('disabled')).toBeUndefined()
    })

    it('should disable redo button when canRedo is false', () => {
      const wrapper = mount(FormActions, {
        props: {
          canRedo: false
        }
      })

      const redoButton = wrapper.find('[aria-label="Redo (Ctrl+Shift+Z)"]')
      expect(redoButton.attributes('disabled')).toBeDefined()
    })

    it('should enable redo button when canRedo is true', () => {
      const wrapper = mount(FormActions, {
        props: {
          canRedo: true
        }
      })

      const redoButton = wrapper.find('[aria-label="Redo (Ctrl+Shift+Z)"]')
      expect(redoButton.attributes('disabled')).toBeUndefined()
    })

    it('should disable submit button when canSubmit is false', () => {
      const wrapper = mount(FormActions, {
        props: {
          canSubmit: false
        }
      })

      const submitButton = wrapper.find('[aria-label="Submit for Review (Ctrl+Enter)"]')
      expect(submitButton.attributes('disabled')).toBeDefined()
    })

    it('should enable submit button when canSubmit is true', () => {
      const wrapper = mount(FormActions, {
        props: {
          canSubmit: true
        }
      })

      const submitButton = wrapper.find('[aria-label="Submit for Review (Ctrl+Enter)"]')
      expect(submitButton.attributes('disabled')).toBeUndefined()
    })
  })

  describe('Loading States', () => {
    it('should show loading state on save button when saving', () => {
      const wrapper = mount(FormActions, {
        props: {
          saving: true
        }
      })

      const saveButton = wrapper.find('[aria-label="Save Draft (Ctrl+S)"]')
      expect(saveButton.classes()).toContain('v-btn--loading')
    })

    it('should show loading state on submit button when submitting', () => {
      const wrapper = mount(FormActions, {
        props: {
          submitting: true
        }
      })

      const submitButton = wrapper.find('[aria-label="Submit for Review (Ctrl+Enter)"]')
      expect(submitButton.classes()).toContain('v-btn--loading')
    })
  })

  describe('Event Emissions', () => {
    it('should emit cancel event when cancel button is clicked', async () => {
      const wrapper = mount(FormActions)

      const cancelButton = wrapper.find('[aria-label="Cancel"]')
      await cancelButton.trigger('click')

      expect(wrapper.emitted('cancel')).toBeTruthy()
      expect(wrapper.emitted('cancel')).toHaveLength(1)
    })

    it('should emit undo event when undo button is clicked', async () => {
      const wrapper = mount(FormActions, {
        props: {
          canUndo: true
        }
      })

      const undoButton = wrapper.find('[aria-label="Undo (Ctrl+Z)"]')
      await undoButton.trigger('click')

      expect(wrapper.emitted('undo')).toBeTruthy()
      expect(wrapper.emitted('undo')).toHaveLength(1)
    })

    it('should emit redo event when redo button is clicked', async () => {
      const wrapper = mount(FormActions, {
        props: {
          canRedo: true
        }
      })

      const redoButton = wrapper.find('[aria-label="Redo (Ctrl+Shift+Z)"]')
      await redoButton.trigger('click')

      expect(wrapper.emitted('redo')).toBeTruthy()
      expect(wrapper.emitted('redo')).toHaveLength(1)
    })

    it('should emit save-draft event when save button is clicked', async () => {
      const wrapper = mount(FormActions)

      const saveButton = wrapper.find('[aria-label="Save Draft (Ctrl+S)"]')
      await saveButton.trigger('click')

      expect(wrapper.emitted('save-draft')).toBeTruthy()
      expect(wrapper.emitted('save-draft')).toHaveLength(1)
    })

    it('should emit submit event when submit button is clicked', async () => {
      const wrapper = mount(FormActions, {
        props: {
          canSubmit: true
        }
      })

      const submitButton = wrapper.find('[aria-label="Submit for Review (Ctrl+Enter)"]')
      await submitButton.trigger('click')

      expect(wrapper.emitted('submit')).toBeTruthy()
      expect(wrapper.emitted('submit')).toHaveLength(1)
    })
  })

  describe('Accessibility', () => {
    it('should have aria-labels on all buttons', () => {
      const wrapper = mount(FormActions)

      expect(wrapper.find('[aria-label="Cancel"]').exists()).toBe(true)
      expect(wrapper.find('[aria-label="Undo (Ctrl+Z)"]').exists()).toBe(true)
      expect(wrapper.find('[aria-label="Redo (Ctrl+Shift+Z)"]').exists()).toBe(true)
      expect(wrapper.find('[aria-label="Save Draft (Ctrl+S)"]').exists()).toBe(true)
      expect(wrapper.find('[aria-label="Submit for Review (Ctrl+Enter)"]').exists()).toBe(true)
    })
  })

  describe('Default Props', () => {
    it('should have canUndo false by default', () => {
      const wrapper = mount(FormActions)

      const undoButton = wrapper.find('[aria-label="Undo (Ctrl+Z)"]')
      expect(undoButton.attributes('disabled')).toBeDefined()
    })

    it('should have canRedo false by default', () => {
      const wrapper = mount(FormActions)

      const redoButton = wrapper.find('[aria-label="Redo (Ctrl+Shift+Z)"]')
      expect(redoButton.attributes('disabled')).toBeDefined()
    })

    it('should have canSubmit true by default', () => {
      const wrapper = mount(FormActions)

      const submitButton = wrapper.find('[aria-label="Submit for Review (Ctrl+Enter)"]')
      expect(submitButton.attributes('disabled')).toBeUndefined()
    })

    it('should not be in saving state by default', () => {
      const wrapper = mount(FormActions)

      const saveButton = wrapper.find('[aria-label="Save Draft (Ctrl+S)"]')
      expect(saveButton.classes()).not.toContain('v-btn--loading')
    })

    it('should not be in submitting state by default', () => {
      const wrapper = mount(FormActions)

      const submitButton = wrapper.find('[aria-label="Submit for Review (Ctrl+Enter)"]')
      expect(submitButton.classes()).not.toContain('v-btn--loading')
    })
  })
})
