import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createApp } from 'vue'
import { createPinia, defineStore, setActivePinia } from 'pinia'
import { piniaErrorHandlerPlugin } from '../piniaErrorHandler'
import { logService } from '@/services/logService'

vi.mock('@/services/logService', () => ({
  logService: { warn: vi.fn(), error: vi.fn(), info: vi.fn(), debug: vi.fn() }
}))

const useProbeStore = defineStore('probe', {
  actions: {
    ok(): number {
      return 1
    },
    fail(error: unknown): never {
      throw error
    }
  }
})

describe('piniaErrorHandlerPlugin', () => {
  let store: ReturnType<typeof useProbeStore>

  beforeEach(() => {
    vi.clearAllMocks()
    const pinia = createPinia()
    pinia.use(piniaErrorHandlerPlugin)
    // Pinia only applies plugins once the instance is installed on an app
    createApp({}).use(pinia)
    setActivePinia(pinia)
    store = useProbeStore()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('logs slow successful actions as warnings', () => {
    vi.spyOn(Date, 'now').mockReturnValueOnce(0).mockReturnValueOnce(2500)

    expect(store.ok()).toBe(1)

    expect(logService.warn).toHaveBeenCalledWith('Slow action: probe.ok', {
      store: 'probe',
      action: 'ok',
      duration_ms: 2500
    })
  })

  it('does not warn for fast successful actions', () => {
    store.ok()

    expect(logService.warn).not.toHaveBeenCalled()
  })

  it('logs failed actions with status and message, not the payload', () => {
    const error = Object.assign(new Error('boom'), { response: { status: 409 } })

    expect(() => store.fail(error)).toThrow(error)

    expect(logService.error).toHaveBeenCalledWith('Store action failed: probe.fail', {
      store: 'probe',
      action: 'fail',
      error_message: 'boom',
      status: 409,
      duration_ms: expect.any(Number),
      args_count: 1
    })
  })

  it('does not swallow the original error', () => {
    const error = new Error('still thrown')

    expect(() => store.fail(error)).toThrow('still thrown')
  })
})
