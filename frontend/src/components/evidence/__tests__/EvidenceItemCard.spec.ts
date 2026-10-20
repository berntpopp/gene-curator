/**
 * EvidenceItemCard Tests
 *
 * Covers what a curator sees on an evidence card (category, score, PMIDs,
 * metadata summary) and the edit/delete actions.
 */
import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import EvidenceItemCard from '../EvidenceItemCard.vue'
import { stubVisualViewport } from './overlayStubs'

const baseEvidence = {
  evidence_category: 'case_level',
  description: 'Two affected probands with frameshift variants',
  computed_score: 3,
  pmids: ['12345678'],
  metadata: { variant_count: 2, family_count: 1, proband_count: 3 }
}

describe('EvidenceItemCard', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the formatted category, score, description and 1-based index', () => {
    const wrapper = mount(EvidenceItemCard, { props: { evidence: baseEvidence, index: 1 } })

    expect(wrapper.text()).toContain('Case Level')
    expect(wrapper.text()).toContain('3 points')
    expect(wrapper.text()).toContain('Two affected probands with frameshift variants')
    expect(wrapper.text()).toContain('#2')
  })

  it('links each PMID to PubMed', () => {
    const wrapper = mount(EvidenceItemCard, { props: { evidence: baseEvidence, index: 0 } })

    const link = wrapper.find('a[href="https://pubmed.ncbi.nlm.nih.gov/12345678/"]')
    expect(link.exists()).toBe(true)
    expect(link.text()).toContain('PMID:12345678')
  })

  it('summarises metadata counts and omits empty ones', () => {
    const wrapper = mount(EvidenceItemCard, { props: { evidence: baseEvidence, index: 0 } })
    expect(wrapper.text()).toContain('2 variants, 1 families, 3 probands')

    const sparse = mount(EvidenceItemCard, {
      props: { evidence: { evidence_category: 'rescue', metadata: { family_count: 2 } }, index: 0 }
    })
    expect(sparse.text()).toContain('2 families')
    expect(sparse.text()).not.toContain('variants')
  })

  it('omits the score chip, PMID row and metadata when they are absent', () => {
    const wrapper = mount(EvidenceItemCard, {
      props: { evidence: { evidence_category: 'models', pmids: [], metadata: null }, index: 0 }
    })

    expect(wrapper.text()).not.toContain('points')
    expect(wrapper.findAll('a[href*="pubmed"]')).toHaveLength(0)
    expect(wrapper.text()).toContain('Models')
  })

  it('falls back to a grey chip for unknown categories', () => {
    const wrapper = mount(EvidenceItemCard, {
      props: { evidence: { evidence_category: 'unknown_kind' }, index: 0 }
    })

    expect(wrapper.text()).toContain('Unknown Kind')
  })

  it('emits delete only after the user confirms', async () => {
    const wrapper = mount(EvidenceItemCard, { props: { evidence: baseEvidence, index: 0 } })
    const vm = wrapper.vm as unknown as { handleDelete: () => void }

    vi.stubGlobal('confirm', vi.fn().mockReturnValue(false))
    vm.handleDelete()
    expect(wrapper.emitted('delete')).toBeUndefined()

    vi.stubGlobal('confirm', vi.fn().mockReturnValue(true))
    vm.handleDelete()
    expect(wrapper.emitted('delete')).toHaveLength(1)
  })

  it('opens the actions menu and emits edit from the Edit item', async () => {
    stubVisualViewport()
    const wrapper = mount(EvidenceItemCard, {
      props: { evidence: baseEvidence, index: 0 },
      attachTo: document.body
    })

    await wrapper.find('button[aria-label="Evidence actions"]').trigger('click')
    await new Promise(resolve => setTimeout(resolve, 0))
    const editItem = Array.from(document.querySelectorAll('.v-list-item'))
      .filter(el => el.textContent?.includes('Edit'))
      .pop() as HTMLElement | undefined
    expect(editItem).toBeDefined()
    editItem?.click()

    expect(wrapper.emitted('edit')).toHaveLength(1)
    wrapper.unmount()
  })
})
