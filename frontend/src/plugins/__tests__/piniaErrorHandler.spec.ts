import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { createApp } from 'vue'
import { createPinia, defineStore, setActivePinia } from 'pinia'
import {
  piniaErrorHandlerPlugin,
  getErrorMessage,
  isErrorCategory,
  ERROR_CATEGORIES,
  type HttpLikeError
} from '../piniaErrorHandler'
import { logService } from '@/services/logService'
import pluginDefault from '../piniaErrorHandler'

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

function httpError(
  message: string,
  response?: HttpLikeError['response'],
  code?: string
): HttpLikeError {
  const error: HttpLikeError = Object.assign(new Error(message), { response, code })
  return error
}

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

  it.each([
    [
      'network failures',
      httpError('Network Error', undefined, 'ERR_NETWORK'),
      ERROR_CATEGORIES.NETWORK,
      'Unable to connect to the server. Please check your connection.'
    ],
    [
      '401 responses',
      httpError('unauthorized', { status: 401 }),
      ERROR_CATEGORIES.AUTH,
      'You are not authorized to perform this action.'
    ],
    [
      '403 responses',
      httpError('forbidden', { status: 403 }),
      ERROR_CATEGORIES.AUTH,
      'You are not authorized to perform this action.'
    ],
    [
      '404 responses',
      httpError('missing', { status: 404 }),
      ERROR_CATEGORIES.NOT_FOUND,
      'The requested resource was not found.'
    ],
    [
      'validation detail arrays',
      httpError('bad', { status: 422, data: { detail: [{ msg: 'Symbol is required' }] } }),
      ERROR_CATEGORIES.VALIDATION,
      'Symbol is required'
    ],
    [
      'other 4xx responses with a message',
      httpError('bad', { status: 400, data: { message: 'Scope is archived' } }),
      ERROR_CATEGORIES.VALIDATION,
      'Scope is archived'
    ],
    [
      'other 4xx responses without detail',
      httpError('bad', { status: 409 }),
      ERROR_CATEGORIES.VALIDATION,
      'Please check your input and try again.'
    ],
    [
      'server errors',
      httpError('boom', { status: 500 }),
      ERROR_CATEGORIES.UNKNOWN,
      'An unexpected error occurred. Please try again.'
    ],
    [
      'plain errors',
      new Error('plain'),
      ERROR_CATEGORIES.UNKNOWN,
      'An unexpected error occurred. Please try again.'
    ]
  ])('categorises %s and attaches context', (_label, error, category, userMessage) => {
    expect(() => store.fail(error)).toThrow(error)

    expect((error as HttpLikeError)._piniaContext).toEqual({
      store: 'probe',
      action: 'fail',
      category,
      userMessage,
      duration: expect.any(Number)
    })
    expect(logService.error).toHaveBeenCalledWith(
      'Store action failed: probe.fail',
      expect.objectContaining({ store: 'probe', action: 'fail', category })
    )
  })

  it('does not swallow the original error', () => {
    const error = new Error('still thrown')

    expect(() => store.fail(error)).toThrow('still thrown')
  })
})

describe('error helpers', () => {
  it('getErrorMessage prefers the attached user message', () => {
    const error = Object.assign(httpError('x', { status: 500 }), {
      _piniaContext: {
        store: 's',
        action: 'a',
        category: 'unknown',
        userMessage: 'Friendly',
        duration: 1
      }
    })

    expect(getErrorMessage(error)).toBe('Friendly')
  })

  it('getErrorMessage falls back to response message, string detail, message, then default', () => {
    expect(getErrorMessage(httpError('x', { data: { message: 'From body' } }))).toBe('From body')
    expect(getErrorMessage(httpError('x', { data: { detail: 'From detail' } }))).toBe('From detail')
    expect(getErrorMessage(new Error('Plain message'))).toBe('Plain message')
    expect(getErrorMessage(new Error(''))).toBe('An unexpected error occurred')
  })

  it('isErrorCategory compares against the attached category only', () => {
    const tagged = Object.assign(new Error('x'), {
      _piniaContext: { category: 'auth' }
    })

    expect(isErrorCategory(tagged, 'auth')).toBe(true)
    expect(isErrorCategory(tagged, 'network')).toBe(false)
    expect(isErrorCategory(new Error('untagged'), 'auth')).toBe(false)
  })

  it('default export exposes the same helpers', () => {
    expect(pluginDefault.piniaErrorHandlerPlugin).toBe(piniaErrorHandlerPlugin)
    expect(pluginDefault.getErrorMessage).toBe(getErrorMessage)
    expect(pluginDefault.isErrorCategory).toBe(isErrorCategory)
    expect(pluginDefault.ERROR_CATEGORIES).toBe(ERROR_CATEGORIES)
  })
})
