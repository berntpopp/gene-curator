import { afterEach, describe, expect, it, vi } from 'vitest'
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
    expect(findButton(wrapper, 'Submit for review').attributes('disabled')).toBeDefined()
  })

  it('scores legacy {points} dict evidence from initialData', async () => {
    const legacy = {
      experimental_evidence: { models: { non_human_model_organism: { points: 0.5 } } }
    }
    wrapper = mount(ClinGenCurationForm, { props: { gene, initialData: legacy as never } })
    await flushPromises()
    expect(wrapper.findComponent(ScoreSummary).props('totalScore')).toBeCloseTo(0.5)
  })

  it('scores initial genetic evidence and enables submit', async () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene, initialData: withCaseLevel } })
    await flushPromises()
    const score = wrapper.findComponent(ScoreSummary)
    expect(score.props('totalScore')).toBeCloseTo(1.5)
    expect(score.props('classification')).toBe('Limited')
    expect(findButton(wrapper, 'Submit for review').attributes('disabled')).toBeUndefined()
  })

  describe('replication over time', () => {
    const strong: Partial<ClinGenEvidenceData> = {
      genetic_evidence: {
        case_level: {
          autosomal_dominant_or_x_linked: {
            predicted_or_proven_null: [{ proband_counted_points: 12 }],
            other_variant_type: []
          }
        }
      }
    }

    it('classifies Strong as Definitive when replicated, and stays Strong otherwise', async () => {
      wrapper = mount(ClinGenCurationForm, { props: { gene, initialData: strong } })
      await flushPromises()
      expect(wrapper.findComponent(ScoreSummary).props('classification')).toBe('Strong')

      await wrapper.setProps({ initialData: { ...strong, replicated_over_time: true } })
      await flushPromises()
      expect(wrapper.findComponent(ScoreSummary).props('classification')).toBe('Definitive')
    })

    it('stays Disputed with contradictory evidence even when replicated', async () => {
      wrapper = mount(ClinGenCurationForm, {
        props: {
          gene,
          initialData: {
            ...strong,
            replicated_over_time: true,
            contradictory_evidence: [{ label: 'Lab study' }]
          }
        }
      })
      await flushPromises()
      expect(wrapper.findComponent(ScoreSummary).props('classification')).toBe('Disputed')
    })

    it('stores the toggle in the emitted data and is disabled when read-only', async () => {
      wrapper = mount(ClinGenCurationForm, { props: { gene } })
      wrapper.findComponent({ name: 'VCheckbox' }).vm.$emit('update:modelValue', true)
      await flushPromises()
      const emitted = wrapper.emitted('update:model-value')?.[0]?.[0] as ClinGenEvidenceData
      expect(emitted.replicated_over_time).toBe(true)

      wrapper.unmount()
      wrapper = mount(ClinGenCurationForm, { props: { gene, readonly: true } })
      expect(wrapper.findComponent({ name: 'VCheckbox' }).props('disabled')).toBe(true)
    })
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
    await findButton(wrapper, 'Save draft').trigger('click')
    const emitted = wrapper.emitted('save-draft')?.[0]?.[0] as ClinGenEvidenceData
    expect(
      emitted.genetic_evidence.case_level?.autosomal_dominant_or_x_linked?.predicted_or_proven_null
    ).toEqual([{ proband_counted_points: 1.5 }])
  })

  it('asks for confirmation before emitting submit, also via Ctrl+Enter', async () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene }, attachTo: document.body })
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }))
    await flushPromises()
    expect(document.body.textContent).not.toContain('Submit this curation')

    await wrapper.setProps({ initialData: withCaseLevel })
    await flushPromises()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }))
    await flushPromises()
    expect(wrapper.emitted('submit')).toBeUndefined()
    expect(document.body.textContent).toContain('Submit this curation')

    const confirm = [...document.body.querySelectorAll('button')].find(
      b => b.textContent?.trim() === 'Submit'
    )
    confirm?.click()
    await flushPromises()
    expect(wrapper.emitted('submit')).toHaveLength(1)
  })

  it('explains why Submit for Review is disabled', () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene } })
    expect(wrapper.text()).toContain('Add at least one scored evidence item')
  })

  it('shows parent-driven saving state and the saved time instead of local flags', async () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene, saving: true, lastSaved: Date.now() } })
    expect(findButton(wrapper, 'Save draft').classes()).toContain('v-btn--loading')
    expect(wrapper.text()).toContain('Saved ')
  })

  it('does not advertise undo or quick actions', () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene } })
    expect(wrapper.text()).not.toContain('Undo')
    expect(wrapper.text()).not.toContain('Quick actions')
  })

  it('saves a draft on Ctrl+S and prevents the browser default', async () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene } })
    const event = new KeyboardEvent('keydown', { key: 's', ctrlKey: true, cancelable: true })
    document.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
    expect(wrapper.emitted('save-draft')).toHaveLength(1)
  })

  it('blurs the focused cell before saving so its last edit is committed', () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene } })
    const input = document.createElement('input')
    document.body.appendChild(input)
    input.focus()
    const blur = vi.spyOn(input, 'blur')
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true }))
    expect(blur).toHaveBeenCalled()
    input.remove()
  })

  it('ignores Ctrl+S and Ctrl+Enter when read-only', () => {
    wrapper = mount(ClinGenCurationForm, {
      props: { gene, readonly: true, initialData: withCaseLevel }
    })
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 's', ctrlKey: true }))
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', ctrlKey: true }))
    expect(wrapper.emitted('save-draft')).toBeUndefined()
    expect(wrapper.emitted('submit')).toBeUndefined()
  })

  it('disables saving and submitting in read-only mode', () => {
    wrapper = mount(ClinGenCurationForm, {
      props: { gene, readonly: true, initialData: withCaseLevel }
    })
    expect(findButton(wrapper, 'Save draft').attributes('disabled')).toBeDefined()
    expect(findButton(wrapper, 'Submit for review').attributes('disabled')).toBeDefined()
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

  it('does not flip to Disputed for an empty contradictory row', () => {
    const blank = { ...withCaseLevel, contradictory_evidence: [{ pmid: '', description: ' ' }] }
    wrapper = mount(ClinGenCurationForm, { props: { gene, initialData: blank } })
    expect(wrapper.findComponent(ScoreSummary).props('classification')).not.toBe('Disputed')

    const filled = { ...withCaseLevel, contradictory_evidence: [{ pmid: '12345678' }] }
    const other = mount(ClinGenCurationForm, { props: { gene, initialData: filled } })
    expect(other.findComponent(ScoreSummary).props('classification')).toBe('Disputed')
    other.unmount()
  })

  it('lets the action bar wrap on narrow screens', () => {
    wrapper = mount(ClinGenCurationForm, { props: { gene } })
    const bar = findButton(wrapper, 'Submit for review').element.parentElement
    expect(bar?.classList.contains('flex-wrap')).toBe(true)
  })
})
