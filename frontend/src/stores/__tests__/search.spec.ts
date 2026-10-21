import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { searchAPI } from '@/api/search'
import { useSearchStore } from '@/stores/search'

vi.mock('@/api/search', () => ({ searchAPI: { search: vi.fn() } }))

const hits = {
  genes: [{ id: 'g1', symbol: 'PKD1', hgnc_id: 'HGNC:9008' }],
  curations: [],
  scopes: []
}

describe('search store', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    vi.mocked(searchAPI.search).mockReset()
    vi.mocked(searchAPI.search).mockResolvedValue(hits as never)
  })
  afterEach(() => vi.useRealTimers())

  it('open and close toggle the palette and clear state', () => {
    const s = useSearchStore()
    s.open()
    expect(s.isOpen).toBe(true)
    s.setQuery('pk')
    s.close()
    expect(s.isOpen).toBe(false)
    expect(s.query).toBe('')
    expect(s.results).toBeNull()
  })

  it('open({ help: true }) shows the shortcut list', () => {
    const s = useSearchStore()
    s.open({ help: true })
    expect(s.showHelp).toBe(true)
    s.close()
    s.open()
    expect(s.showHelp).toBe(false)
  })

  it('typing after "?" leaves the shortcut list so results show again', () => {
    const s = useSearchStore()
    s.open({ help: true })
    s.setQuery('pk')
    expect(s.showHelp).toBe(false)
  })

  it('debounces: one request after 200 ms of quiet, with the final text', async () => {
    const s = useSearchStore()
    s.setQuery('pk')
    vi.advanceTimersByTime(150)
    s.setQuery('pkd')
    vi.advanceTimersByTime(150)
    expect(searchAPI.search).not.toHaveBeenCalled()
    vi.advanceTimersByTime(60)
    expect(searchAPI.search).toHaveBeenCalledTimes(1)
    expect(searchAPI.search).toHaveBeenCalledWith('pkd', expect.any(AbortSignal))
    await vi.runAllTimersAsync()
    expect(s.results).toEqual(hits)
    expect(s.loading).toBe(false)
  })

  it('does not call the backend below 2 characters (it would 422)', async () => {
    const s = useSearchStore()
    s.setQuery('p')
    s.setQuery(' p ')
    await vi.runAllTimersAsync()
    expect(searchAPI.search).not.toHaveBeenCalled()
    expect(s.results).toBeNull()
  })

  it('aborts the in-flight request when the text changes and ignores its late answer', async () => {
    let first!: (v: unknown) => void
    vi.mocked(searchAPI.search)
      .mockImplementationOnce(() => new Promise(r => (first = r)) as never)
      .mockResolvedValueOnce({
        genes: [],
        curations: [],
        scopes: [{ id: 's', name: 'n', display_name: 'N' }]
      } as never)
    const s = useSearchStore()
    s.setQuery('pkd')
    vi.advanceTimersByTime(200)
    const signal = vi.mocked(searchAPI.search).mock.calls[0]![1] as AbortSignal
    s.setQuery('kidney')
    expect(signal.aborted).toBe(true)
    vi.advanceTimersByTime(200)
    await vi.runAllTimersAsync()
    first(hits)
    await vi.runAllTimersAsync()
    expect(s.results?.scopes).toHaveLength(1)
    expect(s.results?.genes).toHaveLength(0)
  })

  it('clearing the text cancels a pending request', async () => {
    const s = useSearchStore()
    s.setQuery('pkd')
    s.setQuery('')
    await vi.runAllTimersAsync()
    expect(searchAPI.search).not.toHaveBeenCalled()
    expect(s.loading).toBe(false)
  })

  it('reports a failed search and keeps no stale results', async () => {
    vi.mocked(searchAPI.search).mockRejectedValueOnce(new Error('boom'))
    const s = useSearchStore()
    s.setQuery('pkd')
    await vi.runAllTimersAsync()
    expect(s.error).toBe('Search failed. Try again.')
    expect(s.results).toBeNull()
    expect(s.loading).toBe(false)
  })
})
