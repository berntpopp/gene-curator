import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import ClinGenCurationForm from '../ClinGenCurationForm.vue'
import ScoreSummary from '../ScoreSummary.vue'
import type { ClinGenEvidenceData } from '../types'

const gene = { symbol: 'HNF1B', approved_symbol: 'HNF1B', hgnc_id: 'HGNC:5024' }

const withCaseLevel: Partial<ClinGenEvidenceData> = {
  genetic_evidence: {
    case_level: {
      autosomal_dominant_or_x_linked: {
        predicted_or_proven_null: [{ proband_counted_points: 1.5 }],
        other_variant_type: []
      }
    }
  }
}

function findButton(wrapper: VueWrapper, text: string) {
  const button = wrapper.findAll('button').find(b => b.text().includes(text))
  if (!button) throw new Error(`no button "${text}"`)
  return button
}

describe('ClinGenCurationForm', () => {
  let wrapper: VueWrapper | undefined

  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
  })

  it('starts unclassified with submit disabled until genetic evidence exists', () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene } })
    const score = wrapper.findComponent(ScoreSummary)
    expect(score.props('totalScore')).toBe(0)
    expect(score.props('classification')).toBe('No Known Disease Relationship')
    expect(findButton(wrapper, 'Submit for Review').attributes('disabled')).toBeDefined()
  })

  it('scores initial genetic evidence and enables submit', async () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene, initialData: withCaseLevel } })
    await flushPromises()
    const score = wrapper.findComponent(ScoreSummary)
    expect(score.props('totalScore')).toBeCloseTo(1.5)
    expect(score.props('classification')).toBe('Limited')
    expect(findButton(wrapper, 'Submit for Review').attributes('disabled')).toBeUndefined()
  })

  it('reports Disputed when contradictory evidence is present, regardless of score', async () => {
    wrapper = mount(ClinGenCurationForm, {
      props: {
        gene,
        initialData: { ...withCaseLevel, contradictory_evidence: [{ label: 'Lab study' }] }
      }
    })
    await flushPromises()
    expect(wrapper.findComponent(ScoreSummary).props('classification')).toBe('Disputed')
    expect(wrapper.findComponent(ScoreSummary).props('hasContradictory')).toBe(true)
  })

  it('emits save-draft with the current evidence when Save Draft is clicked', async () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene, initialData: withCaseLevel } })
    await findButton(wrapper, 'Save Draft').trigger('click')
    const emitted = wrapper.emitted('save-draft')?.[0]?.[0] as ClinGenEvidenceData
    expect(
      emitted.genetic_evidence.case_level?.autosomal_dominant_or_x_linked?.predicted_or_proven_null
    ).toEqual([{ proband_counted_points: 1.5 }])
  })

  it('emits submit only from a submittable form, via Ctrl+Enter', async () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene } })
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }))
    expect(wrapper.emitted('submit')).toBeUndefined()

    await wrapper.setProps({ initialData: withCaseLevel })
    await flushPromises()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }))
    expect(wrapper.emitted('submit')).toHaveLength(1)
  })

  it('saves a draft on Ctrl+S and prevents the browser default', async () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene } })
    const event = new KeyboardEvent('keydown', { key: 's', ctrlKey: true, cancelable: true })
    document.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
    expect(wrapper.emitted('save-draft')).toHaveLength(1)
  })

  it('disables saving and submitting in read-only mode', () => {
    wrapper = mount(ClinGenCurationForm, {
      props: { gene, readonly: true, initialData: withCaseLevel }
    })
    expect(findButton(wrapper, 'Save Draft').attributes('disabled')).toBeDefined()
    expect(findButton(wrapper, 'Submit for Review').attributes('disabled')).toBeDefined()
  })

  it('emits cancel from the Cancel button', async () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene } })
    await findButton(wrapper, 'Cancel').trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('derives the header disease and mode of inheritance from the precuration', () => {
    wrapper = mount(ClinGenCurationForm, {
      props: {
        gene,
        precurationData: {
          disease_name: 'Renal cysts',
          mondo_id: 'MONDO:0000001',
          entity_definition: { mode_of_inheritance: 'Autosomal dominant' }
        }
      }
    })
    expect(wrapper.text()).toContain('Renal cysts')
    expect(wrapper.text()).toContain('AD')
  })
})
