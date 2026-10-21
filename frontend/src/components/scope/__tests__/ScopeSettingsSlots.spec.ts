/** ScopeSettings workflow-pair select slots with real Vuetify (Vuetify 4 slot `item` is the raw pair). */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { VSelect } from 'vuetify/components'
import { useAuthStore } from '@/stores/auth'
import ScopeSettings from '../ScopeSettings.vue'

vi.mock('@/api/scopes', () => ({ scopesAPI: { updateScope: vi.fn(), deleteScope: vi.fn() } }))
vi.mock('@/api/schemas', () => ({
  schemasAPI: {
    getWorkflowPairs: vi.fn().mockResolvedValue([
      {
        id: 'wp-1',
        name: 'ClinGen SOP v11',
        version: '1.0',
        description: 'Standard workflow',
        precuration_schema_id: 'a',
        curation_schema_id: 'b',
        is_active: true
      }
    ]),
    getSchemas: vi.fn().mockResolvedValue([])
  }
}))
vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('ScopeSettings slots', () => {
  it('renders pair version and description in the menu and name in the selection', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    const auth = useAuthStore()
    auth.user = { id: 'u9', role: 'admin' } as typeof auth.user
    auth.isAuthenticated = true
    wrapper = mount(ScopeSettings, {
      props: {
        scope: {
          id: 'scope-1',
          name: 'kidney',
          display_name: 'Kidney',
          description: '',
          institution: '',
          is_public: false,
          created_by: 'u1',
          default_workflow_pair_id: 'wp-1'
        } as never
      },
      global: { plugins: [pinia] },
      attachTo: document.body
    })
    await flushPromises()
    expect(wrapper.text()).toContain('ClinGen SOP v11 (1.0)')

    wrapper.findComponent(VSelect).vm.menu = true
    await flushPromises()
    expect(document.body.textContent).toContain('1.0 • Standard workflow')
  })
})
