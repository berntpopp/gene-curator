/** ReassignGeneModal curator select slots with real Vuetify (Vuetify 4 slot `item` is the raw curator). */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { VAutocomplete } from 'vuetify/components'
import ReassignGeneModal from '../ReassignGeneModal.vue'
import type { GeneRow } from '../types'

const fetchMembers = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast: vi.fn() }) }))
vi.mock('@/stores/scopes', () => ({ useScopesStore: () => ({ fetchMembers }) }))
vi.mock('@/composables/useRoleColors', () => ({
  useRoleColors: () => ({ getRoleColor: () => 'blue' })
}))
vi.mock('@/api', () => ({ assignmentsAPI: { assignCurator: vi.fn() } }))

const gene = {
  assignment_id: 'a-1',
  gene_id: 'g-1',
  gene_symbol: 'BRCA1',
  gene_hgnc_id: 'HGNC:1100',
  curator_id: 'u-1',
  curator_name: 'Ada',
  priority: 'medium',
  assignment_notes: '',
  stage: 'precuration',
  due_date: null,
  updated_at: '2026-10-20T00:00:00Z'
} as GeneRow

const dialogStub = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }
let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('ReassignGeneModal slots', () => {
  it('renders curator fields in the menu and the selection', async () => {
    fetchMembers.mockResolvedValue([
      { user_id: 'u-1', role: 'curator', user_full_name: 'Ada Lovelace', user_email: 'ada@x.org' },
      { user_id: 'u-2', role: 'curator', user_full_name: 'Grace Hopper', user_email: 'grace@x.org' }
    ])
    wrapper = mount(ReassignGeneModal, {
      props: { modelValue: false, scopeId: 'scope-1', gene },
      global: { stubs: { VDialog: dialogStub } },
      attachTo: document.body
    })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()

    wrapper.findComponent(VAutocomplete).vm.menu = true
    await flushPromises()
    const menu = document.body.textContent ?? ''
    expect(menu).toContain('Grace Hopper')
    expect(menu).toContain('grace@x.org')
    expect(menu).toContain('Current')

    const vm = wrapper.vm as unknown as { selectedCurator: unknown; availableCurators: unknown[] }
    vm.selectedCurator = vm.availableCurators[1]
    await flushPromises()
    expect(wrapper.text()).toContain('Grace Hopper')
  })
})
