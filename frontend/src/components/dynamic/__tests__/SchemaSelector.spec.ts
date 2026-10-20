/**
 * Tests for SchemaSelector (precuration / curation schema picker).
 *
 * @see src/components/dynamic/SchemaSelector.vue
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'

const schemasStore = vi.hoisted(() => ({
  loading: false,
  getPrecurationSchemas: [] as Array<Record<string, unknown>>,
  getCurationSchemas: [] as Array<Record<string, unknown>>,
  workflowPairs: [] as Array<Record<string, unknown>>,
  fetchSchemas: vi.fn(),
  fetchWorkflowPairs: vi.fn(),
  createWorkflowPair: vi.fn()
}))

vi.mock('@/stores', () => ({
  useSchemasStore: () => schemasStore
}))

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

import SchemaSelector from '../SchemaSelector.vue'

const stubs = {
  'v-card': { template: '<div><slot /></div>' },
  'v-card-title': { template: '<div><slot /></div>' },
  'v-card-text': { template: '<div><slot /></div>' },
  'v-card-actions': { template: '<div><slot /></div>' },
  'v-row': { template: '<div><slot /></div>' },
  'v-col': { template: '<div><slot /></div>' },
  'v-spacer': { template: '<span />' },
  'v-icon': { template: '<span />' },
  'v-alert': { template: '<div><slot name="prepend" /><slot /></div>' },
  'v-btn': { template: '<button v-bind="$attrs"><slot /></button>' },
  'v-list-item': { template: '<div><slot /><slot name="append" /></div>' },
  'v-list-item-title': { template: '<div><slot /></div>' },
  'v-list-item-subtitle': { template: '<div><slot /></div>' },
  'v-chip': { template: '<span><slot /></span>' },
  'v-select': {
    name: 'VSelect',
    props: ['items', 'modelValue', 'label'],
    template: `<div class="v-select-stub">
      <div v-for="option in items" :key="option.id">
        <slot name="item" :props="{}" :item="{ raw: option }" />
      </div>
    </div>`
  }
}

const precuration = { id: 'pre-1', name: 'Gene Precuration', version: 2, description: 'Pre' }
const curation = { id: 'cur-1', name: 'ClinGen Curation', version: 1, description: null }

/** The two v-selects in order: precuration, then curation */
function selects(wrapper: VueWrapper) {
  return wrapper.findAllComponents({ name: 'VSelect' })
}

describe('SchemaSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    schemasStore.getPrecurationSchemas = [precuration]
    schemasStore.getCurationSchemas = [curation]
    schemasStore.workflowPairs = []
    schemasStore.fetchSchemas.mockResolvedValue(undefined)
    schemasStore.fetchWorkflowPairs.mockResolvedValue(undefined)
  })

  it('loads schemas and workflow pairs on mount', async () => {
    mount(SchemaSelector, { global: { stubs } })
    await flushPromises()

    expect(schemasStore.fetchSchemas).toHaveBeenCalledTimes(1)
    expect(schemasStore.fetchWorkflowPairs).toHaveBeenCalledTimes(1)
  })

  it('offers precuration and curation schemas in their own selects', () => {
    const wrapper = mount(SchemaSelector, { global: { stubs } })

    expect(selects(wrapper)[0]!.props('items')).toEqual([precuration])
    expect(selects(wrapper)[1]!.props('items')).toEqual([curation])
  })

  it('shows neither action before both schemas are chosen', () => {
    const wrapper = mount(SchemaSelector, { global: { stubs } })

    expect(wrapper.findAll('button')).toHaveLength(0)
  })

  it('recognises an existing workflow pair for the chosen schemas', async () => {
    schemasStore.workflowPairs = [
      {
        id: 'pair-1',
        name: 'Existing',
        precuration_schema_id: 'pre-1',
        curation_schema_id: 'cur-1'
      }
    ]
    const wrapper = mount(SchemaSelector, { global: { stubs } })
    await flushPromises()

    selects(wrapper)[0]!.vm.$emit('update:model-value', precuration)
    selects(wrapper)[1]!.vm.$emit('update:model-value', curation)
    await flushPromises()

    expect(wrapper.text()).toContain('Using Existing Workflow Pair')
    expect(wrapper.text()).toContain('Existing')
    // Existing pair: no create button, but Continue is enabled
    const buttons = wrapper.findAll('button')
    expect(buttons.map(b => b.text())).toEqual(['Continue'])
  })

  it('creates a workflow pair for new schema combinations', async () => {
    schemasStore.createWorkflowPair.mockResolvedValue({
      id: 'pair-new',
      name: 'Gene Precuration_ClinGen Curation',
      precuration_schema_id: 'pre-1',
      curation_schema_id: 'cur-1'
    })
    const wrapper = mount(SchemaSelector, { global: { stubs } })

    selects(wrapper)[0]!.vm.$emit('update:model-value', precuration)
    selects(wrapper)[1]!.vm.$emit('update:model-value', curation)
    await flushPromises()

    expect(wrapper.text()).toContain('Methodology Pair Selected')
    const createButton = wrapper
      .findAll('button')
      .find(b => b.text().includes('Create Workflow Pair'))!
    await createButton.trigger('click')
    await flushPromises()

    expect(schemasStore.createWorkflowPair).toHaveBeenCalledWith({
      name: 'Gene Precuration_ClinGen Curation',
      version: '1.0.0',
      precuration_schema_id: 'pre-1',
      curation_schema_id: 'cur-1',
      description: 'Workflow pair for Gene Precuration precuration and ClinGen Curation curation',
      is_active: true
    })
    expect(wrapper.text()).toContain('Using Existing Workflow Pair')
  })

  it('emits the chosen schemas and workflow pair when continuing', async () => {
    const wrapper = mount(SchemaSelector, { global: { stubs } })

    selects(wrapper)[0]!.vm.$emit('update:model-value', precuration)
    selects(wrapper)[1]!.vm.$emit('update:model-value', curation)
    await flushPromises()

    const continueButton = wrapper.findAll('button').find(b => b.text().includes('Continue'))!
    await continueButton.trigger('click')

    expect(wrapper.emitted('schemas-selected')).toEqual([
      [{ precurationSchema: precuration, curationSchema: curation, workflowPair: undefined }]
    ])
  })

  it('clears the existing pair when a schema is deselected', async () => {
    schemasStore.workflowPairs = [
      {
        id: 'pair-1',
        name: 'Existing',
        precuration_schema_id: 'pre-1',
        curation_schema_id: 'cur-1'
      }
    ]
    const wrapper = mount(SchemaSelector, { global: { stubs } })
    await flushPromises()

    selects(wrapper)[0]!.vm.$emit('update:model-value', precuration)
    selects(wrapper)[1]!.vm.$emit('update:model-value', curation)
    await flushPromises()
    selects(wrapper)[1]!.vm.$emit('update:model-value', null)
    await flushPromises()

    expect(wrapper.text()).not.toContain('Using Existing Workflow Pair')
  })

  it('does not create a pair when a schema is missing', async () => {
    const wrapper = mount(SchemaSelector, { global: { stubs } })
    selects(wrapper)[0]!.vm.$emit('update:model-value', precuration)
    await flushPromises()

    // With only one schema chosen the action row stays hidden entirely
    expect(wrapper.findAll('button')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('Methodology Pair Selected')
    expect(schemasStore.createWorkflowPair).not.toHaveBeenCalled()
  })
})
