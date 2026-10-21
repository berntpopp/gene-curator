import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import GeneticEvidenceSection from '../GeneticEvidenceSection.vue'
import ExperimentalEvidenceSection from '../ExperimentalEvidenceSection.vue'
import { createEmptyExperimentalEvidence, createEmptyGeneticEvidence } from '../../evidenceDefaults'

const active = (wrapper: ReturnType<typeof mount>) =>
  wrapper.findAll('.v-expansion-panel--active').map(p => p.find('.v-expansion-panel-title').text())

describe('expansion panels follow the rows', () => {
  it('opens the genetic panels that hold rows on mount', () => {
    const modelValue = {
      ...createEmptyGeneticEvidence(),
      case_level: { autosomal_recessive: { other_variant_type: [{ points: 1 }] } },
      segregation: [{ points: 1 }]
    }
    const text = active(mount(GeneticEvidenceSection, { props: { modelValue } })).join('|')
    expect(text).toContain('Autosomal Recessive')
    expect(text).toContain('Segregation')
    expect(text).not.toContain('Case-Control')
  })

  it('opens a genetic panel when a restore fills it', async () => {
    const wrapper = mount(GeneticEvidenceSection, {
      props: { modelValue: createEmptyGeneticEvidence() }
    })
    expect(active(wrapper).join('|')).not.toContain('Segregation')
    await wrapper.setProps({ modelValue: { ...createEmptyGeneticEvidence(), segregation: [{}] } })
    expect(active(wrapper).join('|')).toContain('Segregation')
  })

  it('leaves a panel the user collapsed alone while it keeps its rows', async () => {
    const modelValue = { ...createEmptyGeneticEvidence(), segregation: [{ points: 1 }] }
    const wrapper = mount(GeneticEvidenceSection, { props: { modelValue } })
    const title = wrapper
      .findAll('.v-expansion-panel-title')
      .find(t => t.text().includes('Segregation'))
    await title?.trigger('click')
    await wrapper.setProps({ modelValue: { ...modelValue, segregation: [{ points: 1 }, {}] } })
    expect(active(wrapper).join('|')).not.toContain('Segregation')
  })

  it('opens the experimental panels that hold rows', () => {
    const modelValue = {
      ...createEmptyExperimentalEvidence(),
      models: { cell_culture_model: [{ points: 1 }] }
    }
    const text = active(mount(ExperimentalEvidenceSection, { props: { modelValue } })).join('|')
    expect(text).toContain('Model')
  })

  it('hides Add buttons and the add hint when readonly', () => {
    const g = mount(GeneticEvidenceSection, {
      props: { modelValue: createEmptyGeneticEvidence(), readonly: true }
    })
    const e = mount(ExperimentalEvidenceSection, {
      props: { modelValue: createEmptyExperimentalEvidence(), readonly: true }
    })
    for (const w of [g, e]) {
      expect(w.findAll('button').some(b => b.text().includes('Add'))).toBe(false)
    }
    expect(g.text()).toContain('No evidence recorded')
  })
})
