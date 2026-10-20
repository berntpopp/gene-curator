import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import type { CurationRecord } from '@/stores/curations'
import { useCurationsStore } from '@/stores/curations'
import { curationsAPI } from '@/api/curations'

vi.mock('@/api/curations', () => ({
  curationsAPI: {
    getCurations: vi.fn(),
    getCuration: vi.fn(),
    createCuration: vi.fn(),
    updateCuration: vi.fn(),
    saveDraft: vi.fn(),
    submitCuration: vi.fn(),
    deleteCuration: vi.fn(),
    calculateScore: vi.fn()
  }
}))

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const api = vi.mocked(curationsAPI)

/** Minimal curation rows; the store only reads these fields. */
const row = (id: string, extra: Record<string, unknown> = {}) =>
  ({
    id,
    gene_id: 'g1',
    scope_id: 's1',
    status: 'draft',
    is_draft: true,
    ...extra
  }) as CurationRecord

/** Axios-style error with an HTTP status and body. */
const httpError = (status: number, data: Record<string, unknown> = {}) =>
  Object.assign(new Error(`HTTP ${status}`), { response: { status, data } })

describe('useCurationsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('getters', () => {
    it('filters curations by id, scope, gene, draft and submitted status', () => {
      const store = useCurationsStore()
      store.curations = [
        row('c1'),
        row('c2', { scope_id: 's2', gene_id: 'g2', is_draft: false, status: 'submitted' })
      ]

      expect(store.getCurationById('c2')?.id).toBe('c2')
      expect(store.getCurationById('none')).toBeUndefined()
      expect(store.getCurationsByScope('s2').map(c => c.id)).toEqual(['c2'])
      expect(store.getCurationsByGene('g1').map(c => c.id)).toEqual(['c1'])
      expect(store.getDraftCurations.map(c => c.id)).toEqual(['c1'])
      expect(store.getSubmittedCurations.map(c => c.id)).toEqual(['c2'])
    })

    it('reports error and conflict state', () => {
      const store = useCurationsStore()
      expect(store.hasError).toBe(false)
      expect(store.isConflictError).toBe(false)

      store.error = { message: 'x', isConflict: true }
      expect(store.hasError).toBe(true)
      expect(store.isConflictError).toBe(true)
    })
  })

  describe('fetchCurations', () => {
    it('merges filters and paging into the request and stores the list', async () => {
      const store = useCurationsStore()
      store.filters.scope_id = 's1'
      store.pagination.page = 2
      api.getCurations.mockResolvedValue({ curations: [row('c1')], total: 120 } as never)

      const result = await store.fetchCurations({ status: 'draft' })

      expect(api.getCurations).toHaveBeenCalledWith({
        scope_id: 's1',
        gene_id: null,
        status: 'draft',
        curator_id: null,
        skip: 50,
        limit: 50
      })
      expect(result).toEqual({ curations: [row('c1')], total: 120 })
      expect(store.curations).toHaveLength(1)
      expect(store.pagination.total).toBe(120)
      expect(store.pagination.pages).toBe(3)
    })

    it('defaults to empty results when the response is sparse', async () => {
      const store = useCurationsStore()
      api.getCurations.mockResolvedValue({} as never)

      await store.fetchCurations()

      expect(store.curations).toEqual([])
      expect(store.pagination.total).toBe(0)
    })

    it('stores the error message and rethrows', async () => {
      const store = useCurationsStore()
      api.getCurations.mockRejectedValue(new Error('down'))

      await expect(store.fetchCurations()).rejects.toThrow('down')
      expect(store.error).toEqual({ message: 'down' })
      expect(store.loading).toBe(false)
    })
  })

  describe('fetchCurationById', () => {
    it('sets the current curation and refreshes the list entry', async () => {
      const store = useCurationsStore()
      store.curations = [row('c1', { status: 'draft' })]
      api.getCuration.mockResolvedValue(row('c1', { status: 'submitted' }))

      const result = await store.fetchCurationById('c1')

      expect(result.status).toBe('submitted')
      expect(store.currentCuration?.id).toBe('c1')
      expect(store.curations[0]?.status).toBe('submitted')
    })

    it('leaves the list untouched when the curation is not listed', async () => {
      const store = useCurationsStore()
      api.getCuration.mockResolvedValue(row('c9'))

      await store.fetchCurationById('c9')

      expect(store.curations).toEqual([])
      expect(store.currentCuration?.id).toBe('c9')
    })

    it('records the error and rethrows', async () => {
      const store = useCurationsStore()
      api.getCuration.mockRejectedValue(new Error('404'))

      await expect(store.fetchCurationById('x')).rejects.toThrow('404')
      expect(store.error).toEqual({ message: '404' })
    })
  })

  describe('createCuration', () => {
    it('prepends the new curation and increments the total', async () => {
      const store = useCurationsStore()
      store.curations = [row('old')]
      store.pagination.total = 1
      api.createCuration.mockResolvedValue(row('new'))

      const created = await store.createCuration({} as Parameters<typeof api.createCuration>[0])

      expect(created.id).toBe('new')
      expect(store.curations.map(c => c.id)).toEqual(['new', 'old'])
      expect(store.pagination.total).toBe(2)
    })

    it('records the error and rethrows', async () => {
      const store = useCurationsStore()
      api.createCuration.mockRejectedValue(new Error('invalid'))

      await expect(
        store.createCuration({} as Parameters<typeof api.createCuration>[0])
      ).rejects.toThrow('invalid')
      expect(store.error).toEqual({ message: 'invalid' })
      expect(store.pagination.total).toBe(0)
    })
  })

  describe('updateCuration', () => {
    it('updates the list entry and the current curation', async () => {
      const store = useCurationsStore()
      store.curations = [row('c1')]
      store.currentCuration = row('c1')
      api.updateCuration.mockResolvedValue(row('c1', { status: 'submitted' }))

      const updated = await store.updateCuration('c1', {} as never)

      expect(updated.status).toBe('submitted')
      expect(store.curations[0]?.status).toBe('submitted')
      expect(store.currentCuration?.status).toBe('submitted')
    })

    it('does not touch unrelated current curation', async () => {
      const store = useCurationsStore()
      store.currentCuration = row('other')
      api.updateCuration.mockResolvedValue(row('c1'))

      await store.updateCuration('c1', {} as never)

      expect(store.currentCuration?.id).toBe('other')
    })

    it('flags 409 conflicts with lock versions and rethrows', async () => {
      const store = useCurationsStore()
      api.updateCuration.mockRejectedValue(
        httpError(409, {
          current_lock_version: 5,
          your_lock_version: 3,
          current_state: 'submitted'
        })
      )

      await expect(store.updateCuration('c1', {} as never)).rejects.toThrow('HTTP 409')

      expect(store.isConflictError).toBe(true)
      expect(store.error).toEqual({
        message: 'Another user has modified this curation. Please refresh and try again.',
        isConflict: true,
        currentVersion: 5,
        yourVersion: 3,
        currentState: 'submitted'
      })
    })

    it('handles a 409 without a response body', async () => {
      const store = useCurationsStore()
      api.updateCuration.mockRejectedValue(
        Object.assign(new Error('conflict'), { response: { status: 409 } })
      )

      await expect(store.updateCuration('c1', {} as never)).rejects.toThrow('conflict')
      expect(store.error?.isConflict).toBe(true)
      expect(store.error?.currentVersion).toBeUndefined()
    })

    it('stores plain messages for other failures', async () => {
      const store = useCurationsStore()
      api.updateCuration.mockRejectedValue(httpError(500))

      await expect(store.updateCuration('c1', {} as never)).rejects.toThrow('HTTP 500')
      expect(store.error).toEqual({ message: 'HTTP 500' })
      expect(store.loading).toBe(false)
    })
  })

  describe('saveDraft', () => {
    it('updates list and current entries on success', async () => {
      const store = useCurationsStore()
      store.curations = [row('c1')]
      store.currentCuration = row('c1')
      api.saveDraft.mockResolvedValue(row('c1', { auto_saved: true }))

      const saved = await store.saveDraft('c1', {} as never)

      expect(saved).toMatchObject({ id: 'c1' })
      expect(store.curations[0]).toMatchObject({ auto_saved: true })
      expect(store.currentCuration).toMatchObject({ auto_saved: true })
      expect(store.loading).toBe(false)
    })

    it('swallows failures, flags auto-save and returns null', async () => {
      const store = useCurationsStore()
      api.saveDraft.mockRejectedValue(new Error('offline'))

      await expect(store.saveDraft('c1', {} as never)).resolves.toBeNull()
      expect(store.error).toEqual({ message: 'offline', isAutoSave: true })
    })
  })

  describe('submitCuration', () => {
    it('updates list and current entries', async () => {
      const store = useCurationsStore()
      store.curations = [row('c1')]
      store.currentCuration = row('c1')
      api.submitCuration.mockResolvedValue(row('c1', { status: 'submitted' }))

      const submitted = await store.submitCuration('c1')

      expect(api.submitCuration).toHaveBeenCalledWith('c1', {})
      expect(submitted.status).toBe('submitted')
      expect(store.curations[0]?.status).toBe('submitted')
      expect(store.currentCuration?.status).toBe('submitted')
    })

    it('flags a 409 as conflict', async () => {
      const store = useCurationsStore()
      api.submitCuration.mockRejectedValue(httpError(409))

      await expect(store.submitCuration('c1', {} as never)).rejects.toThrow('HTTP 409')
      expect(store.error).toEqual({
        message: 'Curation was modified. Please refresh and try again.',
        isConflict: true
      })
    })

    it('stores plain messages for other failures', async () => {
      const store = useCurationsStore()
      api.submitCuration.mockRejectedValue(new Error('bad'))

      await expect(store.submitCuration('c1', {} as never)).rejects.toThrow('bad')
      expect(store.error).toEqual({ message: 'bad' })
    })
  })

  describe('deleteCuration', () => {
    it('removes the curation, decrements the total and clears current', async () => {
      const store = useCurationsStore()
      store.curations = [row('c1'), row('c2')]
      store.currentCuration = row('c1')
      store.pagination.total = 2
      api.deleteCuration.mockResolvedValue({} as never)

      await expect(store.deleteCuration('c1')).resolves.toBe(true)

      expect(store.curations.map(c => c.id)).toEqual(['c2'])
      expect(store.pagination.total).toBe(1)
      expect(store.currentCuration).toBeNull()
    })

    it('never lets the total go negative and keeps unrelated current curation', async () => {
      const store = useCurationsStore()
      store.currentCuration = row('keep')
      store.pagination.total = 0
      api.deleteCuration.mockResolvedValue({} as never)

      await store.deleteCuration('c1')

      expect(store.pagination.total).toBe(0)
      expect(store.currentCuration?.id).toBe('keep')
    })

    it('records the error and rethrows', async () => {
      const store = useCurationsStore()
      api.deleteCuration.mockRejectedValue(new Error('locked'))

      await expect(store.deleteCuration('c1')).rejects.toThrow('locked')
      expect(store.error).toEqual({ message: 'locked' })
    })
  })

  describe('calculateScore', () => {
    it('returns the score result', async () => {
      const store = useCurationsStore()
      api.calculateScore.mockResolvedValue({ total_score: 12 })

      await expect(store.calculateScore('c1')).resolves.toEqual({ total_score: 12 })
      expect(store.loading).toBe(false)
    })

    it('records the error and rethrows', async () => {
      const store = useCurationsStore()
      api.calculateScore.mockRejectedValue(new Error('no schema'))

      await expect(store.calculateScore('c1')).rejects.toThrow('no schema')
      expect(store.error).toEqual({ message: 'no schema' })
    })
  })

  describe('local state actions', () => {
    it('updateFilters merges filters and resets the page', () => {
      const store = useCurationsStore()
      store.pagination.page = 4
      store.updateFilters({ status: 'submitted' })
      expect(store.filters.status).toBe('submitted')
      expect(store.filters.scope_id).toBeNull()
      expect(store.pagination.page).toBe(1)
    })

    it('setPage, setCurrentCuration and clearCurrentCuration', () => {
      const store = useCurationsStore()
      store.setPage(3)
      expect(store.pagination.page).toBe(3)

      store.setCurrentCuration(row('c1'))
      expect(store.currentCuration?.id).toBe('c1')

      store.clearCurrentCuration()
      expect(store.currentCuration).toBeNull()
    })

    it('clearError resets the error', () => {
      const store = useCurationsStore()
      store.error = { message: 'x' }
      store.clearError()
      expect(store.error).toBeNull()
    })

    it('$reset restores the initial state', () => {
      const store = useCurationsStore()
      store.curations = [row('c1')]
      store.currentCuration = row('c1')
      store.loading = true
      store.error = { message: 'x' }
      store.pagination = { page: 5, per_page: 10, total: 9, pages: 1 }
      store.filters = { scope_id: 's', gene_id: 'g', status: 's', curator_id: 'c' }

      store.$reset()

      expect(store.curations).toEqual([])
      expect(store.currentCuration).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.pagination).toEqual({ page: 1, per_page: 50, total: 0, pages: 0 })
      expect(store.filters).toEqual({
        scope_id: null,
        gene_id: null,
        status: null,
        curator_id: null
      })
    })
  })
})
