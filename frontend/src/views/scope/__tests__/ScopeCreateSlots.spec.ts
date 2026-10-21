/** ScopeCreate slot rendering with real Vuetify (Vuetify 4 slot `item` is the raw value). */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { VAutocomplete, VSelect } from 'vuetify/components'
import ScopeCreate from '../ScopeCreate.vue'
import { useScopesStore } from '@/stores/scopes'

vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), back: vi.fn() }),
  useRoute: () => ({ params: {}, query: {} })
}))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('@/api/users', () => ({ usersApi: { searchUsers: vi.fn() } }))
vi.mock('@/api/schemas', () => ({
  schemasAPI: { getWorkflowPairs: vi.fn().mockResolvedValue([]), getSchemas: vi.fn() }
}))

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('ScopeCreate slots', () => {
  it('renders user and role options in the add-member dialog', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    vi.spyOn(useScopesStore(), 'fetchUserScopes').mockResolvedValue(undefined as never)
    wrapper = mount(ScopeCreate, {
      attachTo: document.body,
      global: { plugins: [pinia], stubs: { RouterLink: RouterLinkStub } }
    })
    await flushPromises()
    ;(wrapper.vm as unknown as { showAddMemberDialog: boolean }).showAddMemberDialog = true
    ;(wrapper.vm as unknown as { userSearchResults: unknown[] }).userSearchResults = [
      { id: 'u1', name: 'Ada Lovelace', email: 'ada@example.org', displayName: 'Ada Lovelace' }
    ]
    await flushPromises()

    wrapper.findComponent(VAutocomplete).vm.menu = true
    await flushPromises()
    expect(document.body.textContent).toContain('ada@example.org')

    const role = wrapper.findAllComponents(VSelect).find(c => c.props('label') === 'Role')
    if (role) role.vm.menu = true
    await flushPromises()
    const icons = [...document.body.querySelectorAll('.v-list-item .v-icon')].map(i => i.className)
    expect(icons.some(c => c.includes('mdi-shield-crown'))).toBe(true)
    expect(icons.some(c => c.includes('mdi-eye'))).toBe(true)
  })
})
