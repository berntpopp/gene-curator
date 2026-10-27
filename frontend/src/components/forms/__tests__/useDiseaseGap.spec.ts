import { describe, it, expect, vi, beforeEach } from 'vitest'
import { nextTick, ref } from 'vue'
import { flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { diseaseGapMessage, useDiseaseGap } from '../useDiseaseGap'
import { useWorkflowStore } from '@/stores/workflow'

describe('diseaseGapMessage (#453)', () => {
  it('ignores gaps the form can fix itself', () => {
    expect(diseaseGapMessage(['summary', 'genetic_evidence.case_level'], true)).toBeNull()
  })

  it('names the missing disease fields and says why the form cannot fix them', () => {
    const none = diseaseGapMessage(
      ['entity_definition.disease_name', 'entity_definition.mondo_id', 'summary'],
      false
    )!
    expect(none).toContain('Disease name, MONDO ID')
    expect(none).toContain('no linked precuration')
    expect(none).toContain('scope admin')
    expect(diseaseGapMessage(['mode_of_inheritance'], true)).toContain(
      'linked precuration does not supply'
    )
  })
})

describe('useDiseaseGap', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('asks the server check after load and every save and reports the gap', async () => {
    const validate = vi
      .spyOn(useWorkflowStore(), 'validateTransition')
      .mockResolvedValueOnce({ missing_fields: ['entity_definition.disease_name'] } as never)
      .mockResolvedValueOnce({ missing_fields: [] } as never)
    const savedAt = ref<number | null>(null)
    const report = vi.fn()
    useDiseaseGap({ curationId: () => 'c1', linked: () => false, checkAt: savedAt, report })
    await flushPromises()
    expect(validate).toHaveBeenCalledWith('curation', 'c1', 'review')
    expect(report).toHaveBeenLastCalledWith(expect.stringContaining('Disease name'))
    savedAt.value = 1
    await nextTick()
    await flushPromises()
    expect(report).toHaveBeenLastCalledWith(null)
  })

  it('checks nothing for a new curation and stays quiet when the check fails', async () => {
    const validate = vi.spyOn(useWorkflowStore(), 'validateTransition')
    const report = vi.fn()
    useDiseaseGap({ curationId: () => undefined, linked: () => true, checkAt: ref(0), report })
    await flushPromises()
    expect(validate).not.toHaveBeenCalled()
    validate.mockRejectedValueOnce(new Error('offline'))
    useDiseaseGap({ curationId: () => 'c1', linked: () => true, checkAt: ref(0), report })
    await flushPromises()
    expect(report).not.toHaveBeenCalled()
  })
})
