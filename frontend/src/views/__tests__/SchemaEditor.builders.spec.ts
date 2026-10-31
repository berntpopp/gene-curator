/** SchemaEditor builders (#282): draft diagnostics, workflow stages and the stale-save lock */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { confirmState } from '@/composables/useConfirm'
import { createPinia, setActivePinia } from 'pinia'
import { vmOf, call } from './vm'
import SchemaEditor from '@/views/SchemaEditor.vue'
import WorkflowStagesEditor from '@/components/schema-editor/WorkflowStagesEditor.vue'
import FieldsEditor from '@/components/schema-editor/FieldsEditor.vue'
import { useSchemasStore } from '@/stores/schemas'
import { validationAPI } from '@/api'

vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useRoute: () => ({ params: { id: 's1' }, query: {} })
}))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
const { showError, showWarning } = vi.hoisted(() => ({
  showError: vi.fn(),
  showWarning: vi.fn()
}))
vi.mock('@/composables/useNotifications', () => ({
  showError,
  showSuccess: vi.fn(),
  showInfo: vi.fn(),
  showWarning
}))

const schema = {
  id: 's1',
  name: 'KGDB curation',
  version: '1.0.0',
  schema_type: 'curation',
  description: '',
  field_definitions: { a: { type: 'text', required_when: { b: 1 } } },
  validation_rules: {},
  workflow_states: {
    states: [{ name: 'draft' }, { name: 'submitted' }],
    transitions: { draft: ['submitted'], submitted: ['gone'] }
  },
  ui_configuration: {},
  scoring_configuration: { engine: 'point_model' },
  is_active: true,
  lock_version: 4,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-02-01T00:00:00Z'
}

const report = {
  is_valid: false,
  errors: [
    { field: 'field_definitions.a.required_when.b', message: 'unknown field: b' },
    { field: 'workflow_states.transitions.submitted[0]', message: 'Unknown target: gone' }
  ],
  warnings: []
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.useFakeTimers()
  vi.spyOn(validationAPI, 'validateSchema').mockResolvedValue(report as never)
})
afterEach(() => {
  vi.useRealTimers()
  vi.restoreAllMocks()
  document.body.innerHTML = ''
})

const mountView = async () => {
  const schemas = useSchemasStore()
  vi.spyOn(schemas, 'fetchSchemaById').mockResolvedValue(structuredClone(schema) as never)
  vi.spyOn(schemas, 'fetchVersions').mockResolvedValue([] as never)
  const wrapper = mount(SchemaEditor, { attachTo: document.body })
  await flushPromises()
  await vi.advanceTimersByTimeAsync(700)
  await flushPromises()
  return { wrapper, vm: vmOf(wrapper), schemas }
}

describe('SchemaEditor builders (#282)', () => {
  it('checks the unsaved draft and shows its report inline and as badges', async () => {
    const { wrapper, vm } = await mountView()
    const sent = vi.mocked(validationAPI.validateSchema).mock.calls.at(-1)![0]
    expect(sent.schema_definition).toMatchObject({ workflow_states: schema.workflow_states })
    expect(vm.fieldProblems).toBe(1)
    expect(vm.workflowProblems).toBe(1)
    expect(wrapper.find('[data-testid="draft-diagnostics"]').text()).toContain('(2)')
    expect(wrapper.findComponent(FieldsEditor).text()).toContain('unknown field: b')
  })

  it('opens a stage builder from the workflow table and edits its stages', async () => {
    const { wrapper, vm } = await mountView()
    vm.tab = 'workflow'
    vm.isEditing = true
    await flushPromises()
    const stages = wrapper.findComponent(WorkflowStagesEditor)
    expect(stages.find('[data-testid="stage-submitted"]').text()).toContain('Unknown target')
    await stages
      .findAll('button')
      .find(b => b.text() === 'Open scoring')!
      .trigger('click')
    expect(vm.tab).toBe('scoring')
    stages.vm.$emit('update:modelValue', { states: [{ name: 'draft' }], transitions: {} })
    expect((vm.draft as { workflow_states: unknown }).workflow_states).toEqual({
      states: [{ name: 'draft' }],
      transitions: {}
    })
  })

  it('saves with the loaded lock_version so a stale copy is refused', async () => {
    const { vm, schemas } = await mountView()
    const update = vi
      .spyOn(schemas, 'updateSchema')
      .mockResolvedValue({ ...schema, lock_version: 5 } as never)
    vm.isEditing = true
    await flushPromises()
    await call(vm, 'saveSchema')
    expect(update.mock.calls[0]![1]).toMatchObject({ lock_version: 4 })
  })

  it('keeps the draft after a 409 and the next Save replaces their version', async () => {
    const { vm, schemas } = await mountView()
    const update = vi
      .spyOn(schemas, 'updateSchema')
      .mockRejectedValueOnce({ response: { status: 409, data: { detail: 'stale' } } })
      .mockResolvedValueOnce({ ...schema, lock_version: 6 } as never)
    vm.isEditing = true
    ;(vm.editableSchema as Record<string, unknown>).description = 'mine'
    vi.mocked(schemas.fetchSchemaById).mockResolvedValueOnce({
      ...structuredClone(schema),
      description: 'theirs',
      lock_version: 5
    } as never)
    await call(vm, 'saveSchema')
    await flushPromises()
    expect(showWarning).toHaveBeenCalledWith(
      'Someone else saved this schema. Your draft is kept: Save again to replace their version, or Cancel to load theirs.'
    )
    expect(showError).not.toHaveBeenCalled()
    expect(vm.isEditing).toBe(true)
    expect((vm.editableSchema as Record<string, unknown>).description).toBe('mine')
    await call(vm, 'saveSchema')
    expect(update.mock.calls[1]![1]).toMatchObject({ description: 'mine', lock_version: 5 })
  })

  it('Cancel after a 409 loads their version', async () => {
    const { vm, schemas } = await mountView()
    vi.spyOn(schemas, 'updateSchema').mockRejectedValueOnce({ response: { status: 409 } })
    vm.isEditing = true
    ;(vm.editableSchema as Record<string, unknown>).description = 'mine'
    vi.mocked(schemas.fetchSchemaById).mockResolvedValueOnce({
      ...structuredClone(schema),
      description: 'theirs',
      lock_version: 5
    } as never)
    await call(vm, 'saveSchema')
    await flushPromises()
    const cancelled = call(vm, 'cancelEdit')
    confirmState.settle(true) // discarding the draft asks first (MUI-08)
    await cancelled
    expect((vm.editableSchema as Record<string, unknown>).description).toBe('theirs')
  })
})
