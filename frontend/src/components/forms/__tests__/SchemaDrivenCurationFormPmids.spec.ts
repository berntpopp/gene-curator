import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SchemaDrivenCurationForm from '../SchemaDrivenCurationForm.vue'
import { WORKSPACE_FRAME, createWorkspaceFrame } from '@/components/workspace/useWorkspaceFrame'

// #267: a draft reloaded on the Summary tab never mounted the evidence tables, so an unknown
// PMID saved in a case-level row did not block Submit.
const api = vi.hoisted(() => ({ validatePMIDs: vi.fn() }))
const curations = vi.hoisted(() => ({ currentCuration: null, fetchCurationById: vi.fn() }))
vi.mock('@/api/publications', () => ({ publicationsAPI: api }))
vi.mock('@/stores/curations', () => ({ useCurationsStore: () => curations }))
vi.mock('@/stores/precurations', () => ({ usePrecurationsStore: () => ({}) }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast: vi.fn() }) }))
vi.mock('@/stores/schemas', () => ({
  useSchemasStore: () => ({
    getSchemaById: (id: string) => ({ id }),
    fetchSchemaById: vi.fn(),
    fetchPinnedVersion: vi.fn().mockResolvedValue({ id: 'v1', snapshot: {} })
  })
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }))
vi.mock('@/composables/useHistory', () => ({
  useHistory: () => ({ canUndo: ref(false), canRedo: ref(false), recordAction: vi.fn() })
}))

const unknown = (pmid: string) => ({
  pmid,
  is_valid: false,
  error: `Publication not found: ${pmid}`
})

describe('SchemaDrivenCurationForm PMID check on load', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
  })

  it('blocks Submit for an unknown PMID in any table, without opening it', async () => {
    curations.fetchCurationById.mockResolvedValue({
      status: 'draft',
      lock_version: 1,
      evidence_data: {
        evidence_summary: 'x',
        genetic_evidence: { case_level: { ad: { other: [{ pmid: 'PMID: 99999999' }] } } },
        experimental_evidence: { function: [{ pmid: '31000001' }, { pmid: '' }] }
      }
    })
    api.validatePMIDs.mockResolvedValue({
      results: [unknown('99999999'), { pmid: '31000001', is_valid: true, publication: null }]
    })
    const frame = createWorkspaceFrame()
    mount(SchemaDrivenCurationForm, {
      props: { schemaId: 's', scopeId: 'sc', curationId: 'c' },
      global: {
        stubs: { DynamicForm: true, FormRecoveryDialog: true, ErrorBoundary: true },
        provide: { [WORKSPACE_FRAME as symbol]: frame }
      }
    })
    await flushPromises()

    expect(api.validatePMIDs).toHaveBeenCalledTimes(1)
    expect(api.validatePMIDs.mock.calls[0]![0]).toEqual(['99999999', '31000001'])
    expect(frame.canSubmit.value).toBe(false)
    expect(frame.blockers.value).toEqual([
      'Fix 1 unknown PMID before submitting: PMID 99999999 not found in Europe PMC'
    ])
  })
})
