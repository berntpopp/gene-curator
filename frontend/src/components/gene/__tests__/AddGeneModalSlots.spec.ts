/** AddGeneModal gene search slots with real Vuetify (Vuetify 4 slot `item` is the raw HGNC hit). */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { VAutocomplete } from 'vuetify/components'
import AddGeneModal from '../AddGeneModal.vue'

const hit = {
  hgnc_id: 'HGNC:1100',
  symbol: 'BRCA1',
  name: 'BRCA1 DNA repair associated',
  status: 'Approved',
  location: '17q21.31',
  alias_symbols: [],
  previous_symbols: []
}

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast: vi.fn() }) }))
vi.mock('@/composables/useHgncSearch', async () => {
  const { ref } = await import('vue')
  return {
    useHgncSearch: () => ({
      results: ref([hit]),
      isSearching: ref(false),
      search: vi.fn(),
      validateBulk: vi.fn()
    })
  }
})
vi.mock('@/api', () => ({
  genesAPI: { createGene: vi.fn(), bulkCreateGenes: vi.fn(), searchGenes: vi.fn() },
  assignmentsAPI: { createAssignment: vi.fn(), bulkAssignGenes: vi.fn() }
}))

const dialogStub = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }
let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

describe('AddGeneModal slots', () => {
  it('renders hit fields in the menu and the selection', async () => {
    wrapper = mount(AddGeneModal, {
      props: { modelValue: false, scopeId: 'scope-1' },
      global: { stubs: { VDialog: dialogStub } },
      attachTo: document.body
    })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()
    wrapper.findComponent(VAutocomplete).vm.menu = true
    await flushPromises()
    const text = document.body.textContent ?? ''
    expect(text).toContain('BRCA1')
    expect(text).toContain('Approved')
    expect(text).toContain('HGNC:1100')
    expect(text).toContain('BRCA1 DNA repair associated')
    expect(text).toContain('17q21.31')

    ;(wrapper.vm as unknown as { selectedGene: unknown }).selectedGene = hit
    await flushPromises()
    expect(document.body.textContent).toContain('(HGNC:1100)')
  })
})
