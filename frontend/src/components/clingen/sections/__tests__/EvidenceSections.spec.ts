import { describe, expect, it } from 'vitest'
import { mount, type DOMWrapper, type VueWrapper } from '@vue/test-utils'
import GeneticEvidenceSection from '../GeneticEvidenceSection.vue'
import ExperimentalEvidenceSection from '../ExperimentalEvidenceSection.vue'
import ContradictoryEvidenceSection from '../ContradictoryEvidenceSection.vue'
import EvidenceDataTable from '../../EvidenceDataTable.vue'
import { createEmptyExperimentalEvidence, createEmptyGeneticEvidence } from '../../evidenceDefaults'
import type { EvidenceItem, GeneticEvidence } from '../../types'

function buttonWithText(
  wrapper: { findAll(selector: string): DOMWrapper<Element>[] },
  text: string
) {
  const button = wrapper.findAll('button').find(b => b.text().includes(text))
  if (!button) throw new Error(`no button with text "${text}"`)
  return button
}

// Expands every panel, then drives add, update and remove for every subsection table.
async function exerciseAllSubsections(wrapper: VueWrapper) {
  for (const title of wrapper.findAll('.v-expansion-panel-title')) await title.trigger('click')
  const adds = wrapper.findAll('button').filter(b => b.text().includes('Add'))
  for (const add of adds) await add.trigger('click')
  const tables = wrapper.findAllComponents(EvidenceDataTable)
  for (const table of tables) {
    table.vm.$emit('update:items', [{ points: 1 }])
    table.vm.$emit('remove', 0)
  }
  return { adds: adds.length, tables: tables.length }
}

describe('GeneticEvidenceSection', () => {
  it('shows per-category score chips with the SOP caps applied to segregation and case-control', () => {
    const value: GeneticEvidence = {
      ...createEmptyGeneticEvidence(),
      case_level: {
        autosomal_dominant_or_x_linked: {
          predicted_or_proven_null: [{ proband_counted_points: 1.5 }],
          other_variant_type: [{ proband_counted_points: 0.1 }]
        }
      },
      segregation: [{ points: 2 }, { points: 2 }],
      case_control: {
        single_variant_analysis: [{ points: 4 }],
        aggregate_variant_analysis: [{ points: 3 }]
      }
    }
    const wrapper = mount(GeneticEvidenceSection, { props: { modelValue: value } })
    expect(wrapper.text()).toContain('1.60 pts')
    expect(wrapper.text()).toContain('3.00 pts (max 3)')
    // Case-control uses the larger of single-variant and aggregate totals, capped at 6.
    expect(wrapper.text()).toContain('4.00 pts (max 6)')
  })

  it('emits a new object with only the addressed path changed when a table updates', () => {
    const value: GeneticEvidence = createEmptyGeneticEvidence()
    value.case_level = {
      autosomal_dominant_or_x_linked: {
        predicted_or_proven_null: [{ variant: 'c.1A>T', points: 1 }]
      }
    }
    const wrapper = mount(GeneticEvidenceSection, { props: { modelValue: value } })

    const nullTable = wrapper
      .findAllComponents(EvidenceDataTable)
      .find(t => t.props('evidenceType') === 'null_variant')
    nullTable?.vm.$emit('update:items', [{ variant: 'c.2A>T', proband_counted_points: 1.5 }])

    const emitted = wrapper.emitted('update:model-value')?.[0]?.[0] as GeneticEvidence
    expect(emitted.case_level?.autosomal_dominant_or_x_linked?.predicted_or_proven_null).toEqual([
      { variant: 'c.2A>T', proband_counted_points: 1.5 }
    ])
    expect(emitted.case_level?.autosomal_dominant_or_x_linked?.other_variant_type).toBeUndefined()
    expect(emitted.segregation).toEqual([])
    // The prop value itself must not be mutated.
    expect(value.case_level?.autosomal_dominant_or_x_linked?.predicted_or_proven_null).toEqual([
      { variant: 'c.1A>T', points: 1 }
    ])
  })

  it('appends a default row with the SOP default points when "Add Evidence" is clicked', async () => {
    const wrapper = mount(GeneticEvidenceSection, {
      props: { modelValue: createEmptyGeneticEvidence() }
    })
    await buttonWithText(wrapper, 'Add Evidence').trigger('click')

    const emitted = wrapper.emitted('update:model-value')?.[0]?.[0] as GeneticEvidence
    const rows = emitted.case_level?.autosomal_dominant_or_x_linked?.predicted_or_proven_null
    expect(rows).toHaveLength(1)
    expect(rows?.[0]).toMatchObject({
      variant_type: 'nonsense',
      proband_counted_points: 1.5,
      score_status: 'score'
    })
  })

  it('removes a row through the table remove event', () => {
    const value: GeneticEvidence = createEmptyGeneticEvidence()
    value.case_level = {
      autosomal_dominant_or_x_linked: {
        predicted_or_proven_null: [{ variant: 'a' }, { variant: 'b' }]
      }
    }
    const wrapper = mount(GeneticEvidenceSection, { props: { modelValue: value } })
    const nullTable = wrapper
      .findAllComponents(EvidenceDataTable)
      .find(t => t.props('evidenceType') === 'null_variant')
    nullTable?.vm.$emit('remove', 0)

    const emitted = wrapper.emitted('update:model-value')?.[0]?.[0] as GeneticEvidence
    expect(emitted.case_level?.autosomal_dominant_or_x_linked?.predicted_or_proven_null).toEqual([
      { variant: 'b' }
    ])
  })

  it('drives add, update and remove for every genetic subsection', async () => {
    const wrapper = mount(GeneticEvidenceSection, {
      props: { modelValue: createEmptyGeneticEvidence() }
    })
    const { adds, tables } = await exerciseAllSubsections(wrapper)
    expect(tables).toBeGreaterThan(0)
    expect(wrapper.emitted('update:model-value')).toHaveLength(adds + tables * 2)
  })
})

