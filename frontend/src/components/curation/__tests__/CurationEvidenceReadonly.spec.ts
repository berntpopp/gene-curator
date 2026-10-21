import { describe, expect, it } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import CurationEvidenceReadonly from '../CurationEvidenceReadonly.vue'
import GeneticEvidenceSection from '@/components/clingen/sections/GeneticEvidenceSection.vue'
import EvidenceDataTable from '@/components/clingen/EvidenceDataTable.vue'

describe('CurationEvidenceReadonly', () => {
  it('renders the narrative and every evidence section read-only', async () => {
    const wrapper = mount(CurationEvidenceReadonly, {
      props: {
        moi: 'AD',
        evidence: {
          evidence_summary: 'The gene is strongly supported.',
          genetic_evidence: { segregation: [{ pmid: '12345', points: 1 }] }
        }
      }
    })
    await flushPromises()
    expect(wrapper.text()).toContain('The gene is strongly supported.')
    const pmid = wrapper.find('input[aria-label^="PMID"]').element as HTMLInputElement
    expect(pmid.value).toBe('12345')
    expect(pmid.readOnly).toBe(true)
    expect(wrapper.findComponent(GeneticEvidenceSection).props('readonly')).toBe(true)
    for (const table of wrapper.findAllComponents(EvidenceDataTable)) {
      expect(table.props('readonly')).toBe(true)
    }
  })

  it('says so when there is no narrative', () => {
    const wrapper = mount(CurationEvidenceReadonly, { props: { evidence: {} } })
    expect(wrapper.text()).toContain('No evidence summary')
  })
})
