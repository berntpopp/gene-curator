/**
 * Setup pages for scope admins (#284): their scopes' templates and workflows are editable,
 * global ones are listed read-only, and new items belong to the chosen owner.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { vmOf } from './vm'
import SchemaManagement from '@/views/SchemaManagement.vue'
import WorkflowManagement from '@/views/WorkflowManagement.vue'
import { useAuthStore } from '@/stores/auth'
import { useSchemasStore } from '@/stores/schemas'
import { useScopesStore } from '@/stores/scopes'
import { useWorkflowStore } from '@/stores/workflow'

vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push: vi.fn() })
}))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

let pinia: ReturnType<typeof createPinia>
const opts = () => ({
  attachTo: document.body,
  global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } }
})
const base = { schema_type: 'curation', is_active: true, version: '1.0' }
const rows = [
  { ...base, id: 'g', name: 'Global template', owner_scope_id: null },
  { ...base, id: 'own', name: 'Kidney template', owner_scope_id: 's1' },
  { ...base, id: 'foreign', name: 'Other template', owner_scope_id: 'other' }
]

beforeEach(() => {
  pinia = createPinia()
  setActivePinia(pinia)
  useAuthStore().user = { id: 'u', role: 'user' } as never
  useScopesStore().scopes = [
    { id: 's1', name: 'kidney', display_name: 'Kidney', user_role: 'admin' },
    { id: 's2', name: 'eye', display_name: 'Eye', user_role: 'admin' }
  ] as never
  const schemas = useSchemasStore()
  vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
  vi.spyOn(schemas, 'fetchWorkflowPairs').mockResolvedValue(undefined as never)
  schemas.schemas = rows as never
})

afterEach(() => {
  document.body.innerHTML = ''
})

describe('Setup pages for a scope admin', () => {
  it('templates: own editable, global read-only, other scopes hidden, owner chosen', async () => {
    const wrapper = mount(SchemaManagement, opts())
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('Kidney template')
    expect(text).toContain('Global template')
    expect(text).not.toContain('Other template')
    expect(wrapper.findAll('[aria-label="Edit schema"]')).toHaveLength(1)
    expect(wrapper.findAll('[aria-label="Delete schema"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="config-owner"]').exists()).toBe(true)
    expect(text).not.toContain('Import methodology')
    expect(vmOf(wrapper).owner).toBe('s1')
  })

  it('workflows: own editable and the create dialog asks who it belongs to', async () => {
    const workflow = useWorkflowStore()
    vi.spyOn(workflow, 'fetchWorkflowAnalytics').mockResolvedValue(null as never)
    vi.spyOn(workflow, 'fetchPeerReviewers').mockResolvedValue(null as never)
    useSchemasStore().workflowPairs = rows.map(r => ({
      ...r,
      precuration_schema_id: 'g',
      curation_schema_id: 'g'
    })) as never
    const wrapper = mount(WorkflowManagement, opts())
    await flushPromises()
    expect(wrapper.findAll('[aria-label="Edit workflow"]')).toHaveLength(1)
    expect(wrapper.findAll('[aria-label="Delete workflow"]')).toHaveLength(1)
    vmOf(wrapper).createWorkflowDialog = true
    await flushPromises()
    expect(document.querySelector('[data-testid="config-owner"]')).not.toBeNull()
  })
})
