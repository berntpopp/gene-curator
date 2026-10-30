/** SchemaEditor: building fields without JSON, preview and publish (#219) */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { call, vmOf } from './vm'
import SchemaEditor from '@/views/SchemaEditor.vue'
import FieldDialog from '@/components/schema-editor/FieldDialog.vue'
import DynamicForm from '@/components/dynamic/DynamicForm.vue'
import { useSchemasStore } from '@/stores/schemas'

vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useRoute: () => ({ params: { id: 's1' }, query: {} })
}))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('@/composables/useNotifications', () => ({
  showError: vi.fn(),
  showSuccess: vi.fn(),
  showInfo: vi.fn(),
  showWarning: vi.fn()
}))

let pinia: ReturnType<typeof createPinia>
const opts = () => ({ attachTo: document.body, global: { plugins: [pinia] } })

const curationSchema = {
  id: 's1',
  name: 'KGDB curation',
  version: '1.0.0',
  schema_type: 'curation',
  description: '',
  field_definitions: { a: { type: 'text' } },
  validation_rules: {},
  workflow_states: {},
  ui_configuration: {},
  scoring_configuration: null,
  is_active: true,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-02-01T00:00:00Z'
}

const mountView = async () => {
  vi.spyOn(useSchemasStore(), 'fetchSchemaById').mockResolvedValue(curationSchema as never)
  const wrapper = mount(SchemaEditor, opts())
  await flushPromises()
  return { wrapper, vm: vmOf(wrapper) }
}

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
})
afterEach(() => {
  document.body.innerHTML = ''
})

describe('SchemaEditor field builder', () => {
  it('adds a field without JSON, shows it in the preview and saves it (#219)', async () => {
    const schemas = useSchemasStore()
    vi.spyOn(schemas, 'fetchSchemaById').mockResolvedValue({
      ...curationSchema,
      field_definitions: {},
      ui_configuration: {}
    } as never)
    const update = vi
      .spyOn(schemas, 'updateSchema')
      .mockImplementation(async (_id, body) => ({ ...curationSchema, ...body }) as never)
    const wrapper = mount(SchemaEditor, opts())
    await flushPromises()
    const vm = vmOf(wrapper)
    vm.isEditing = true
    await nextTick()
    const addSection = wrapper.findAll('button').find(b => b.text().includes('Add section'))!
    await addSection.trigger('click')
    await wrapper
      .findAll('button')
      .find(b => b.text().includes('Add field'))!
      .trigger('click')
    await flushPromises()
    wrapper
      .findComponent(FieldDialog)
      .vm.$emit('save', { id: 'kidney_relevance', type: 'text', label: 'Kidney relevance' })
    await flushPromises()
    expect(wrapper.text()).toContain('Kidney relevance')
    vm.tab = 'preview'
    await flushPromises()
    expect(wrapper.findComponent(DynamicForm).text()).toContain('Kidney relevance')
    await call(vm, 'saveSchema')
    expect(update.mock.calls[0]![1].field_definitions).toEqual({
      sections: [
        {
          id: 'section_1',
          label: 'Section 1',
          fields: [{ id: 'kidney_relevance', type: 'text', label: 'Kidney relevance' }]
        }
      ]
    })
    expect(vm.isEditing).toBe(false)
  })

  it('opens the publish dialog only outside edit mode', async () => {
    const { wrapper, vm } = await mountView()
    const publish = () => wrapper.findAll('button').find(b => b.text().includes('Publish version'))!
    expect(publish().attributes('disabled')).toBeUndefined()
    vm.isEditing = true
    await nextTick()
    expect(publish().attributes('disabled')).toBeDefined()
  })
})
