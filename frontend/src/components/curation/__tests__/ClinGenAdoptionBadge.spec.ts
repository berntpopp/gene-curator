import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createVuetify } from 'vuetify'
import ClinGenAdoptionBadge from '../ClinGenAdoptionBadge.vue'

const vuetify = createVuetify()
const link = 'https://search.clinicalgenome.org/kb/gene-validity/CGGV:assertion_x'

function badge(adoption: { [key: string]: unknown } | null) {
  return mount(ClinGenAdoptionBadge, { props: { adoption }, global: { plugins: [vuetify] } })
}

describe('ClinGenAdoptionBadge', () => {
  it('links the ClinGen record of an adopted curation', () => {
    const w = badge({ permalink: link, classification: 'Definitive', expert_panel: 'GCEP' })
    expect(w.text()).toContain('Adopted from ClinGen')
    expect(w.find('a').attributes('href')).toBe(link)
    expect(w.find('a').attributes('title')).toBe('Definitive · GCEP')
  })

  it('shows nothing for our own curation or a link that is not https', () => {
    expect(badge(null).html()).not.toContain('ClinGen')
    expect(badge({ permalink: 'javascript:alert(1)' }).html()).not.toContain('ClinGen')
  })
})
