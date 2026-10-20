import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { EvidenceRecord } from '@/stores/evidence'
import { setActivePinia, createPinia } from 'pinia'
import { useEvidenceStore } from '@/stores/evidence'
import { evidenceAPI } from '@/api/evidence'

vi.mock('@/api/evidence', () => ({
  evidenceAPI: {
    getEvidenceItems: vi.fn(),
    createEvidenceItem: vi.fn(),
    updateEvidenceItem: vi.fn(),
    deleteEvidenceItem: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(evidenceAPI)

const item = (id: string, extra: Record<string, unknown> = {}) =>
  ({
    id,
    curation_id: 'c1',
    evidence_category: 'case',
    evidence_type: 'genetic',
    created_at: '2024-01-01T00:00:00Z',
    ...extra
  }) as EvidenceRecord

describe('useEvidenceStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('lists evidence for a curation newest first', () => {
      const store = useEvidenceStore()
      store.evidence = new Map([
        ['e1', item('e1', { created_at: '2024-01-01T00:00:00Z' })],
        ['e2', item('e2', { created_at: '2024-03-01T00:00:00Z' })],
        ['e3', item('e3', { curation_id: 'other' })]
      ])

      expect(store.getEvidenceByCuration('c1').map(e => e.id)).toEqual(['e2', 'e1'])
      expect(store.getEvidenceByCuration('none')).toEqual([])
    })

    it('filters by category and counts by evidence type', () => {
      const store = useEvidenceStore()
      store.evidence = new Map([
        ['e1', item('e1')],
        ['e2', item('e2', { evidence_category: 'control', evidence_type: 'experimental' })],
        ['e3', item('e3', { evidence_type: 'experimental' })]
      ])

      expect(store.getEvidenceByCategory('c1', 'control').map(e => e.id)).toEqual(['e2'])
      expect(store.geneticEvidenceCount('c1')).toBe(1)
      expect(store.experimentalEvidenceCount('c1')).toBe(2)
      expect(store.experimentalEvidenceCount('other')).toBe(0)
    })
  })

  describe('fetchEvidenceForCuration', () => {
    it('stores fetched items keyed by id', async () => {
      const store = useEvidenceStore()
      api.getEvidenceItems.mockResolvedValue([item('e1'), item('e2')])

      const items = await store.fetchEvidenceForCuration('c1')

      expect(api.getEvidenceItems).toHaveBeenCalledWith('c1')
      expect(items).toHaveLength(2)
      expect(store.evidence.size).toBe(2)
      expect(store.loading).toBe(false)
    })

    it('records the error and rethrows', async () => {
      const store = useEvidenceStore()
      api.getEvidenceItems.mockRejectedValue(new Error('down'))

      await expect(store.fetchEvidenceForCuration('c1')).rejects.toThrow('down')
      expect(store.error).toBe('down')
      expect(store.loading).toBe(false)
    })

    it('uses a fallback message when the error has none', async () => {
      const store = useEvidenceStore()
      api.getEvidenceItems.mockRejectedValue({})

      await expect(store.fetchEvidenceForCuration('c1')).rejects.toEqual({})
      expect(store.error).toBe('Failed to fetch evidence')
    })
  })

  describe('createEvidence / updateEvidence / deleteEvidence', () => {
    it('createEvidence stores the created item', async () => {
      const store = useEvidenceStore()
      api.createEvidenceItem.mockResolvedValue(item('new'))

      await expect(store.createEvidence('c1', {} as never)).resolves.toEqual(item('new'))
      expect(store.evidence.get('new')).toEqual(item('new'))
    })

    it('createEvidence records errors and uses a fallback message', async () => {
      const store = useEvidenceStore()
      api.createEvidenceItem.mockRejectedValue(new Error('invalid'))

      await expect(store.createEvidence('c1', {} as never)).rejects.toThrow('invalid')
      expect(store.error).toBe('invalid')

      api.createEvidenceItem.mockRejectedValue({})
      await expect(store.createEvidence('c1', {} as never)).rejects.toEqual({})
      expect(store.error).toBe('Failed to create evidence')
    })

    it('updateEvidence replaces the stored item', async () => {
      const store = useEvidenceStore()
      store.evidence.set('e1', item('e1'))
      api.updateEvidenceItem.mockResolvedValue(item('e1', { evidence_type: 'experimental' }))

      await store.updateEvidence('c1', 'e1', {} as never)

      expect(store.evidence.get('e1')).toMatchObject({ evidence_type: 'experimental' })
    })

    it('updateEvidence records errors and uses a fallback message', async () => {
      const store = useEvidenceStore()
      api.updateEvidenceItem.mockRejectedValue(new Error('locked'))

      await expect(store.updateEvidence('c1', 'e1', {} as never)).rejects.toThrow('locked')
      expect(store.error).toBe('locked')

      api.updateEvidenceItem.mockRejectedValue({})
      await expect(store.updateEvidence('c1', 'e1', {} as never)).rejects.toEqual({})
      expect(store.error).toBe('Failed to update evidence')
    })

    it('deleteEvidence removes the item', async () => {
      const store = useEvidenceStore()
      store.evidence.set('e1', item('e1'))
      api.deleteEvidenceItem.mockResolvedValue({} as never)

      await store.deleteEvidence('c1', 'e1')

      expect(api.deleteEvidenceItem).toHaveBeenCalledWith('c1', 'e1')
      expect(store.evidence.has('e1')).toBe(false)
    })

    it('deleteEvidence records errors and uses a fallback message', async () => {
      const store = useEvidenceStore()
      store.evidence.set('e1', item('e1'))
      api.deleteEvidenceItem.mockRejectedValue(new Error('denied'))

      await expect(store.deleteEvidence('c1', 'e1')).rejects.toThrow('denied')
      expect(store.evidence.has('e1')).toBe(true)
      expect(store.error).toBe('denied')

      api.deleteEvidenceItem.mockRejectedValue({})
      await expect(store.deleteEvidence('c1', 'e1')).rejects.toEqual({})
      expect(store.error).toBe('Failed to delete evidence')
    })
  })

  describe('clearing', () => {
    it('clearEvidence empties the map and error; clearError resets only the error', () => {
      const store = useEvidenceStore()
      store.evidence.set('e1', item('e1'))
      store.error = 'x'

      store.clearError()
      expect(store.error).toBeNull()
      expect(store.evidence.size).toBe(1)

      store.clearEvidence()
      expect(store.evidence.size).toBe(0)
    })
  })
})
