import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

// Monkey B4: the curator picks the workflow pair (Mendelian or susceptibility) at the start
vi.mock('@/api', () => ({
  genesAPI: { getGeneById: vi.fn().mockResolvedValue({ approved_symbol: 'APOL1' }) },
  scopesAPI: {
    getScopeById: vi.fn().mockResolvedValue({
      default_workflow_pair_id: 'men',
      allowed_workflow_pair_ids: ['sus']
    })
  },
  schemasAPI: {
    getWorkflowPairs: vi.fn().mockResolvedValue([
      { id: 'men', name: 'KGDB Mendelian', precuration_schema_id: 's-men' },
      { id: 'sus', name: 'KGDB Susceptibility', precuration_schema_id: 's-sus' },
      { id: 'cur', name: 'Curation only', precuration_schema_id: null },
      { id: 'ext', name: 'Not allowed here', precuration_schema_id: 's-ext' }
    ])
  }
}))
vi.mock('@/api/precurations', () => ({ precurationsAPI: { getPrecuration: vi.fn() } }))
const route = vi.hoisted(() => ({ params: {} as Record<string, string>, query: {} }))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => route,
  onBeforeRouteLeave: vi.fn()
}))

import { scopesAPI } from '@/api'
import { precurationsAPI } from '@/api/precurations'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import PrecurationFormView from '@/views/curation/PrecurationFormView.vue'

const mountView = async () => {
  const wrapper = mount(PrecurationFormView, {
    global: { stubs: { SchemaDrivenPrecurationForm: true } }
  })
  await flushPromises()
  return wrapper
}
const formSchema = (w: Awaited<ReturnType<typeof mountView>>) =>
  w.findComponent({ name: 'SchemaDrivenPrecurationForm' }).props('schemaId')

beforeEach(() => {
  setActivePinia(createPinia())
  vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue('curator' as never)
})

describe('PrecurationFormView workflow pair', () => {
  it('starts on the scope default and switches to the picked pair', async () => {
    route.params = { scopeId: 'sc1', geneId: 'g1' }
    const wrapper = await mountView()
    expect(formSchema(wrapper)).toBe('s-men')
    const select = wrapper.findComponent({ name: 'VSelect' })
    expect(select.props('items')).toHaveLength(2)
    const before = wrapper.findComponent({ name: 'SchemaDrivenPrecurationForm' }).vm
    select.vm.$emit('update:modelValue', 'sus')
    await flushPromises()
    expect(formSchema(wrapper)).toBe('s-sus')
    // A fresh form: the new pair's schema and defaults (relationship type), nothing of the old one
    expect(wrapper.findComponent({ name: 'SchemaDrivenPrecurationForm' }).vm).not.toBe(before)
  })

  it('offers only the scope default when the scope allows no other pair (#284)', async () => {
    vi.mocked(scopesAPI.getScopeById).mockResolvedValueOnce({
      default_workflow_pair_id: 'men'
    } as never)
    route.params = { scopeId: 'sc1', geneId: 'g1' }
    const wrapper = await mountView()
    expect(formSchema(wrapper)).toBe('s-men')
    expect(wrapper.find('[data-testid="workflow-pair"]').exists()).toBe(false)
  })

  it('opens a saved precuration with its own schema and no picker', async () => {
    useAuthStore().user = { id: 'me' } as never
    route.params = { scopeId: 'sc1', precurationId: 'p1' }
    vi.mocked(precurationsAPI.getPrecuration).mockResolvedValue({
      id: 'p1',
      gene_id: 'g1',
      status: 'draft',
      created_by: 'me',
      scope_id: 'sc1',
      precuration_schema_id: 's-sus'
    } as never)
    const wrapper = await mountView()
    expect(formSchema(wrapper)).toBe('s-sus')
    expect(wrapper.find('[data-testid="workflow-pair"]').exists()).toBe(false)
  })
})
