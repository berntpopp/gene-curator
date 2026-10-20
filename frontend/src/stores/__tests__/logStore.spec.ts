import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useLogStore } from '@/stores/logStore'

function stubFailingStorage(method: 'getItem' | 'setItem' | 'removeItem', message: string) {
  const store: Record<string, unknown> = {
    getItem: () => null,
    setItem: () => undefined,
    removeItem: () => undefined,
    clear: () => undefined
  }
  store[method] = () => {
    throw new Error(message)
  }
  vi.stubGlobal('localStorage', store)
}

const entry = (level: string, message: string, extra: Record<string, unknown> = {}) => ({
  level,
  message,
  timestamp: '2025-01-01T00:00:00.000Z',
  ...extra
})

describe('useLogStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  describe('initial state', () => {
    it('uses the stored max entries when valid', () => {
      localStorage.setItem('gene-curator-log-max-entries', '7')
      setActivePinia(createPinia())
      expect(useLogStore().maxEntries).toBe(7)
    })

    it('falls back to the environment default for missing or invalid values', () => {
      localStorage.setItem('gene-curator-log-max-entries', 'abc')
      setActivePinia(createPinia())
      expect(useLogStore().maxEntries).toBeGreaterThan(0)
    })

    it('logs and uses the default when localStorage throws', () => {
      stubFailingStorage('getItem', 'blocked')
      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => undefined)
      setActivePinia(createPinia())

      const store = useLogStore()

      expect(store.maxEntries).toBeGreaterThan(0)
      expect(errorSpy).toHaveBeenCalledWith(
        'Failed to load max entries from storage:',
        expect.any(Error)
      )
    })
  })

  describe('addLogEntry', () => {
    it('appends entries, stamps a missing timestamp and counts received logs', () => {
      const store = useLogStore()
      const bare = { level: 'INFO', message: 'hello' } as ReturnType<typeof entry>

      store.addLogEntry(bare)

      expect(store.logs).toHaveLength(1)
      expect(store.logs[0]?.timestamp).toEqual(expect.any(String))
      expect(store.stats.totalLogsReceived).toBe(1)
      expect(store.stats.lastLogTime).toBe(store.logs[0]?.timestamp)
    })

    it('trims the oldest entries beyond maxEntries and counts drops', () => {
      const store = useLogStore()
      store.trimLogs(2)
      store.addLogEntry(entry('INFO', 'a'))
      store.addLogEntry(entry('INFO', 'b'))
      store.addLogEntry(entry('INFO', 'c'))

      expect(store.logs.map(l => l.message)).toEqual(['b', 'c'])
      expect(store.stats.totalLogsDropped).toBe(1)
    })

    it('honours a per-call max override', () => {
      const store = useLogStore()
      store.addLogEntry(entry('INFO', 'a'), 1)
      store.addLogEntry(entry('INFO', 'b'), 1)

      expect(store.logs.map(l => l.message)).toEqual(['b'])
    })
  })

  describe('clearLogs and trimLogs', () => {
    it('clearLogs empties the list and returns the previous count', () => {
      const store = useLogStore()
      store.addLogEntry(entry('INFO', 'a'))
      store.addLogEntry(entry('INFO', 'b'))

      expect(store.clearLogs()).toBe(2)
      expect(store.logs).toEqual([])
      expect(store.stats.totalLogsDropped).toBe(2)
    })

    it('trimLogs updates maxEntries and only drops when over the limit', () => {
      const store = useLogStore()
      store.addLogEntry(entry('INFO', 'a'))

      store.trimLogs(5)
      expect(store.maxEntries).toBe(5)
      expect(store.logs).toHaveLength(1)
      expect(store.stats.totalLogsDropped).toBe(0)
    })
  })

  describe('computed counts', () => {
    it('counts logs by level and derives error and warning totals', () => {
      const store = useLogStore()
      store.addLogEntry(entry('DEBUG', 'd'))
      store.addLogEntry(entry('INFO', 'i'))
      store.addLogEntry(entry('WARN', 'w'))
      store.addLogEntry(entry('ERROR', 'e'))
      store.addLogEntry(entry('CRITICAL', 'c'))

      expect(store.logCount).toBe(5)
      expect(store.debugCount).toBe(1)
      expect(store.infoCount).toBe(1)
      expect(store.warningCount).toBe(1)
      expect(store.errorCount).toBe(2)
      expect(store.logsByLevel).toEqual({ DEBUG: 1, INFO: 1, WARN: 1, ERROR: 1, CRITICAL: 1 })
      expect(store.recentErrors.map(l => l.message)).toEqual(['c', 'e'])
    })

    it('ignores unknown levels in the per-level counts', () => {
      const store = useLogStore()
      store.addLogEntry(entry('TRACE', 't'))
      expect(store.logsByLevel.DEBUG).toBe(0)
      expect(store.logCount).toBe(1)
    })

    it('reports an approximate memory footprint', () => {
      const store = useLogStore()
      expect(store.memoryUsage.bytes).toBe(2)
      store.addLogEntry(entry('INFO', 'x'.repeat(2048)))
      expect(store.memoryUsage.bytes).toBeGreaterThan(2048)
      expect(store.memoryUsage.kb).toMatch(/^\d+\.\d{2}$/)
      expect(store.memoryUsage.mb).toMatch(/^\d+\.\d{2}$/)
    })
  })

  describe('filteredLogs', () => {
    it('filters by level and by search text across message, level, data and correlation id', () => {
      const store = useLogStore()
      store.addLogEntry(entry('INFO', 'Loaded genes'))
      store.addLogEntry(entry('ERROR', 'Save failed', { data: { gene: 'BRCA1' } }))
      store.addLogEntry(entry('WARN', 'Slow call', { correlationId: 'abc-123' }))

      store.setLevelFilter(['ERROR', 'WARN'])
      expect(store.filteredLogs.map(l => l.message)).toEqual(['Save failed', 'Slow call'])

      store.setLevelFilter([])
      store.setSearchQuery('brca1')
      expect(store.filteredLogs.map(l => l.message)).toEqual(['Save failed'])

      store.setSearchQuery('warn')
      expect(store.filteredLogs.map(l => l.message)).toEqual(['Slow call'])

      store.setSearchQuery('ABC-123')
      expect(store.filteredLogs.map(l => l.message)).toEqual(['Slow call'])
    })
  })

  describe('viewer visibility', () => {
    it('shows, hides and toggles the viewer', () => {
      const store = useLogStore()
      store.showViewer()
      expect(store.isViewerVisible).toBe(true)
      store.hideViewer()
      expect(store.isViewerVisible).toBe(false)
      store.toggleViewer()
      expect(store.isViewerVisible).toBe(true)
    })
  })

  describe('exportLogs', () => {
    beforeEach(() => {
      vi.stubGlobal('navigator', { userAgent: 'test-agent' })
    })

    it('exports JSON with statistics and metadata by default', () => {
      const store = useLogStore()
      store.addLogEntry(entry('INFO', 'one'))

      const output = store.exportLogs()
      expect(typeof output).toBe('string')
      const parsed = JSON.parse(output as string)

      expect(parsed.application).toBe('Gene Curator')
      expect(parsed.statistics).toMatchObject({ totalExported: 1, totalReceived: 1, INFO: 1 })
      expect(parsed.metadata.userAgent).toBe('test-agent')
      expect(parsed.logs).toHaveLength(1)
    })

    it('omits metadata on request and exports only filtered logs', () => {
      const store = useLogStore()
      store.addLogEntry(entry('INFO', 'keep'))
      store.addLogEntry(entry('ERROR', 'drop'))
      store.setLevelFilter(['INFO'])

      const parsed = JSON.parse(
        store.exportLogs({ format: 'json', includeMetadata: false, filtered: true }) as string
      )

      expect(parsed.metadata).toBeUndefined()
      expect(parsed.logs.map((l: { message: string }) => l.message)).toEqual(['keep'])
    })

    it('exports CSV with escaped cells', () => {
      const store = useLogStore()
      store.addLogEntry(entry('INFO', 'say "hi"', { correlationId: 'c1', url: '/x' }))

      const csv = store.exportLogs({ format: 'csv' }) as string
      const lines = csv.split('\n')

      expect(lines[0]).toBe('Timestamp,Level,Message,Data,Correlation ID,URL')
      expect(lines[1]).toContain('"say ""hi"""')
      expect(lines[1]).toContain('"c1"')
    })

    it('returns an empty string for CSV without logs', () => {
      const store = useLogStore()
      expect(store.exportLogs({ format: 'csv' })).toBe('')
    })

    it('returns the raw object for an unknown format', () => {
      const store = useLogStore()
      const result = store.exportLogs({ format: 'xml' as never }) as Record<string, unknown>
      expect(result.application).toBe('Gene Curator')
      expect(result.logs).toEqual([])
    })
  })
})
