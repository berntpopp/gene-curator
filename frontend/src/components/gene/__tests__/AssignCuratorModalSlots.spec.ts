/** AssignCuratorModal slots with real Vuetify (Vuetify 4 slot `item` is the raw gene/curator). */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { VAutocomplete } from 'vuetify/components'
import AssignCuratorModal from '../AssignCuratorModal.vue'
import { assignmentsAPI } from '@/api'

const fetchMembers = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast: vi.fn() }) }))
vi.mock('@/stores/scopes', () => ({ useScopesStore: () => ({ fetchMembers }) }))
vi.mock('@/composables/useRoleColors', () => ({
  useRoleColors: () => ({ getRoleColor: () => 'grey' })
}))
vi.mock('@/api', () => ({
  assignmentsAPI: { getAssignmentsByScope: vi.fn(), bulkAssignGenes: vi.fn() }
}))

const dialogStub = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }
let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('AssignCuratorModal slots', () => {
  it('renders gene and curator fields in menus, chips and selection', async () => {
    vi.mocked(assignmentsAPI.getAssignmentsByScope).mockResolvedValue([
      { gene_id: 'g-1', gene_symbol: 'BRCA1', gene_hgnc_id: 'HGNC:1100', is_active: true }
    ] as never)
    fetchMembers.mockResolvedValue([
      { user_id: 'u-1', role: 'curator', user_full_name: 'Ada Lovelace', user_email: 'ada@x.org' }
    ])
    wrapper = mount(AssignCuratorModal, {
      props: { modelValue: true, scopeId: 'scope-1' },
      global: { stubs: { VDialog: dialogStub } },
      attachTo: document.body
    })
    await flushPromises()
    const [genes, curators] = wrapper.findAllComponents(VAutocomplete)

    genes!.vm.menu = true
    await flushPromises()
    expect(document.body.textContent).toContain('BRCA1')
    expect(document.body.textContent).toContain('HGNC:1100')
    genes!.vm.menu = false

    curators!.vm.menu = true
    await flushPromises()
    const menu = document.body.textContent ?? ''
    expect(menu).toContain('Ada Lovelace')
    expect(menu).toContain('curator')
    expect(menu).toContain('ada@x.org')

    const vm = wrapper.vm as unknown as { selectedGenes: unknown[]; selectedCurator: unknown }
    vm.selectedGenes = [{ id: 'g-1', approved_symbol: 'BRCA1', hgnc_id: 'HGNC:1100' }]
    vm.selectedCurator = (
      wrapper.vm as unknown as { availableCurators: unknown[] }
    ).availableCurators[0]
    await flushPromises()
    expect(wrapper.find('.v-chip').text()).toContain('BRCA1')
    expect(wrapper.text()).toContain('Ada Lovelace')
  })
})
