import { describe, it, expect, vi, beforeEach, type Mock } from 'vitest'
import { logService, LogLevel, type LogEntry } from '../logService'

interface MockStore {
  logs: LogEntry[]
  addLogEntry: Mock<(entry: LogEntry, maxEntries: number) => void>
  trimLogs: Mock<(maxEntries: number) => void>
  clearLogs: Mock<() => void>
}

function makeStore(): MockStore {
  return {
    logs: [],
    addLogEntry: vi.fn<(entry: LogEntry, maxEntries: number) => void>(),
    trimLogs: vi.fn<(maxEntries: number) => void>(),
    clearLogs: vi.fn<() => void>()
  }
}

function lastEntry(store: MockStore): LogEntry {
  return store.addLogEntry.mock.lastCall?.[0] as LogEntry
}

describe('logService', () => {
  let store: MockStore

  beforeEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
    // The service is a singleton: reset every piece of mutable state between tests
    logService.store = null
    logService.consoleEcho = false
    logService.minLogLevel = 'DEBUG'
    logService.maxEntries = 100
    logService.correlationId = null
    logService.metadata = {}
    store = makeStore()
  })

  describe('LogLevel', () => {
    it('exposes the five canonical level names', () => {
      expect(LogLevel).toEqual({
        DEBUG: 'DEBUG',
        INFO: 'INFO',
        WARN: 'WARN',
        ERROR: 'ERROR',
        CRITICAL: 'CRITICAL'
      })
    })
  })

  describe('store integration', () => {
    it('initStore writes an initialisation entry to the store', () => {
      logService.initStore(store)

      expect(logService.store).toBe(store)
      expect(lastEntry(store)).toMatchObject({
        level: LogLevel.INFO,
        message: 'LogService initialized'
      })
    })

    it('adds full context to each entry: correlation id, metadata and page info', () => {
      logService.initStore(store)
      logService.setCorrelationId('req-1')
      logService.setMetadata({ tenant: 'lab' })
      logService.setMetadata({ role: 'curator' })

      logService.info('hello', { step: 1 })

      const entry = lastEntry(store)
      expect(entry).toMatchObject({
        level: LogLevel.INFO,
        message: 'hello',
        data: { step: 1 },
        correlationId: 'req-1',
        metadata: { tenant: 'lab', role: 'curator' }
      })
      expect(entry.timestamp).toEqual(expect.any(String))
      expect(entry.url).toEqual(expect.any(String))
      expect(entry.userAgent).toEqual(expect.any(String))
    })

    it('sanitises messages and data before they reach the store', () => {
      logService.initStore(store)

      logService.error('login for user@example.com', { token: 'abc', note: 'ok' })

      expect(lastEntry(store)).toMatchObject({
        message: 'login for [REDACTED_EMAIL]',
        data: { token: '[REDACTED_SENSITIVE]', note: 'ok' }
      })
    })

    it('keeps logging when the store throws, reporting the failure to the console', () => {
      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      store.addLogEntry.mockImplementation(() => {
        throw new Error('store full')
      })
      logService.initStore(store)

      expect(() => logService.warn('still fine')).not.toThrow()
      expect(errorSpy).toHaveBeenCalledWith('Failed to add log to store:', expect.any(Error))
    })

    it('does not touch a store when none is attached', () => {
      expect(() => logService.error('no store yet')).not.toThrow()
      expect(store.addLogEntry).not.toHaveBeenCalled()
    })

    it('clearLogs and exportLogs delegate to the store', () => {
      logService.initStore(store)
      store.logs.push({ message: 'kept' } as unknown as LogEntry)

      logService.clearLogs()
      expect(store.clearLogs).toHaveBeenCalledTimes(1)

      const exported = logService.exportLogs()
      expect(exported).toMatchObject({
        environment: expect.any(String),
        configuration: { maxEntries: 100, minLogLevel: 'DEBUG', consoleEcho: false },
        logs: store.logs
      })
    })

    it('exportLogs returns an empty payload when no store is attached', () => {
      expect(logService.exportLogs()).toEqual({
        logs: [],
        exportedAt: expect.any(String)
      })
    })
  })

  describe('level filtering and public methods', () => {
    it('drops entries below the minimum level', () => {
      logService.initStore(store)
      logService.setMinLogLevel('WARN')
      store.addLogEntry.mockClear()

      logService.debug('d')
      logService.info('i')
      logService.warn('w')
      logService.error('e')
      logService.critical('c')

      const levels = store.addLogEntry.mock.calls.map(call => (call[0] as LogEntry).level)
      expect(levels).toEqual([LogLevel.WARN, LogLevel.ERROR, LogLevel.CRITICAL])
    })

    it('stores critical entries at CRITICAL level', () => {
      logService.initStore(store)
      logService.critical('boom', { code: 7 })
      expect(lastEntry(store)).toMatchObject({ level: LogLevel.CRITICAL, data: { code: 7 } })
    })

    it('logPerformance warns when the operation is slow and debugs otherwise', () => {
      logService.initStore(store)
      const now = vi.spyOn(window.performance, 'now')

      now.mockReturnValue(1500)
      logService.logPerformance('load', 0, { rows: 3 })
      expect(lastEntry(store)).toMatchObject({
        level: LogLevel.WARN,
        message: 'Performance: load',
        data: { rows: 3, duration_ms: 1500, slow: true }
      })

      now.mockReturnValue(20)
      logService.logPerformance('quick', 0)
      expect(lastEntry(store)).toMatchObject({
        level: LogLevel.DEBUG,
        data: { duration_ms: 20, slow: false }
      })
    })

    it('logApiCall maps status codes onto success and error levels', () => {
      logService.initStore(store)

      logService.logApiCall('GET', '/genes', 200, 12)
      expect(lastEntry(store)).toMatchObject({
        level: LogLevel.DEBUG,
        message: 'API GET /genes',
        data: { status: 200, duration_ms: 12, success: true }
      })

      logService.logApiCall('POST', '/genes', 422, 8)
      expect(lastEntry(store)).toMatchObject({
        level: LogLevel.ERROR,
        data: { status: 422, success: false }
      })
    })
  })

  describe('console echo', () => {
    it('is off by default and echoes each level to the matching console method when enabled', () => {
      const debugSpy = vi.spyOn(console, 'debug').mockImplementation(() => {})
      const infoSpy = vi.spyOn(console, 'info').mockImplementation(() => {})
      const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

      logService.debug('quiet')
      expect(debugSpy).not.toHaveBeenCalled()

      logService.setConsoleEcho(true)
      logService.debug('d', { a: 1 })
      logService.info('i')
      logService.warn('w')
      logService.error('e')
      logService.critical('c')

      expect(debugSpy).toHaveBeenCalledWith('[DEBUG]', 'd', { a: 1 })
      expect(infoSpy).toHaveBeenCalledWith('[INFO]', 'i')
      expect(warnSpy).toHaveBeenCalledWith('[WARN]', 'w')
      expect(errorSpy).toHaveBeenCalledWith('[ERROR]', 'e')
      expect(errorSpy).toHaveBeenCalledWith('[CRITICAL]', 'c')
    })

    it('persists the echo setting to localStorage', () => {
      logService.setConsoleEcho(true)
      expect(localStorage.getItem('gene-curator-console-echo')).toBe('true')
    })
  })

  describe('correlation and metadata', () => {
    it('clearMetadata removes all global metadata', () => {
      logService.setMetadata({ a: 1 })
      logService.clearMetadata()
      expect(logService.metadata).toEqual({})
    })

    it('clearCorrelationId resets the id used for later entries', () => {
      logService.initStore(store)
      logService.setCorrelationId('abc')
      logService.clearCorrelationId()
      logService.info('after')
      expect(lastEntry(store).correlationId).toBeNull()
    })
  })

  describe('configuration', () => {
    it('setMaxEntries persists the value and trims the store', () => {
      logService.initStore(store)
      logService.setMaxEntries(25)

      expect(logService.maxEntries).toBe(25)
      expect(localStorage.getItem('gene-curator-log-max-entries')).toBe('25')
      expect(store.trimLogs).toHaveBeenCalledWith(25)
    })

    it('setMaxEntries without a store only updates the setting', () => {
      expect(() => logService.setMaxEntries(5)).not.toThrow()
      expect(logService.maxEntries).toBe(5)
    })

    it('setMinLogLevel accepts known levels and ignores unknown ones', () => {
      logService.setMinLogLevel('ERROR')
      expect(logService.minLogLevel).toBe('ERROR')
      expect(localStorage.getItem('gene-curator-log-level')).toBe('ERROR')

      logService.setMinLogLevel('VERBOSE')
      expect(logService.minLogLevel).toBe('ERROR')
    })
  })

  describe('loading persisted settings', () => {
    it('reads console echo, max entries and level from localStorage', () => {
      localStorage.setItem('gene-curator-console-echo', 'true')
      localStorage.setItem('gene-curator-log-max-entries', '42')
      localStorage.setItem('gene-curator-log-level', 'WARN')

      expect(logService.loadConsoleEchoFromStorage()).toBe(true)
      expect(logService.loadMaxEntriesFromStorage()).toBe(42)
      expect(logService.loadLogLevelFromStorage()).toBe('WARN')
    })

    it('falls back to defaults for missing or invalid values', () => {
      localStorage.setItem('gene-curator-log-max-entries', '-3')
      localStorage.setItem('gene-curator-log-level', 'LOUD')

      expect(logService.loadConsoleEchoFromStorage()).toBe(false)
      expect(logService.loadMaxEntriesFromStorage()).toBe(import.meta.env.DEV ? 100 : 50)
      expect(logService.loadLogLevelFromStorage()).toBe(
        import.meta.env.DEV ? LogLevel.DEBUG : LogLevel.INFO
      )
    })

    it('uses defaults and reports the error when localStorage throws', () => {
      const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      vi.stubGlobal('localStorage', {
        getItem: () => {
          throw new Error('storage disabled')
        },
        setItem: () => {}
      })

      try {
        expect(logService.loadConsoleEchoFromStorage()).toBe(false)
        expect(logService.loadMaxEntriesFromStorage()).toBe(import.meta.env.DEV ? 100 : 50)
        expect(logService.loadLogLevelFromStorage()).toBe(
          import.meta.env.DEV ? LogLevel.DEBUG : LogLevel.INFO
        )
        expect(errorSpy).toHaveBeenCalledTimes(3)
      } finally {
        vi.unstubAllGlobals()
      }
    })
  })
})
