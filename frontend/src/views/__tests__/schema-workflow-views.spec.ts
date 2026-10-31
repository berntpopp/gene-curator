/**
 * Behaviour tests for SchemaManagement and SchemaEditor (WorkflowManagement has its own spec).
 * Stores are real Pinia stores; their actions are stubbed with vi.spyOn.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { call, vmOf } from './vm'
import SchemaManagement from '@/views/SchemaManagement.vue'
import SchemaEditor from '@/views/SchemaEditor.vue'
import { useSchemasStore } from '@/stores/schemas'
import AdvancedJson from '@/components/schema-editor/AdvancedJson.vue'
import PointModelBuilder from '@/components/schema-editor/scoring/PointModelBuilder.vue'

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
    vm.selectedStatus = 'inactive'
    await nextTick()
    expect(wrapper.text()).not.toContain('ClinGen curation')
    vm.selectedStatus = 'active'
    await nextTick()
    expect(wrapper.text()).toContain('ClinGen curation')
  })

  it('loads inactive schemas too and marks them inactive, filterable and reactivatable', async () => {
    const schemas = useSchemasStore()
    const fetch = vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
    schemas.schemas = [{ ...curationSchema, id: 's2', name: 'Retired', is_active: false }] as never
    const wrapper = mount(SchemaManagement, opts())
    await flushPromises()
    expect(fetch).toHaveBeenCalledWith({ active_only: false })
    expect(wrapper.text()).toContain('Retired')
    expect(wrapper.text()).toContain('Inactive')
    vmOf(wrapper).selectedStatus = 'active'
    await nextTick()
    expect(wrapper.text()).not.toContain('Retired')
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
    expect(vm.viewSchema).toBeUndefined()
  })

  it('duplicates a schema through the store', async () => {
    const { vm, schemas } = await mountView()
    const pinned = vi.spyOn(schemas, 'fetchPinnedVersion')
    const duplicate = vi
      .spyOn(schemas, 'duplicateSchema')
      .mockResolvedValue({ derived: { id: 's2' }, source: { version: 3 } } as never)
    await call(vm, 'duplicateSchema', row)
    expect(pinned).not.toHaveBeenCalled() // the store reports the version it derived from
    expect(duplicate).toHaveBeenCalledWith('s1', null)
    expect(showSuccess).toHaveBeenCalledWith('Derived from v3 (unpublished edits not included)')
  })

  it('reports a failed duplicate with the backend reason', async () => {
    const { vm, schemas } = await mountView()
    vi.spyOn(schemas, 'duplicateSchema').mockRejectedValue({
      response: { data: { detail: 'Schema with this name and version already exists' } }
    })
    await call(vm, 'duplicateSchema', row)
    expect(showError).toHaveBeenCalledWith('Schema with this name and version already exists')
  })

  it('reports a failed delete', async () => {
    const { vm, schemas } = await mountView()
    vi.spyOn(schemas, 'deleteSchema').mockRejectedValue(new Error('in use'))
    confirmMock.mockResolvedValue(true)
    await call(vm, 'deleteSchema', row)
    expect(showError).toHaveBeenCalledWith('in use')
    vi.unstubAllGlobals()
  })

  it('wraps the header actions on a narrow screen (monkey B11)', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.find('[data-testid="page-header"]').classes()).toContain('flex-wrap')
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
      owner_scope_id: null,
      // Sectioned, so the editor offers Add section (monkey B7)
      field_definitions: {
        sections: [
          {
            id: 'main',
            label: 'Main',
            fields: [{ id: 'example_field', type: 'string', label: 'Example field' }]
          }
        ]
      },
      workflow_states: {
        states: [{ name: 'draft' }, { name: 'submitted' }],
        transitions: { draft: ['submitted'], submitted: [] },
        initial_state: 'draft'
      },
      ui_configuration: { sections: [] },
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
    expect(showError).toHaveBeenCalledWith('bad')
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

  it('shows the real schema fields and their count', async () => {
    const { wrapper } = await mountView()
    expect(wrapper.text()).toContain('Derive')
    expect(wrapper.text()).not.toContain('Duplicate schema')
    expect(wrapper.text()).toContain('curation schema v2.0.0')
    const textareas = wrapper.findAll('textarea').map(t => (t.element as HTMLTextAreaElement).value)
    expect(textareas.some(v => v.includes('"max": 12'))).toBe(true)
    const stats = wrapper.text().replace(/\s+/g, ' ')
    expect(stats).toContain('Total Fields:2')
  })

  it('saves metadata and all five blocks, then leaves edit mode', async () => {
    const { vm, schemas } = await mountView()
    const update = vi
      .spyOn(schemas, 'updateSchema')
      .mockResolvedValue({ ...curationSchema, name: 'Renamed' } as never)
    vm.isEditing = true
    await nextTick()
    vm.editableSchema = { name: 'Renamed', version: '2.0.0', description: 'd', is_active: false }
    call(vm, 'setBlock', 'field_definitions', { x: { type: 'text' } })
    call(vm, 'setBlock', 'ui_configuration', { sections: [] })
    call(vm, 'setBlock', 'scoring_configuration', null)
    await call(vm, 'saveSchema')
    expect(update).toHaveBeenCalledWith('s1', {
      name: 'Renamed',
      version: '2.0.0',
      description: 'd',
      is_active: false,
      field_definitions: { x: { type: 'text' } },
      ui_configuration: { sections: [] },
      validation_rules: {},
      workflow_states: {},
      scoring_configuration: null,
      lock_version: 0
    })
    expect(vm.isEditing).toBe(false)
  })

  it('refuses to save while a JSON block is invalid and flags its tab', async () => {
    const { wrapper, vm, schemas } = await mountView()
    const update = vi.spyOn(schemas, 'updateSchema').mockResolvedValue(undefined as never)
    vm.isEditing = true
    await nextTick()
    const ui = wrapper.findComponent(AdvancedJson).findAll('textarea')[1]! // fields, ui, ...
    await ui.setValue('{nope')
    expect(vm.hasJsonErrors).toBe(true)
    expect(wrapper.text()).toContain('JSON')
    await call(vm, 'saveSchema')
    expect(update).not.toHaveBeenCalled()
    await ui.setValue('{"sections": []}')
    expect(vm.hasJsonErrors).toBe(false)
    expect((vm.draft as Record<string, unknown>).ui_configuration).toEqual({ sections: [] })
  })

  it('shows the backend reason when a save fails', async () => {
    const { vm, schemas } = await mountView()
    vi.spyOn(schemas, 'updateSchema').mockRejectedValue({
      response: { data: { detail: 'Not enough permissions' } }
    })
    vm.isEditing = true
    await nextTick()
    await call(vm, 'saveSchema')
    expect(showError).toHaveBeenCalledWith('Not enough permissions')
    expect(vm.isEditing).toBe(true)
  })

  it('blocks save while the scoring JSON is invalid and says why', async () => {
    const { wrapper, vm, schemas } = await mountView()
    const update = vi.spyOn(schemas, 'updateSchema').mockResolvedValue(undefined as never)
    vm.isEditing = true
    await nextTick()
    const scoring = wrapper.findComponent(AdvancedJson).findAll('textarea')[3]!
    await scoring.setValue('{bad')
    const message = (vm.jsonErrors as Record<string, string>).scoring_configuration
    expect(message).not.toBe('')
    expect(wrapper.text()).toContain(String(message))
    await call(vm, 'saveSchema')
    expect(update).not.toHaveBeenCalled()
    await scoring.setValue('{"max": 1}')
    expect(vm.hasJsonErrors).toBe(false)
    expect((vm.draft as Record<string, unknown>).scoring_configuration).toEqual({ max: 1 })
  })

  it('shows scoring even when the schema has none, so it can be added', async () => {
    const schemas = useSchemasStore()
    vi.spyOn(schemas, 'fetchSchemaById').mockResolvedValue({
      ...curationSchema,
      scoring_configuration: null
    } as never)
    const wrapper = mount(SchemaEditor, opts())
    await flushPromises()
    expect(wrapper.text()).toContain('Scoring configuration (JSON)') // read-only outside edit mode
    vmOf(wrapper).isEditing = true
    await nextTick()
    // edit mode mounts the point-model builder (W10I) on the Scoring tab
    expect(wrapper.findComponent(PointModelBuilder).props('fieldDefinitions')).toEqual(
      curationSchema.field_definitions
    )
    expect(wrapper.text()).toContain('Scoring engine')
    wrapper
      .findComponent(PointModelBuilder)
      .vm.$emit('update:modelValue', { engine: 'point_model' })
    expect((vmOf(wrapper).draft as Record<string, unknown>).scoring_configuration).toEqual({
      engine: 'point_model'
    })
  })

  it('goes back to the schema list, not browser history', async () => {
    const { wrapper } = await mountView()
    await wrapper.find('[aria-label="Go back"]').trigger('click')
    expect(routerPush).toHaveBeenCalledWith({ name: 'SchemaManagement' })
  })

  it('shows no 1/1/1970 and no required-fields count', async () => {
    const schemas = useSchemasStore()
    vi.spyOn(schemas, 'fetchSchemaById').mockResolvedValue({
      ...curationSchema,
      updated_at: null
    } as never)
    const wrapper = mount(SchemaEditor, opts())
    await flushPromises()
    const text = wrapper.text()
    expect(text).not.toContain('1970')
    expect(text).not.toContain('Required Fields')
    expect(text.replace(/\s+/g, ' ')).toContain('Last Modified:—')
  })

  it('restores the original values on cancel', async () => {
    const { vm } = await mountView()
    vm.isEditing = true
    vm.editableSchema = { name: 'Changed' }
    call(vm, 'setBlock', 'field_definitions', { junk: { type: 'text' } })
    call(vm, 'cancelEdit')
    expect(vm.isEditing).toBe(false)
    expect((vm.editableSchema as { name: string }).name).toBe('ClinGen curation')
    expect((vm.draft as Record<string, unknown>).field_definitions).toEqual(
      curationSchema.field_definitions
    )
  })

  it('shows the validation errors and warnings inline, and Valid when clean', async () => {
    const { wrapper, vm, schemas } = await mountView()
    const validate = vi.spyOn(schemas, 'validateSchema').mockResolvedValue({
      is_valid: false,
      errors: ['Missing required field: x'],
      warnings: ['No engine']
    } as never)
    await call(vm, 'validateSchema')
    await flushPromises()
    expect(validate).toHaveBeenCalledWith('s1')
    expect(wrapper.text()).toContain('Missing required field: x')
    expect(wrapper.text()).toContain('No engine')
    validate.mockResolvedValue({ is_valid: true, errors: [], warnings: [] } as never)
    await call(vm, 'validateSchema')
    await flushPromises()
    expect(wrapper.text()).not.toContain('Missing required field: x')
    expect(wrapper.text()).toContain('Schema is valid')
  })

  it('reports a failed validation request', async () => {
    const { vm, schemas } = await mountView()
    vi.spyOn(schemas, 'validateSchema').mockRejectedValue(new Error('x'))
    await call(vm, 'validateSchema')
    expect(showError).toHaveBeenCalledWith('x')
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

  it('duplicates the schema and opens the copy, or shows the reason', async () => {
    const { vm, schemas } = await mountView()
    const create = vi
      .spyOn(schemas, 'duplicateSchema')
      .mockResolvedValue({ derived: { id: 's9' }, source: { version: 1 } } as never)
    await call(vm, 'duplicateSchema')
    expect(routerPush).toHaveBeenCalledWith({ name: 'SchemaEditor', params: { id: 's9' } })
    create.mockRejectedValueOnce(new Error('dup'))
    await call(vm, 'duplicateSchema')
    expect(showError).toHaveBeenCalledWith('dup')
    create.mockRejectedValueOnce({})
    await call(vm, 'duplicateSchema')
    expect(showError).toHaveBeenCalledWith('Failed to derive schema')
  })

  it('deletes after confirmation and returns to the list', async () => {
    const { vm, schemas } = await mountView()
    const del = vi.spyOn(schemas, 'deleteSchema').mockResolvedValue(undefined as never)
    confirmMock.mockResolvedValue(false)
    await call(vm, 'deleteSchema')
    expect(del).not.toHaveBeenCalled()
    confirmMock.mockResolvedValue(true)
    await call(vm, 'deleteSchema')
    expect(del).toHaveBeenCalledWith('s1')
    expect(routerPush).toHaveBeenCalledWith({ name: 'SchemaManagement' })
    del.mockRejectedValueOnce(new Error('in use'))
    await call(vm, 'deleteSchema')
    expect(showError).toHaveBeenCalledWith('in use')
    vi.unstubAllGlobals()
  })
})