describe('ExperimentalEvidenceSection', () => {
  it('caps function and rescue scores at their SOP maxima', () => {
    const value = createEmptyExperimentalEvidence()
    value.function = {
      biochemical_function: [{ points: 1.5 }],
      protein_interaction: [{ points: 1.5 }],
      expression: [{ points: 1 }]
    }
    value.rescue = { human: [{ points: 3 }], patient_cells: [{ points: 3 }] }
    const wrapper = mount(ExperimentalEvidenceSection, { props: { modelValue: value } })
    expect(wrapper.text()).toContain('2.00 pts (max 2)')
    expect(wrapper.text()).toContain('4.00 pts (max 4)')
  })

  it('adds a default biochemical-function row with 0.5 points', async () => {
    const wrapper = mount(ExperimentalEvidenceSection, {
      props: { modelValue: createEmptyExperimentalEvidence() }
    })
    const addButton = wrapper.findAll('button').find(b => b.text().includes('Add Evidence'))
    await addButton?.trigger('click')

    const emitted = wrapper.emitted('update:model-value')?.[0]?.[0] as {
      function: { biochemical_function: EvidenceItem[] }
    }
    expect(emitted.function.biochemical_function).toEqual([
      expect.objectContaining({ points: 0.5, score_status: 'score' })
    ])
  })

  it('creates missing parent objects when emitting an update for an absent section', async () => {
    const wrapper = mount(ExperimentalEvidenceSection, { props: { modelValue: {} } })
    const tables = wrapper.findAllComponents(EvidenceDataTable)
    tables[0]?.vm.$emit('update:items', [{ points: 0.5 }])

    const emitted = wrapper.emitted('update:model-value')?.[0]?.[0] as {
      function: { biochemical_function: EvidenceItem[] }
    }
    expect(emitted.function.biochemical_function).toEqual([{ points: 0.5 }])
  })

  it('drives add, update and remove for every experimental subsection', async () => {
    const wrapper = mount(ExperimentalEvidenceSection, {
      props: { modelValue: createEmptyExperimentalEvidence() }
    })
    const { adds, tables } = await exerciseAllSubsections(wrapper)
    expect(tables).toBeGreaterThan(0)
    expect(wrapper.emitted('update:model-value')).toHaveLength(adds + tables * 2)
  })
})

describe('ContradictoryEvidenceSection', () => {
  it('shows the empty-state prompt and no table until an item is added', () => {
    const wrapper = mount(ContradictoryEvidenceSection, { props: { modelValue: [] } })
    expect(wrapper.text()).toContain('No Contradictory Evidence')
    expect(wrapper.find('table').exists()).toBe(false)
  })

  it('adds a default contradictory item, updates a field and removes a row', async () => {
    const wrapper = mount(ContradictoryEvidenceSection, { props: { modelValue: [] } })
    await buttonWithText(wrapper, 'Add contradictory evidence').trigger('click')
    const added = wrapper.emitted('update:model-value')?.[0]?.[0] as EvidenceItem[]
    expect(added).toEqual([
      expect.objectContaining({ evidence_type: 'population', impact: 'note' })
    ])

    const withRow = mount(ContradictoryEvidenceSection, { props: { modelValue: added } })
    expect(withRow.text()).toContain('Classification Impact')
    withRow.findAllComponents({ name: 'VTextField' })[0]?.vm.$emit('update:modelValue', 'Lab study')
    const updated = withRow.emitted('update:model-value')?.[0]?.[0] as EvidenceItem[]
    expect(updated[0]).toMatchObject({ label: 'Lab study', evidence_type: 'population' })

    const buttons = withRow.findAll('button')
    await buttons[buttons.length - 1]?.trigger('click')
    const removed = withRow.emitted('update:model-value')?.at(-1)?.[0] as EvidenceItem[]
    expect(removed).toEqual([])
  })
})
