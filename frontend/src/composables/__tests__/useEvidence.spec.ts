import { describe, it, expect, vi, beforeEach } from 'vitest'

const items = [
  { id: 'e1', evidence_type: 'genetic', evidence_category: 'case_level', computed_score: 3 },
  { id: 'e2', evidence_type: 'genetic', evidence_category: 'segregation', computed_score: 2 },
  { id: 'e3', evidence_type: 'experimental', evidence_category: 'models', computed_score: null }
]

const store = vi.hoisted(() => ({
  getEvidenceByCuration: vi.fn(),
  fetchEvidenceForCuration: vi.fn(),
  createEvidence: vi.fn(),
  updateEvidence: vi.fn(),
  deleteEvidence: vi.fn()
}))

vi.mock('@/stores/evidence', () => ({
  useEvidenceStore: () => store
}))

import { useEvidence } from '../useEvidence'

describe('useEvidence', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    store.getEvidenceByCuration.mockReturnValue(items)
  })

  it('derives filtered lists, total score and category grouping from the store', () => {
    const { evidenceItems, geneticEvidence, experimentalEvidence, totalScore, evidenceByCategory } =
      useEvidence('cur-1')

    expect(evidenceItems.value).toHaveLength(3)
    expect(store.getEvidenceByCuration).toHaveBeenCalledWith('cur-1')
    expect(geneticEvidence.value.map(i => i.id)).toEqual(['e1', 'e2'])
    expect(experimentalEvidence.value.map(i => i.id)).toEqual(['e3'])
    expect(totalScore.value).toBe(5)
    expect(Object.keys(evidenceByCategory.value).sort()).toEqual([
      'case_level',
      'models',
      'segregation'
    ])
    expect(evidenceByCategory.value.models?.[0]?.id).toBe('e3')
  })

  it('fetchEvidence loads data and toggles loading', async () => {
    store.fetchEvidenceForCuration.mockResolvedValue(undefined)
    const { fetchEvidence, loading, error } = useEvidence('cur-1')

    const pending = fetchEvidence()
    expect(loading.value).toBe(true)
    await pending

    expect(store.fetchEvidenceForCuration).toHaveBeenCalledWith('cur-1')
    expect(loading.value).toBe(false)
    expect(error.value).toBeNull()
  })

  it('fetchEvidence stores a fallback message on failure without throwing', async () => {
    store.fetchEvidenceForCuration.mockRejectedValue('nope')
    const { fetchEvidence, error, loading } = useEvidence('cur-1')

    await fetchEvidence()

    expect(error.value).toBe('Failed to fetch evidence')
    expect(loading.value).toBe(false)
  })

  it('addEvidence passes data through and rethrows errors', async () => {
    const { addEvidence, error } = useEvidence('cur-1')

    await addEvidence({ evidence_type: 'genetic' })
    expect(store.createEvidence).toHaveBeenCalledWith('cur-1', { evidence_type: 'genetic' })

    store.createEvidence.mockRejectedValueOnce(new Error('invalid'))
    await expect(addEvidence({})).rejects.toThrow('invalid')
    expect(error.value).toBe('invalid')
  })

  it('updateEvidence passes id and data through and rethrows errors', async () => {
    const { updateEvidence, error } = useEvidence('cur-1')

    await updateEvidence('e1', { computed_score: 4 })
    expect(store.updateEvidence).toHaveBeenCalledWith('cur-1', 'e1', { computed_score: 4 })

    store.updateEvidence.mockRejectedValueOnce(new Error('conflict'))
    await expect(updateEvidence('e1', {})).rejects.toThrow('conflict')
    expect(error.value).toBe('conflict')
  })

  it('removeEvidence deletes by id and uses fallback message on non-Error failure', async () => {
    const { removeEvidence, error } = useEvidence('cur-1')

    await removeEvidence('e2')
    expect(store.deleteEvidence).toHaveBeenCalledWith('cur-1', 'e2')

    store.deleteEvidence.mockRejectedValueOnce('bad')
    await expect(removeEvidence('e2')).rejects.toBe('bad')
    expect(error.value).toBe('Failed to delete evidence')
  })
})
