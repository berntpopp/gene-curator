/**
 * Behaviour tests for WorkflowManagement.
 * Stores are real Pinia stores; their actions are stubbed with vi.spyOn.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { call, vmOf } from './vm'
import WorkflowManagement from '@/views/WorkflowManagement.vue'
import { useSchemasStore } from '@/stores/schemas'
import { useWorkflowStore } from '@/stores/workflow'

const confirmMock = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))

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
      {
        id: 'pre',
        name: 'Pre schema',
        version: '1.0',
        schema_type: 'precuration',
        is_active: true
      },
      { id: 'cur', name: 'Cur schema', version: '2.0', schema_type: 'curation', is_active: true }
    ] as never
    const wrapper = mount(WorkflowManagement, opts())
    await flushPromises()
    return { wrapper, schemas, vm: vmOf(wrapper) }
  }

  it('lists pairs with resolved schema names and status', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.text()).toContain('Precuration: Pre schema · v1.0')
    expect(wrapper.text()).toContain('Curation: Cur schema · v2.0')
    expect(wrapper.text()).toContain('Active')
  })

  it('links each pair schema to its editor and drops the static stage grid (#216)', async () => {
    const { wrapper } = await mountView()
    const to = wrapper.findAllComponents(RouterLinkStub).map(l => l.props('to'))
    expect(to).toEqual([
      { name: 'SchemaEditor', params: { id: 'pre' } },
      { name: 'SchemaEditor', params: { id: 'cur' } }
    ])
    expect(wrapper.text()).not.toContain('Workflow stages configuration')
    expect(wrapper.text()).not.toContain('Required Roles')
  })

  it('warns when the chosen schema pair already exists (#216)', async () => {
    const { vm } = await mountView()
    vm.createWorkflowDialog = true
    await nextTick()
    const warning = () => document.body.querySelector('[data-testid="duplicate-pair"]')
    vm.newWorkflow = { ...(vm.newWorkflow as object), precuration_schema_id: 'pre' }
    await flushPromises()
    expect(warning()).toBeNull()
    vm.newWorkflow = { ...(vm.newWorkflow as object), curation_schema_id: 'cur' }
    await flushPromises()
    expect(warning()?.textContent).toContain('ClinGen flow')
  })

  it('loads inactive pairs and schemas too', async () => {
    const schemas = useSchemasStore()
    const fetchSchemas = vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
    const fetchPairs = vi.spyOn(schemas, 'fetchWorkflowPairs').mockResolvedValue(undefined as never)
    vi.spyOn(useWorkflowStore(), 'fetchWorkflowAnalytics').mockResolvedValue(null as never)
    vi.spyOn(useWorkflowStore(), 'fetchPeerReviewers').mockResolvedValue(null as never)
    mount(WorkflowManagement, opts())
    await flushPromises()
    expect(fetchSchemas).toHaveBeenCalledWith({ active_only: false })
    expect(fetchPairs).toHaveBeenCalledWith({ active_only: false })
  })

  it('offers only active schemas in the create-pair dropdowns', async () => {
    const { schemas, vm } = await mountView()
    schemas.schemas = [
      { id: 'a', name: 'A', schema_type: 'curation', is_active: true },
      { id: 'b', name: 'B', schema_type: 'curation', is_active: false }
    ] as never
    await nextTick()
    expect((vm.curationSchemas as { id: string }[]).map(x => x.id)).toEqual(['a'])
  })

  it('labels schema options with version and sorts them stably (#471)', async () => {
    const { schemas, vm } = await mountView()
    const sop = 'ClinGen SOP'
    const make = (id: string, version: string, created_at: string) =>
      ({ id, name: sop, version, created_at, schema_type: 'curation', is_active: true }) as never
    schemas.schemas = [
      make('z', '11.0', '2026-10-02T00:00:00Z'),
      make('y', '11.0', '2026-10-01T00:00:00Z'),
      make('x', '10.0', '2026-09-01T00:00:00Z')
    ]
    await nextTick()
    const opts = vm.curationSchemas as { id: string; title: string }[]
    expect(opts.map(o => o.id)).toEqual(['x', 'y', 'z'])
    expect(opts[0]!.title).toBe('ClinGen SOP · v10.0')
    // Same name and version: the creation date tells them apart
    expect(opts[1]!.title).toContain('ClinGen SOP · v11.0 · created')
    expect(opts[1]!.title).not.toBe(opts[2]!.title)
  })

  it('names a deactivated linked schema instead of showing its id (Wave 10 polish)', async () => {
    const { wrapper, schemas } = await mountView()
    schemas.schemas = [
      { id: 'pre', name: 'Old pre', version: '0.9', schema_type: 'precuration', is_active: false },
      { id: 'cur', name: 'Cur schema', version: '2.0', schema_type: 'curation', is_active: true }
    ] as never
    schemas.workflowPairs = [{ ...pair, curation_schema_id: 'gone' }] as never
    await flushPromises()
    expect(wrapper.text()).toContain('Precuration: Old pre · v0.9 (inactive)')
    expect(wrapper.text()).toContain('Curation: Unknown schema')
    expect(wrapper.text()).not.toContain('gone')
  })

  it('shows an inactive pair as Inactive', async () => {
    const { wrapper, schemas } = await mountView()
    schemas.workflowPairs = [{ ...pair, is_active: false }] as never
    await flushPromises()
    expect(wrapper.text()).toContain('Inactive')
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
    expect(document.body.textContent).toContain('Workflow details')
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
    expect((vm.newWorkflow as { version: string }).version).toBe('1.0.0')
    vm.newWorkflow = {
      name: 'New flow',
      description: '',
      version: '2.1.0',
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
      version: '2.1.0',
      is_active: true
    })
    expect((vm.newWorkflow as { version: string }).version).toBe('1.0.0')
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
      curation_schema_id: 'cur',
      version: '1.0.0'
    }
    await flushPromises()
    await call(vm, 'createWorkflow')
    expect(showError).toHaveBeenCalledWith('Failed to create workflow')
  })

  it('reports a failed delete and skips it when not confirmed', async () => {
    const { vm, schemas } = await mountView()
    const del = vi.spyOn(schemas, 'deleteWorkflowPair').mockRejectedValue(new Error('in use'))
    confirmMock.mockResolvedValue(false)
    await call(vm, 'deleteWorkflow', pair)
    expect(del).not.toHaveBeenCalled()
    confirmMock.mockResolvedValue(true)
    await call(vm, 'deleteWorkflow', pair)
    expect(showError).toHaveBeenCalledWith('Failed to delete workflow')
    vi.unstubAllGlobals()
  })

  it('maps stage types to icons and lacks the removed stage-edit placeholder', async () => {
    const { vm } = await mountView()
    expect(call(vm, 'getStageIcon', 'entry')).toBe('mdi-file-document-plus')
    expect(call(vm, 'getStageIcon', 'other')).toBe('mdi-circle')
    expect(call(vm, 'getSchemaName', null, 'curation')).toBe('—')
    expect(vm.editStage).toBeUndefined()
  })
})
