/**
 * HPOInheritanceSelect Tests
 *
 * Loads inheritance patterns, adds shortcodes, selects by HPO ID or shortcode,
 * and emits the selection. Internals are reached through the component instance.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { ontologyAPI } from '@/api'
import HPOInheritanceSelect from '../HPOInheritanceSelect.vue'

vi.mock('@/api', () => ({
  ontologyAPI: { getInheritancePatterns: vi.fn() }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

interface Pattern {
  hpo_id: string
  name: string
  shortcode?: string | null
  displayText?: string
  isHeader?: boolean
}

interface SelectInternals {
  mendelianPatterns: Pattern[]
  nonMendelianPatterns: Pattern[]
  selectedItem: Pattern | null
  loadError: string | null | undefined
  inheritanceItems: Pattern[]
  errorMessages: string[]
  handleSelect: (item: Pattern | null | undefined) => void
  findAndSelectItem: (value: string) => void
}

const response = {
  total_patterns: 3,
  cached: true,
  mendelian: [
    { hpo_id: 'HP:0000006', name: 'Autosomal dominant inheritance', category: 'mendelian' },
    { hpo_id: 'HP:0001419', name: 'X-linked recessive inheritance', category: 'mendelian' }
  ],
  non_mendelian: [
    { hpo_id: 'HP:0010982', name: 'Polygenic inheritance', category: 'non_mendelian' }
  ]
}

describe('HPOInheritanceSelect', () => {
  beforeEach(() => {
    vi.mocked(ontologyAPI.getInheritancePatterns).mockReset()
    vi.mocked(ontologyAPI.getInheritancePatterns).mockResolvedValue(response)
  })

  async function mountSelect(props: Record<string, unknown> = {}) {
    const wrapper = mount(HPOInheritanceSelect, { props })
    await flushPromises()
    return { wrapper, vm: wrapper.vm as unknown as SelectInternals }
  }

  it('maps the X-linked HPO terms to their own shortcodes', async () => {
    vi.mocked(ontologyAPI.getInheritancePatterns).mockResolvedValue({
      ...response,
      mendelian: [
        { hpo_id: 'HP:0001417', name: 'X-linked inheritance', category: 'mendelian' },
        { hpo_id: 'HP:0001423', name: 'X-linked dominant inheritance', category: 'mendelian' },
        { hpo_id: 'HP:0001419', name: 'X-linked recessive inheritance', category: 'mendelian' }
      ]
    })
    const { vm } = await mountSelect()
    expect(vm.mendelianPatterns.map(p => p.shortcode)).toEqual(['XL', 'XLD', 'XLR'])
  })

  it('loads patterns on mount, adds shortcodes and builds section headers', async () => {
    const { vm } = await mountSelect()

    expect(ontologyAPI.getInheritancePatterns).toHaveBeenCalledTimes(1)
    expect(vm.mendelianPatterns.map(p => p.shortcode)).toEqual(['AD', 'XLR'])
    expect(vm.nonMendelianPatterns[0]?.shortcode).toBe('PG')

    const headers = vm.inheritanceItems.filter(item => item.isHeader)
    expect(headers.map(h => h.displayText)).toEqual([
      'Mendelian Inheritance',
      'Non-Mendelian Inheritance'
    ])
    expect(vm.inheritanceItems.find(i => i.hpo_id === 'HP:0000006')?.displayText).toBe(
      'Autosomal dominant inheritance (AD)'
    )
  })

  it('preselects the pattern matching an HPO ID passed on mount', async () => {
    const { vm } = await mountSelect({ hpoId: 'HP:0010982' })

    expect(vm.selectedItem?.name).toBe('Polygenic inheritance')
  })

  it('selects by shortcode when the value is not an HPO ID', async () => {
    const { vm } = await mountSelect()

    vm.findAndSelectItem('XLR')
    expect(vm.selectedItem?.hpo_id).toBe('HP:0001419')

    vm.findAndSelectItem('HP:0000006')
    expect(vm.selectedItem?.hpo_id).toBe('HP:0000006')

    vm.findAndSelectItem('')
    expect(vm.selectedItem?.hpo_id).toBe('HP:0000006')
  })

  it('emits the shortcode, HPO ID and item when a pattern is selected', async () => {
    const { wrapper, vm } = await mountSelect()
    const ad = vm.mendelianPatterns[0] as Pattern

    vm.handleSelect(ad)

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['AD'])
    expect(wrapper.emitted('update:hpoId')?.at(-1)).toEqual(['HP:0000006'])
    expect(wrapper.emitted('select')?.at(-1)).toEqual([ad])
    expect(vm.selectedItem?.hpo_id).toBe('HP:0000006')
  })

  it('falls back to the HPO ID when a pattern has no shortcode', async () => {
    const { wrapper, vm } = await mountSelect()

    vm.handleSelect(vm.nonMendelianPatterns[0] as Pattern)
    vm.handleSelect({ hpo_id: 'HP:0000001', name: 'No shortcode', shortcode: null })

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['HP:0000001'])
  })

  it('clears the selection when a header or nothing is chosen', async () => {
    const { wrapper, vm } = await mountSelect({ hpoId: 'HP:0000006' })

    vm.handleSelect({ hpo_id: 'header_mendelian', name: '', isHeader: true })

    expect(vm.selectedItem).toBeNull()
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([''])
    expect(wrapper.emitted('select')?.at(-1)).toEqual([null])

    vm.handleSelect(null)
    expect(wrapper.emitted('select')?.at(-1)).toEqual([null])
  })

  it('follows external hpoId changes once patterns are loaded', async () => {
    const { wrapper, vm } = await mountSelect()

    await wrapper.setProps({ hpoId: 'HP:0001419' })
    expect(vm.selectedItem?.hpo_id).toBe('HP:0001419')

    // Same value again: the selection is left alone
    vm.selectedItem = null
    await wrapper.setProps({ hpoId: 'HP:0001419' })
    expect(vm.selectedItem).toBeNull()
  })

  it('reports a load failure and does not select anything', async () => {
    vi.mocked(ontologyAPI.getInheritancePatterns).mockRejectedValueOnce(new Error('offline'))
    const { vm } = await mountSelect({ hpoId: 'HP:0000006' })

    expect(vm.loadError).toBe('offline')
    expect(vm.selectedItem).toBeNull()
    expect(vm.errorMessages).toEqual(['Failed to load options'])
  })

  it('requires a value when marked required', async () => {
    const { vm } = await mountSelect({ required: true })

    expect(vm.errorMessages).toEqual(['Mode of inheritance is required'])
  })

  it('lists patterns under their section headers and selects one from the open menu', async () => {
    const wrapper = mount(HPOInheritanceSelect, { props: {}, attachTo: document.body })
    await flushPromises()

    await wrapper.find('.v-field').trigger('mousedown')
    await flushPromises()
    expect(document.body.textContent).toContain('Mendelian Inheritance')
    expect(document.body.textContent).toContain('Non-Mendelian Inheritance')

    const option = Array.from(document.querySelectorAll('.v-list-item'))
      .filter(el => el.textContent?.includes('X-linked recessive inheritance'))
      .pop() as HTMLElement | undefined
    option?.click()
    await flushPromises()

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['XLR'])
    wrapper.unmount()
  })
})
