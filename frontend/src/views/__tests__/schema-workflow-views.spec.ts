/**
 * Behaviour tests for WorkflowManagement, SchemaManagement and SchemaEditor.
 * Stores are real Pinia stores; their actions are stubbed with vi.spyOn.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import './visualViewport'
import { call, vmOf } from './vm'
import WorkflowManagement from '@/views/WorkflowManagement.vue'
import SchemaManagement from '@/views/SchemaManagement.vue'
import SchemaEditor from '@/views/SchemaEditor.vue'
import { useSchemasStore } from '@/stores/schemas'
import { useWorkflowStore } from '@/stores/workflow'

const { routerPush, routeState, logger, showError, showSuccess, showInfo } = vi.hoisted(() => ({
  routerPush: vi.fn(),
  routeState: { params: {} as Record<string, string>, query: {} as Record<string, string> },
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  showError: vi.fn(),
  showSuccess: vi.fn(),
  showInfo: vi.fn()
}))

vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push: routerPush, back: vi.fn() }),
  useRoute: () => routeState
}))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/composables/useNotifications', () => ({
  showError,
  showSuccess,
  showInfo,
  showWarning: vi.fn()
}))

let pinia: ReturnType<typeof createPinia>
const opts = () => ({
  attachTo: document.body,
  global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } }
})

beforeEach(() => {
  vi.clearAllMocks()
  pinia = createPinia()
  setActivePinia(pinia)
})

afterEach(() => {
  document.body.innerHTML = ''
})

const pair = {
  id: 'wp1',
  name: 'ClinGen flow',
  version: '1.0.0',
  description: 'Two stage',
  precuration_schema_id: 'pre',
  curation_schema_id: 'cur',
  is_active: true,
  created_at: '2026-01-01T00:00:00Z'
}

const curationSchema = {
  id: 's1',
  name: 'ClinGen curation',
  version: '2.0.0',
  schema_type: 'curation',
  institution: null,
  description: 'desc',
  field_definitions: { a: { required: true }, b: {} },
  validation_rules: {},
  workflow_states: {},
  ui_configuration: {},
  scoring_configuration: { max: 12 },
  is_active: true,
  use_dynamic_form: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-02-01T00:00:00Z'
}

describe('WorkflowManagement', () => {
  const mountView = async (stub = true) => {
    const schemas = useSchemasStore()
    const workflow = useWorkflowStore()
    if (stub) {
      vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
      vi.spyOn(schemas, 'fetchWorkflowPairs').mockResolvedValue(undefined as never)
      vi.spyOn(workflow, 'fetchWorkflowAnalytics').mockResolvedValue(null as never)
      vi.spyOn(workflow, 'fetchPeerReviewers').mockResolvedValue(null as never)
    }
    schemas.workflowPairs = [pair] as never
    schemas.schemas = [
      { id: 'pre', name: 'Pre schema', schema_type: 'precuration', is_active: true },
      { id: 'cur', name: 'Cur schema', schema_type: 'curation', is_active: true }
    ] as never
    const wrapper = mount(WorkflowManagement, opts())
    await flushPromises()
    return { wrapper, schemas, vm: vmOf(wrapper) }
  }

  it('lists pairs with resolved schema names and status', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.text()).toContain('Pre: Pre schema')
    expect(wrapper.text()).toContain('Cur: Cur schema')
    expect(wrapper.text()).toContain('Active')
  })

  it('reports a load failure', async () => {
    const schemas = useSchemasStore()
    vi.spyOn(schemas, 'fetchSchemas').mockRejectedValue(new Error('down'))
    vi.spyOn(schemas, 'fetchWorkflowPairs').mockResolvedValue(undefined as never)
    vi.spyOn(useWorkflowStore(), 'fetchWorkflowAnalytics').mockResolvedValue(null as never)
    vi.spyOn(useWorkflowStore(), 'fetchPeerReviewers').mockResolvedValue(null as never)
    mount(WorkflowManagement, opts())
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('Failed to load workflow data. Please refresh.')
  })

  it('opens the details dialog for a workflow', async () => {
    const { vm } = await mountView()
    call(vm, 'viewWorkflow', pair)
    await nextTick()
    expect(vm.viewWorkflowDialog).toBe(true)
    expect(document.body.textContent).toContain('Workflow Details')
  })

  it('saves edits to a workflow and closes the dialog', async () => {
    const { vm, schemas } = await mountView()
    const update = vi.spyOn(schemas, 'updateWorkflowPair').mockResolvedValue(undefined as never)
    call(vm, 'editWorkflow', pair)
    await nextTick()
    await call(vm, 'saveWorkflow')
    expect(update).toHaveBeenCalledWith('wp1', {
      name: 'ClinGen flow',
      description: 'Two stage',
      is_active: true
    })
    expect(showSuccess).toHaveBeenCalledWith('Workflow updated successfully')
    expect(vm.editWorkflowDialog).toBe(false)
  })

  it('does not save an edit with an empty name', async () => {
    const { vm, schemas } = await mountView()
    const update = vi.spyOn(schemas, 'updateWorkflowPair').mockResolvedValue(undefined as never)
    call(vm, 'editWorkflow', { ...pair, name: '' })
    await nextTick()
    await call(vm, 'saveWorkflow')
    expect(update).not.toHaveBeenCalled()
  })

  it('reports a failed save', async () => {
    const { vm, schemas } = await mountView()
    vi.spyOn(schemas, 'updateWorkflowPair').mockRejectedValue(new Error('conflict'))
    call(vm, 'editWorkflow', pair)
    await nextTick()
    await call(vm, 'saveWorkflow')
    expect(showError).toHaveBeenCalledWith('Failed to update workflow')
  })

  it('creates a workflow pair with the API-required fields', async () => {
    const { vm, schemas } = await mountView()
    const create = vi.spyOn(schemas, 'createWorkflowPair').mockResolvedValue(undefined as never)
    vm.createWorkflowDialog = true
    await nextTick()
    vm.newWorkflow = {
      name: 'New flow',
      description: '',
      precuration_schema_id: 'pre',
      curation_schema_id: 'cur'
    }
    await flushPromises()
    await call(vm, 'createWorkflow')
    expect(create).toHaveBeenCalledWith({
      name: 'New flow',
      description: '',
      precuration_schema_id: 'pre',
      curation_schema_id: 'cur',
      version: '1.0.0',
      is_active: true
    })
    expect(showSuccess).toHaveBeenCalledWith('Workflow created successfully')
    expect(vm.createWorkflowDialog).toBe(false)
  })

  it('refuses to create a workflow without both schemas', async () => {
    const { vm, schemas } = await mountView()
    const create = vi.spyOn(schemas, 'createWorkflowPair').mockResolvedValue(undefined as never)
    vm.createWorkflowDialog = true
    await nextTick()
    vm.newWorkflow = {
      name: 'x',
      description: '',
      precuration_schema_id: null,
      curation_schema_id: 'cur'
    }
    await flushPromises()
    await call(vm, 'createWorkflow')
    expect(create).not.toHaveBeenCalled()
  })

  it('reports a failed create', async () => {
    const { vm, schemas } = await mountView()
    vi.spyOn(schemas, 'createWorkflowPair').mockRejectedValue(new Error('dup'))
    vm.createWorkflowDialog = true
    await nextTick()
    vm.newWorkflow = {
      name: 'x',
      description: '',
      precuration_schema_id: 'pre',
      curation_schema_id: 'cur'
    }
    await flushPromises()
    await call(vm, 'createWorkflow')
    expect(showError).toHaveBeenCalledWith('Failed to create workflow')
  })

  it('reports a failed delete and skips it when not confirmed', async () => {
    const { vm, schemas } = await mountView()
    const del = vi.spyOn(schemas, 'deleteWorkflowPair').mockRejectedValue(new Error('in use'))
    vi.stubGlobal(
      'confirm',
      vi.fn(() => false)
    )
    await call(vm, 'deleteWorkflow', pair)
    expect(del).not.toHaveBeenCalled()
    vi.stubGlobal(
      'confirm',
      vi.fn(() => true)
    )
    await call(vm, 'deleteWorkflow', pair)
    expect(showError).toHaveBeenCalledWith('Failed to delete workflow')
    vi.unstubAllGlobals()
  })

  it('maps stage types to colours and icons and announces stage editing', async () => {
    const { vm } = await mountView()
    expect(call(vm, 'getStageColor', 'review')).toBe('purple')
    expect(call(vm, 'getStageColor', 'other')).toBe('grey')
    expect(call(vm, 'getStageIcon', 'entry')).toBe('mdi-file-document-plus')
    expect(call(vm, 'getStageIcon', 'other')).toBe('mdi-circle')
    expect(call(vm, 'getSchemaName', null, 'curation')).toBe('N/A')
    call(vm, 'editStage', { id: 'st1' })
    expect(showInfo).toHaveBeenCalledWith('Stage editing coming soon')
  })
})

describe('SchemaManagement', () => {
  const mountView = async () => {
    const schemas = useSchemasStore()
    vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
    schemas.schemas = [curationSchema] as never
    const wrapper = mount(SchemaManagement, opts())
    await flushPromises()
    return { wrapper, schemas, vm: vmOf(wrapper) }
  }
  const row = { id: 's1', name: 'ClinGen curation' }

  it('filters the table by type and status', async () => {
    const { wrapper, vm } = await mountView()
    expect(wrapper.text()).toContain('ClinGen curation')
    vm.selectedType = 'precuration'
    await nextTick()
    expect(wrapper.text()).not.toContain('ClinGen curation')
    vm.selectedType = 'curation'
    vm.selectedStatus = 'deprecated'
    await nextTick()
    expect(wrapper.text()).not.toContain('ClinGen curation')
    vm.selectedStatus = 'active'
    await nextTick()
    expect(wrapper.text()).toContain('ClinGen curation')
  })

  it('opens the editor for a schema and reports navigation failures', async () => {
    const { vm } = await mountView()
    call(vm, 'editSchema', row)
    expect(routerPush).toHaveBeenCalledWith({ name: 'SchemaEditor', params: { id: 's1' } })
    routerPush.mockImplementationOnce(() => {
      throw new Error('nav')
    })
    call(vm, 'editSchema', row)
    expect(showError).toHaveBeenCalledWith('Failed to open schema editor')
    call(vm, 'viewSchema', row)
    expect(logger.info).toHaveBeenCalledWith('View schema requested', expect.anything())
  })

  it('duplicates a schema through the store', async () => {
    const { vm, schemas } = await mountView()
    const duplicate = vi.spyOn(schemas, 'duplicateSchema').mockResolvedValue({ id: 's2' } as never)
    await call(vm, 'duplicateSchema', row)
    expect(duplicate).toHaveBeenCalledWith('s1')
    expect(showSuccess).toHaveBeenCalledWith('Schema "ClinGen curation" duplicated successfully')
  })

  it('reports a failed duplicate', async () => {
    const { vm, schemas } = await mountView()
    vi.spyOn(schemas, 'duplicateSchema').mockRejectedValue(new Error('dup'))
    await call(vm, 'duplicateSchema', row)
    expect(showError).toHaveBeenCalledWith('Failed to duplicate schema')
  })

  it('reports a failed delete', async () => {
    const { vm, schemas } = await mountView()
    vi.spyOn(schemas, 'deleteSchema').mockRejectedValue(new Error('in use'))
    vi.stubGlobal(
      'confirm',
      vi.fn(() => true)
    )
    await call(vm, 'deleteSchema', row)
    expect(showError).toHaveBeenCalledWith('Failed to delete schema')
    vi.unstubAllGlobals()
  })

  it('creates an inactive skeleton schema from the dialog and resets the form', async () => {
    const { vm, schemas } = await mountView()
    const create = vi.spyOn(schemas, 'createSchema').mockResolvedValue({ id: 's3' } as never)
    vm.createSchemaDialog = true
    await nextTick()
    vm.newSchema = { name: 'Fresh', description: 'd', type: 'curation', version: '1.0.0' }
    await flushPromises()
    await call(vm, 'createSchema')
    expect(create).toHaveBeenCalledWith({
      name: 'Fresh',
      description: 'd',
      version: '1.0.0',
      schema_type: 'curation',
      field_definitions: {},
      workflow_states: {},
      ui_configuration: {},
      is_active: false,
      use_dynamic_form: true
    })
    expect(showSuccess).toHaveBeenCalledWith('Schema "Fresh" created successfully')
    expect(vm.createSchemaDialog).toBe(false)
    expect((vm.newSchema as { name: string }).name).toBe('')
  })

  it('does not create a schema when the form is invalid, and reports API failures', async () => {
    const { vm, schemas } = await mountView()
    const create = vi.spyOn(schemas, 'createSchema').mockRejectedValue(new Error('bad'))
    vm.createSchemaDialog = true
    await nextTick()
    vm.newSchema = { name: '', description: '', type: null, version: '1.0.0' }
    await flushPromises()
    await call(vm, 'createSchema')
    expect(create).not.toHaveBeenCalled()
    vm.newSchema = { name: 'Fresh', description: '', type: 'curation', version: '1.0.0' }
    await flushPromises()
    await call(vm, 'createSchema')
    expect(showError).toHaveBeenCalledWith('Failed to create schema')
  })

  it('formats dates and tolerates a missing one', async () => {
    const { vm } = await mountView()
    expect(call(vm, 'formatDate', null)).toBe('')
    expect(call(vm, 'formatDate', '2026-01-02T00:00:00Z')).not.toBe('')
  })
})

describe('SchemaEditor', () => {
  beforeEach(() => {
    routeState.params = { id: 's1' }
  })
  afterEach(() => {
    routeState.params = {}
  })

  const mountView = async () => {
    const schemas = useSchemasStore()
    vi.spyOn(schemas, 'fetchSchemaById').mockResolvedValue(curationSchema as never)
    const wrapper = mount(SchemaEditor, opts())
    await flushPromises()
    return { wrapper, schemas, vm: vmOf(wrapper) }
  }

  it('shows the real schema fields and counts the required ones', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.text()).toContain('curation schema v2.0.0')
    expect(wrapper.text()).toContain('"max": 12')
    const stats = wrapper.text().replace(/\s+/g, ' ')
    expect(stats).toContain('Total Fields:2')
    expect(stats).toContain('Required Fields:1')
  })

  it('saves edited JSON and metadata, then leaves edit mode', async () => {
    const { vm, schemas } = await mountView()
    const update = vi
      .spyOn(schemas, 'updateSchema')
      .mockResolvedValue({ ...curationSchema, name: 'Renamed' } as never)
    vm.isEditing = true
    await nextTick()
    vm.editableSchema = { name: 'Renamed', version: '2.0.0', description: 'd', is_active: false }
    vm.jsonSchemaText = '{"x": {"required": true}}'
    vm.scoringConfigText = ''
    await call(vm, 'saveSchema')
    expect(update).toHaveBeenCalledWith('s1', {
      name: 'Renamed',
      version: '2.0.0',
      description: 'd',
      is_active: false,
      field_definitions: { x: { required: true } },
      scoring_configuration: null
    })
    expect(vm.isEditing).toBe(false)
  })

  it('refuses to save invalid JSON and flags it', async () => {
    const { vm, schemas } = await mountView()
    const update = vi.spyOn(schemas, 'updateSchema').mockResolvedValue(undefined as never)
    vm.isEditing = true
    await nextTick()
    vm.jsonSchemaText = '{nope'
    call(vm, 'validateJson')
    expect(vm.isValidJson).toBe(false)
    expect(vm.jsonError).not.toBe('')
    await call(vm, 'saveSchema')
    expect(update).not.toHaveBeenCalled()
    vm.jsonSchemaText = '{}'
    call(vm, 'validateJson')
    expect(vm.isValidJson).toBe(true)
  })

  it('logs a failed save and a malformed scoring configuration', async () => {
    const { vm, schemas } = await mountView()
    vi.spyOn(schemas, 'updateSchema').mockRejectedValue(new Error('conflict'))
    vm.isEditing = true
    await nextTick()
    await call(vm, 'saveSchema')
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to save schema:',
      expect.objectContaining({ error: 'conflict' })
    )
    vm.scoringConfigText = '{bad'
    call(vm, 'validateScoringConfig')
    expect(logger.error).toHaveBeenCalledWith('Invalid scoring config JSON:', expect.anything())
  })

  it('restores the original values on cancel', async () => {
    const { vm } = await mountView()
    vm.isEditing = true
    vm.editableSchema = { name: 'Changed' }
    vm.jsonSchemaText = 'junk'
    call(vm, 'cancelEdit')
    expect(vm.isEditing).toBe(false)
    expect((vm.editableSchema as { name: string }).name).toBe('ClinGen curation')
    expect(String(vm.jsonSchemaText)).toContain('"a"')
  })

  it('validates the schema through the schemas store', async () => {
    const { vm, schemas } = await mountView()
    const validate = vi
      .spyOn(schemas, 'validateSchema')
      .mockResolvedValue({ is_valid: true } as never)
    await call(vm, 'validateSchema')
    expect(validate).toHaveBeenCalledWith('s1')
    expect(logger.info).toHaveBeenCalledWith('Schema validation result:', { is_valid: true })
    validate.mockRejectedValueOnce(new Error('x'))
    await call(vm, 'validateSchema')
    expect(logger.error).toHaveBeenCalledWith(
      'Schema validation failed:',
      expect.objectContaining({ error: 'x' })
    )
  })

  it('exports the schema as a JSON download', async () => {
    const { vm } = await mountView()
    const create = vi.fn(() => 'blob:x')
    const revoke = vi.fn()
    URL.createObjectURL = create
    URL.revokeObjectURL = revoke
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    call(vm, 'exportSchema')
    expect(create).toHaveBeenCalled()
    expect(click).toHaveBeenCalled()
    expect(revoke).toHaveBeenCalledWith('blob:x')
    click.mockRestore()
  })

  it('duplicates the schema and opens the copy, or logs a failure', async () => {
    const { vm, schemas } = await mountView()
    const create = vi.spyOn(schemas, 'duplicateSchema').mockResolvedValue({ id: 's9' } as never)
    await call(vm, 'duplicateSchema')
    expect(routerPush).toHaveBeenCalledWith({ name: 'SchemaEditor', params: { id: 's9' } })
    create.mockRejectedValueOnce(new Error('dup'))
    await call(vm, 'duplicateSchema')
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to duplicate schema:',
      expect.objectContaining({ error: 'dup' })
    )
  })

  it('deletes after confirmation and returns to the list', async () => {
    const { vm, schemas } = await mountView()
    const del = vi.spyOn(schemas, 'deleteSchema').mockResolvedValue(undefined as never)
    vi.stubGlobal(
      'confirm',
      vi.fn(() => false)
    )
    await call(vm, 'deleteSchema')
    expect(del).not.toHaveBeenCalled()
    vi.stubGlobal(
      'confirm',
      vi.fn(() => true)
    )
    await call(vm, 'deleteSchema')
    expect(del).toHaveBeenCalledWith('s1')
    expect(routerPush).toHaveBeenCalledWith({ name: 'SchemaManagement' })
    del.mockRejectedValueOnce(new Error('in use'))
    await call(vm, 'deleteSchema')
    expect(logger.error).toHaveBeenCalledWith(
      'Failed to delete schema:',
      expect.objectContaining({ error: 'in use' })
    )
    vi.unstubAllGlobals()
  })
})
