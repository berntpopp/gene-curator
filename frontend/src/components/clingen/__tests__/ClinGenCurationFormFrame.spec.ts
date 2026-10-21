import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import ClinGenCurationForm from '../ClinGenCurationForm.vue'
import { WORKSPACE_FRAME, createWorkspaceFrame } from '@/components/workspace/useWorkspaceFrame'
import type { ClinGenEvidenceData } from '../types'

const gene = { symbol: 'COL4A5', approved_symbol: 'COL4A5' }
const strong: Partial<ClinGenEvidenceData> = {
  genetic_evidence: {
    case_level: {
      autosomal_dominant_or_x_linked: {
        predicted_or_proven_null: [{ pmid: '1', proband_counted_points: 7.5 }],
        other_variant_type: []
      }
    }
  }
}
const precurationData = {
  disease_name: 'Alport syndrome',
  mode_of_inheritance: 'X-linked'
}

describe('ClinGenCurationForm inside the workspace frame', () => {
  let wrapper: VueWrapper | undefined
  afterEach(() => wrapper?.unmount())

  function mountFramed(props: Record<string, unknown> = {}) {
    const frame = createWorkspaceFrame()
    wrapper = mount(ClinGenCurationForm, {
      props: { gene, initialData: strong, precurationData, ...props },
      global: { provide: { [WORKSPACE_FRAME as symbol]: frame } }
    })
    return frame
  }

  it('publishes the live score and entity details to the frame', async () => {
    const frame = mountFramed()
    await flushPromises()
    expect(frame.score.value?.total).toBeCloseTo(7.5)
    expect(frame.score.value?.classification).toBe('Moderate')
    expect(frame.score.value?.geneticBreakdown?.caseLevel).toBeCloseTo(7.5)
    expect(frame.meta.value).toEqual({ disease: 'Alport syndrome', moi: 'X-linked' })
  })

  it('lets the frame submit (opens the confirmation) only when submitting is allowed', async () => {
    const frame = mountFramed()
    await flushPromises()
    expect(frame.canSubmit.value).toBe(true)
    expect(frame.submit()).toBe(true)
    await flushPromises()
    expect(document.body.textContent).toContain('Submit this curation')
    wrapper?.unmount()
    const empty = mountFramed({ initialData: {} })
    await flushPromises()
    expect(empty.canSubmit.value).toBe(false)
  })

  it('does not repeat what the frame shows: no own header, score sidebar or action bar', async () => {
    mountFramed()
    await flushPromises()
    expect(wrapper!.find('.curation-header').exists()).toBe(false)
    expect(wrapper!.find('.score-summary').exists()).toBe(false)
    expect(wrapper!.text()).not.toContain('Save draft')
  })

  it('leaves Ctrl+S to the frame but keeps Ctrl+Enter', async () => {
    mountFramed()
    await flushPromises()
    const save = new KeyboardEvent('keydown', { key: 's', ctrlKey: true, cancelable: true })
    document.dispatchEvent(save)
    expect(save.defaultPrevented).toBe(false)
    expect(wrapper!.emitted('save-draft')).toBeUndefined()
  })
})

describe('ClinGenCurationForm tab bar (#245)', () => {
  it('uses short labels and scroll arrows so all tabs fit', () => {
    const w = mount(ClinGenCurationForm, { props: { gene } })
    const labels = w.findAll('.v-tab').map(t =>
      t
        .text()
        .replace(/\d+\.\d+/, '')
        .trim()
    )
    expect(labels).toEqual(['Summary', 'Genetic', 'Experimental', 'Contradictory', 'Lumping'])
    expect(w.findComponent({ name: 'VTabs' }).props('showArrows')).toBe(true)
    w.unmount()
  })
})
