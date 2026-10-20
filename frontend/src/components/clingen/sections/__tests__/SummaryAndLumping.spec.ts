import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import SummarySection from '../SummarySection.vue'
import LumpingSplittingSection from '../LumpingSplittingSection.vue'

describe('SummarySection', () => {
  it('shows classification and score totals with one and two decimals', () => {
    const wrapper = mount(SummarySection, {
      props: {
        classification: 'Moderate',
        geneticScore: 2.5,
        experimentalScore: 1,
        totalScore: 3.5
      }
    })
    expect(wrapper.text()).toContain('Moderate')
    expect(wrapper.text()).toContain('2.5')
    expect(wrapper.text()).toContain('3.5')
    expect(wrapper.text()).toContain('3.50')
  })

  it('emits update:evidence-summary when the narrative changes', async () => {
    const wrapper = mount(SummarySection, { props: { evidenceSummary: 'start' } })
    wrapper.findComponent({ name: 'VTextarea' }).vm.$emit('update:modelValue', 'New narrative')
    expect(wrapper.emitted('update:evidence-summary')?.[0]).toEqual(['New narrative'])
  })

  it('follows external updates to evidenceSummary', async () => {
    const wrapper = mount(SummarySection, { props: { evidenceSummary: 'first' } })
    await wrapper.setProps({ evidenceSummary: 'second' })
    expect(wrapper.findComponent({ name: 'VTextarea' }).props('modelValue')).toBe('second')
  })
})

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
