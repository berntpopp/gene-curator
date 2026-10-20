import { describe, it, expect, vi, afterEach } from 'vitest'
import { generateUUID, isNativeUUIDAvailable } from '../uuidPolyfill'

const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/

describe('uuidPolyfill', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('uses crypto.randomUUID when the browser provides it', () => {
    const randomUUID = vi.fn(() => 'native-id')
    vi.stubGlobal('crypto', { randomUUID })

    expect(isNativeUUIDAvailable()).toBe(true)
    expect(generateUUID()).toBe('native-id')
    expect(randomUUID).toHaveBeenCalledTimes(1)
  })

  it('falls back to an RFC 4122 v4 generator when randomUUID is missing', () => {
    vi.stubGlobal('crypto', {})

    expect(isNativeUUIDAvailable()).toBe(false)
    const id = generateUUID()
    expect(id).toMatch(UUID_V4)
  })

  it('fallback ids differ between calls', () => {
    vi.stubGlobal('crypto', undefined)

    expect(generateUUID()).not.toBe(generateUUID())
  })

  it('reports native support as unavailable when crypto is undefined', () => {
    vi.stubGlobal('crypto', undefined)

    expect(isNativeUUIDAvailable()).toBe(false)
  })
})
