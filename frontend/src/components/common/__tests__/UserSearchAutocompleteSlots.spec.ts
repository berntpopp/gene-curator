/** UserSearchAutocomplete slot rendering with real Vuetify (Vuetify 4 slot `item` is the raw user). */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { VAutocomplete } from 'vuetify/components'
import UserSearchAutocomplete from '../UserSearchAutocomplete.vue'

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('@/services/scopeService', () => ({ scopeService: { searchUsersForInvite: vi.fn() } }))

const ada = {
  id: 'u1',
  name: 'Ada Lovelace',
  email: 'ada@example.org',
  institution: 'Berlin',
  displayName: 'Ada Lovelace'
}
const grace = { id: 'u2', name: null, email: 'grace@example.org', displayName: 'grace@example.org' }

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('UserSearchAutocomplete slots', () => {
  it('renders user fields in the open menu', async () => {
    wrapper = mount(UserSearchAutocomplete, {
      props: { scopeId: 's1' },
      attachTo: document.body
    })
    ;(wrapper.vm as unknown as { searchResults: unknown[] }).searchResults = [ada, grace]
    await flushPromises()
    wrapper.findComponent(VAutocomplete).vm.menu = true
    await flushPromises()
    const text = document.body.textContent ?? ''
    expect(text).toContain('Ada Lovelace')
    expect(text).toContain('ada@example.org')
    expect(text).toContain('(Berlin)')
    expect(text).toContain('grace@example.org')
  })

  it('renders the selected user as a chip', async () => {
    wrapper = mount(UserSearchAutocomplete, {
      props: { scopeId: 's1', modelValue: ada as never },
      attachTo: document.body
    })
    await flushPromises()
    expect(wrapper.find('.v-chip').text()).toContain('Ada Lovelace')
  })
})
