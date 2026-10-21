import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import type { PrecurationRecord, PrecurationDetail } from '@/stores/precurations'
import type { Schema } from '@/types/api'
import { usePrecurationsStore } from '@/stores/precurations'
import { precurationsAPI } from '@/api/precurations'
import { logService } from '@/services/logService'

vi.mock('@/api/precurations', () => ({
  precurationsAPI: {
    getPrecurations: vi.fn(),
    getPrecuration: vi.fn(),
    createPrecuration: vi.fn(),
    updatePrecuration: vi.fn(),
    saveDraft: vi.fn(),
    submitPrecuration: vi.fn(),
    approvePrecuration: vi.fn(),
    rejectPrecuration: vi.fn(),
    deletePrecuration: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(precurationsAPI)

const row = (id: string, extra: Partial<PrecurationRecord> = {}): PrecurationRecord =>
  ({
    id,
    gene_id: 'g1',
    scope_id: 's1',
    status: 'draft',
    ...extra
  }) as PrecurationRecord

const full = (id: string, extra: Partial<PrecurationDetail> = {}): PrecurationDetail =>
  ({ ...row(id), ...extra }) as PrecurationDetail

const newPrecuration: Schema<'PrecurationCreate'> = {
  gene_id: 'g1',
  scope_id: 's1',
  precuration_schema_id: 'ps1'
}

const httpError = (message: string) => new Error(message)

const approval: Schema<'PrecurationApprovalResult'> = {
  precuration_id: 'p1',
  approved: true,
  curation_created: true,
  curation_id: 'c1',
  message: 'ok'
}

describe('usePrecurationsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('filters by id, scope, gene and status', () => {
      const store = usePrecurationsStore()
      store.precurations = [
        row('p1'),
        row('p2', { scope_id: 's2', gene_id: 'g2', status: 'submitted' }),
        row('p3', { status: 'approved' })
      ]

      expect(store.getPrecurationById('p2')?.id).toBe('p2')
      expect(store.getPrecurationById('nope')).toBeUndefined()
      expect(store.getPrecurationsByScope('s2').map(p => p.id)).toEqual(['p2'])
      expect(store.getPrecurationsByGene('g1').map(p => p.id)).toEqual(['p1', 'p3'])
      expect(store.draftPrecurations.map(p => p.id)).toEqual(['p1'])
      expect(store.submittedPrecurations.map(p => p.id)).toEqual(['p2'])
      expect(store.approvedPrecurations.map(p => p.id)).toEqual(['p3'])
      expect(store.hasError).toBe(false)
    })
  })

  describe('fetchPrecurations', () => {
    it('sends merged filters and paging and stores the list', async () => {
      const store = usePrecurationsStore()
      store.filters.gene_id = 'g1'
      store.pagination.page = 3
      api.getPrecurations.mockResolvedValue({
        precurations: [row('p1')],
        total: 101,
        skip: 100,
        limit: 50
      })

      const result = await store.fetchPrecurations({ status: 'draft' })

      expect(api.getPrecurations).toHaveBeenCalledWith({
        scope_id: null,
        gene_id: 'g1',
        precuration_status: 'draft',
        skip: 100,
        limit: 50
      })
      expect(result.total).toBe(101)
      expect(store.pagination.total).toBe(101)
      expect(store.pagination.pages).toBe(3)
    })

    it('records errors', async () => {
      const store = usePrecurationsStore()
      api.getPrecurations.mockRejectedValueOnce(new Error('down'))
      await expect(store.fetchPrecurations()).rejects.toThrow('down')
      expect(store.error).toEqual({ message: 'down' })
    })
  })

  describe('fetchPrecurationById', () => {
    it('sets current and refreshes the list entry', async () => {
      const store = usePrecurationsStore()
      store.precurations = [row('p1')]
      api.getPrecuration.mockResolvedValue(full('p1', { status: 'submitted' }))

      await store.fetchPrecurationById('p1')

      expect(store.currentPrecuration?.id).toBe('p1')
      expect(store.precurations[0]?.status).toBe('submitted')
    })

    it('records errors and rethrows', async () => {
      const store = usePrecurationsStore()
      api.getPrecuration.mockRejectedValue(httpError('404'))

      await expect(store.fetchPrecurationById('x')).rejects.toThrow('404')
      expect(store.error).toEqual({ message: '404' })
    })
  })

  describe('createPrecuration', () => {
    it('prepends and increments the total', async () => {
      const store = usePrecurationsStore()
      store.precurations = [row('old')]
      store.pagination.total = 1
      api.createPrecuration.mockResolvedValue(full('new'))

      const created = await store.createPrecuration(newPrecuration)

      expect(created.id).toBe('new')
      expect(store.precurations.map(p => p.id)).toEqual(['new', 'old'])
      expect(store.pagination.total).toBe(2)
    })

    it('records errors and rethrows', async () => {
      const store = usePrecurationsStore()
      api.createPrecuration.mockRejectedValue(new Error('invalid'))

      await expect(store.createPrecuration(newPrecuration)).rejects.toThrow('invalid')
      expect(store.error).toEqual({ message: 'invalid' })
    })
  })

  describe('updatePrecuration', () => {
    it('updates list and current entries', async () => {
      const store = usePrecurationsStore()
      store.precurations = [row('p1')]
      store.currentPrecuration = full('p1')
      api.updatePrecuration.mockResolvedValue(full('p1', { status: 'submitted' }))

      await store.updatePrecuration('p1', { lock_version: 0 })

      expect(store.precurations[0]).toMatchObject({ status: 'submitted' })
      expect(store.currentPrecuration).toMatchObject({ status: 'submitted' })
    })

    it('records errors and rethrows', async () => {
      const store = usePrecurationsStore()
      api.updatePrecuration.mockRejectedValue(new Error('locked'))

      await expect(store.updatePrecuration('p1', { lock_version: 0 })).rejects.toThrow('locked')
      expect(store.error).toEqual({ message: 'locked' })
    })
  })

  describe('saveDraft', () => {
    it('wraps evidence data and updates list and current entries', async () => {
      const store = usePrecurationsStore()
      store.precurations = [row('p1')]
      store.currentPrecuration = full('p1', { lock_version: 7 })
      api.saveDraft.mockResolvedValue(full('p1', { status: 'submitted' }))

      const saved = await store.saveDraft('p1', { score: 2 })

      expect(api.saveDraft).toHaveBeenCalledWith('p1', {
        evidence_data: { score: 2 },
        lock_version: 7
      })
      expect(saved).toMatchObject({ status: 'submitted' })
      expect(store.precurations[0]).toMatchObject({ status: 'submitted' })
      expect(store.currentPrecuration).toMatchObject({ status: 'submitted' })
    })

    it('logs and swallows failures, flagging auto-save', async () => {
      const store = usePrecurationsStore()
      api.saveDraft.mockRejectedValue(new Error('offline'))

      await expect(store.saveDraft('p1', {})).resolves.toBeNull()
      expect(logService.error).toHaveBeenCalledWith(
        'Auto-save failed',
        expect.objectContaining({ precuration_id: 'p1', error: 'offline' })
      )
      expect(store.error).toEqual({ message: 'offline', isAutoSave: true })
    })

    it('flags a 409 as a conflict', async () => {
      const store = usePrecurationsStore()
      store.currentPrecuration = full('p1', { lock_version: 1 })
      api.saveDraft.mockRejectedValue({
        isAxiosError: true,
        message: 'Request failed',
        response: { status: 409, data: { current_lock_version: 2, your_lock_version: 1 } }
      })

      await expect(store.saveDraft('p1', {})).resolves.toBeNull()
      expect(store.error).toMatchObject({ isConflict: true, currentVersion: 2, yourVersion: 1 })
    })
  })

  describe('submitForReview', () => {
    it('submits with notes and updates both entries', async () => {
      const store = usePrecurationsStore()
      store.precurations = [row('p1')]
      store.currentPrecuration = full('p1')
      api.submitPrecuration.mockResolvedValue(full('p1', { status: 'submitted' }))

      const submitted = await store.submitForReview('p1', 'ready')

      expect(api.submitPrecuration).toHaveBeenCalledWith('p1', { notes: 'ready' })
      expect(submitted.status).toBe('submitted')
      expect(store.precurations[0]?.status).toBe('submitted')
      expect(store.currentPrecuration?.status).toBe('submitted')
    })

    it('defaults notes to null and records errors', async () => {
      const store = usePrecurationsStore()
      api.submitPrecuration.mockResolvedValueOnce(full('p1'))
      await store.submitForReview('p1')
      expect(api.submitPrecuration).toHaveBeenCalledWith('p1', { notes: null })

      api.submitPrecuration.mockRejectedValueOnce(new Error('not allowed'))
      await expect(store.submitForReview('p1')).rejects.toThrow('not allowed')
      expect(store.error).toEqual({ message: 'not allowed' })
    })
  })

  describe('approvePrecuration', () => {
    it('marks the listed precuration approved and returns the result', async () => {
      const store = usePrecurationsStore()
      store.precurations = [row('p1')]
      api.approvePrecuration.mockResolvedValue(approval)

      await expect(store.approvePrecuration('p1')).resolves.toEqual(approval)
      expect(store.precurations[0]?.status).toBe('approved')
    })

    it('returns the result without changing an unlisted precuration', async () => {
      const store = usePrecurationsStore()
      api.approvePrecuration.mockResolvedValue(approval)

      await store.approvePrecuration('p9')

      expect(store.precurations).toEqual([])
    })

    it('records errors and rethrows', async () => {
      const store = usePrecurationsStore()
      api.approvePrecuration.mockRejectedValue(new Error('denied'))

      await expect(store.approvePrecuration('p1')).rejects.toThrow('denied')
      expect(store.error).toEqual({ message: 'denied' })
    })
  })

  describe('rejectPrecuration', () => {
    it('updates the listed precuration with the rejected record', async () => {
      const store = usePrecurationsStore()
      store.precurations = [row('p1')]
      api.rejectPrecuration.mockResolvedValue(full('p1', { status: 'rejected' }))

      await store.rejectPrecuration('p1', 'weak evidence')

      expect(api.rejectPrecuration).toHaveBeenCalledWith('p1', { reason: 'weak evidence' })
      expect(store.precurations[0]?.status).toBe('rejected')
    })

    it('records errors and rethrows', async () => {
      const store = usePrecurationsStore()
      api.rejectPrecuration.mockRejectedValue(new Error('nope'))

      await expect(store.rejectPrecuration('p1', 'r')).rejects.toThrow('nope')
      expect(store.error).toEqual({ message: 'nope' })
    })
  })

  describe('deletePrecuration', () => {
    it('removes the entry, decrements the total and clears current', async () => {
      const store = usePrecurationsStore()
      store.precurations = [row('p1'), row('p2')]
      store.currentPrecuration = full('p1')
      store.pagination.total = 2
      api.deletePrecuration.mockResolvedValue(undefined)

      await expect(store.deletePrecuration('p1')).resolves.toBe(true)

      expect(store.precurations.map(p => p.id)).toEqual(['p2'])
      expect(store.pagination.total).toBe(1)
      expect(store.currentPrecuration).toBeNull()
    })

    it('keeps an unrelated current entry and floors the total at zero', async () => {
      const store = usePrecurationsStore()
      store.currentPrecuration = full('keep')
      api.deletePrecuration.mockResolvedValue(undefined)

      await store.deletePrecuration('p1')

      expect(store.pagination.total).toBe(0)
      expect(store.currentPrecuration?.id).toBe('keep')
    })

    it('records errors and rethrows', async () => {
      const store = usePrecurationsStore()
      api.deletePrecuration.mockRejectedValue(new Error('locked'))

      await expect(store.deletePrecuration('p1')).rejects.toThrow('locked')
      expect(store.error).toEqual({ message: 'locked' })
    })
  })

  describe('local state actions', () => {
    it('updateFilters merges and resets the page; setPage and current helpers', () => {
      const store = usePrecurationsStore()
      store.pagination.page = 4
      store.updateFilters({ status: 'draft' })
      expect(store.filters.status).toBe('draft')
      expect(store.pagination.page).toBe(1)

      store.setPage(2)
      expect(store.pagination.page).toBe(2)

      store.setCurrentPrecuration(full('p1'))
      expect(store.currentPrecuration?.id).toBe('p1')
      store.clearCurrentPrecuration()
      expect(store.currentPrecuration).toBeNull()
    })

    it('clearError and $reset restore defaults', () => {
      const store = usePrecurationsStore()
      store.error = { message: 'x' }
      store.clearError()
      expect(store.error).toBeNull()

      store.precurations = [row('p1')]
      store.currentPrecuration = full('p1')
      store.loading = true
      store.filters = { scope_id: 's', gene_id: 'g', status: 'draft' }
      store.$reset()

      expect(store.precurations).toEqual([])
      expect(store.currentPrecuration).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.filters).toEqual({ scope_id: null, gene_id: null, status: null })
      expect(store.pagination).toEqual({ page: 1, per_page: 50, total: 0, pages: 0 })
    })
  })
})
