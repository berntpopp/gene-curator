import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import LumpingSplittingSection from '../LumpingSplittingSection.vue'

describe('LumpingSplittingSection', () => {
  it('falls back to the nested lumping_splitting block and labels the curation type', () => {
    const wrapper = mount(LumpingSplittingSection, {
      props: {
        precurationData: {
          disease_name: 'Renal cysts',
          mondo_id: 'MONDO:0000001',
          lumping_splitting: { curation_type: 'lumped_entity', rationale: ['assertion'] }
        }
      }
    })
    expect(wrapper.html()).toContain('Renal cysts')
    expect(wrapper.text()).toContain('Curate a "lumped" disease entity from this list')
    expect(wrapper.text()).toContain('Assertion')
  })

  it('shows unknown curation types verbatim and unknown rationales as-is', () => {
    const wrapper = mount(LumpingSplittingSection, {
      props: { precurationData: { curation_type: 'custom_type', rationale: ['custom_reason'] } }
    })
    expect(wrapper.text()).toContain('custom_type')
    expect(wrapper.text()).toContain('custom_reason')
  })

  it('renders a free-text rationale as text, not one chip per character (W9 monkey)', () => {
    const wrapper = mount(LumpingSplittingSection, {
      props: { precurationData: { lumping_splitting: { rationale: 'Same mechanism' } } }
    })
    expect(wrapper.findAll('.v-chip')).toHaveLength(0)
    expect(wrapper.text()).toContain('Same mechanism')
  })

  it('splits comma-separated supporting PMIDs into links', () => {
    const wrapper = mount(LumpingSplittingSection, {
      props: { precurationData: { supporting_pmids: '111, 222' } }
    })
    expect(wrapper.text()).toContain('PMID: 111')
    expect(wrapper.text()).toContain('PMID: 222')
    expect(wrapper.find('a[href="https://pubmed.ncbi.nlm.nih.gov/222"]').exists()).toBe(true)
  })

  it('lists MIM phenotypes and links to the precuration only when an id is present', () => {
    const withLink = mount(LumpingSplittingSection, {
      props: {
        precurationData: {
          id: 'pre-1',
          included_mim_phenotypes: [
            { mim_number: '123456', name: 'Included form', inheritance: null }
          ],
          excluded_mim_phenotypes: [
            { mim_number: '654321', name: 'Excluded form', inheritance: 'AR' }
          ]
        }
      },
      global: { stubs: { RouterLink: true } }
    })
    expect(withLink.text()).toContain('Included MIM Phenotypes')
    expect(withLink.text()).toContain('Excluded MIM Phenotypes')
    expect(withLink.find('a[href="https://omim.org/entry/654321"]').exists()).toBe(true)
    expect(withLink.text()).not.toContain('View Source Precuration')

    const withoutLink = mount(LumpingSplittingSection, {
      props: { precurationData: {} },
      global: { stubs: { RouterLink: true } }
    })
    expect(withoutLink.html()).toContain('Not specified')
    expect(withoutLink.text()).not.toContain('View Source Precuration')
  })
})
