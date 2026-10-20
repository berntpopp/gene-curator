import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import type { App } from 'vue'
import loggerPlugin from '../logger'
import { logService } from '@/services/logService'
import { useLogStore } from '@/stores/logStore'

vi.mock('@/services/logService', () => ({
  logService: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
    critical: vi.fn(),
    initStore: vi.fn()
  }
}))

vi.mock('@/stores/logStore', () => ({
  useLogStore: vi.fn()
}))

interface FakeApp {
  config: {
    globalProperties: Record<string, unknown>
    errorHandler?: (err: unknown, instance: unknown, info: string) => void
    warnHandler?: (msg: string, instance: unknown, trace: string) => void
  }
}

function makeApp(pinia?: unknown): FakeApp {
  return { config: { globalProperties: pinia ? { $pinia: pinia } : {} } }
}

describe('logger plugin', () => {
  const store = { addLogEntry: vi.fn(), trimLogs: vi.fn(), clearLogs: vi.fn(), logs: [] }

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(useLogStore).mockReturnValue(store as never)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('exposes the logger as $logger and wires the store from the app pinia', () => {
    const pinia = { id: 'pinia' }
    const app = makeApp(pinia)

    loggerPlugin.install(app as unknown as App)

    expect(app.config.globalProperties.$logger).toBe(logService)
    expect(useLogStore).toHaveBeenCalledWith(pinia)
    expect(logService.initStore).toHaveBeenCalledWith(store)
    expect(logService.debug).toHaveBeenCalledWith('Logger plugin installed', expect.any(Object))
  })

  it('falls back to the active pinia and warns when no store can be created', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.mocked(useLogStore).mockImplementation(() => {
      throw new Error('no active pinia')
    })

    expect(() => loggerPlugin.install(makeApp() as unknown as App)).not.toThrow()

    expect(logService.initStore).not.toHaveBeenCalled()
    expect(warnSpy).toHaveBeenCalledTimes(2)
  })

  it('reports unexpected install failures to the console', () => {
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
    const app = makeApp({ id: 'pinia' })
    vi.mocked(useLogStore).mockReturnValue(store as never)
    vi.mocked(logService.initStore).mockImplementationOnce(() => {
      throw new Error('init exploded')
    })

    expect(() => loggerPlugin.install(app as unknown as App)).not.toThrow()

    expect(errorSpy).toHaveBeenCalledWith('Failed to initialize logger plugin:', expect.any(Error))
  })

  it('routes uncaught Vue errors to the critical log with component context', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
    const app = makeApp({ id: 'pinia' })
    loggerPlugin.install(app as unknown as App)

    const error = new Error('render failed')
    app.config.errorHandler?.(error, { $options: { name: 'GeneTable' } }, 'render function')

    expect(logService.critical).toHaveBeenCalledWith('Uncaught Vue error', {
      error: 'render failed',
      stack: error.stack,
      component: 'GeneTable',
      info: 'render function'
    })
  })

  it('names unknown components as Unknown in error and warning reports', () => {
    const app = makeApp({ id: 'pinia' })
    loggerPlugin.install(app as unknown as App)

    app.config.errorHandler?.(new Error('x'), null, 'setup')
    expect(logService.critical).toHaveBeenCalledWith(
      'Uncaught Vue error',
      expect.objectContaining({ component: 'Unknown' })
    )

    app.config.warnHandler?.('Invalid prop', null, 'trace')
    expect(logService.warn).toHaveBeenCalledWith('Vue warning', {
      message: 'Invalid prop',
      component: 'Unknown',
      trace: 'trace'
    })
  })

  it('takes the component name from the instance type when options carry none', () => {
    const app = makeApp({ id: 'pinia' })
    loggerPlugin.install(app as unknown as App)

    app.config.warnHandler?.('w', { $: { type: { name: 'ScopeCard' } } }, 't')

    expect(logService.warn).toHaveBeenCalledWith(
      'Vue warning',
      expect.objectContaining({ component: 'ScopeCard' })
    )
  })

  it('installs the development warning handler', () => {
    const app = makeApp({ id: 'pinia' })
    loggerPlugin.install(app as unknown as App)

    expect(app.config.warnHandler).toBeTypeOf('function')
  })
})
