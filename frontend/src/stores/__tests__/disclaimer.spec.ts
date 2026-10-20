import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useDisclaimerStore } from '@/stores/disclaimer'
import { logService } from '@/services/logService'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

/** happy-dom ignores prototype spies on localStorage, so the global is stubbed instead. */
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

const KEY = 'geneCuratorDisclaimerAcknowledged'
const TIMESTAMP_KEY = 'geneCuratorDisclaimerTimestamp'
const VERSION_KEY = 'geneCuratorDisclaimerVersion'

describe('useDisclaimerStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
  })

  it('starts unacknowledged and shows the disclaimer', () => {
    const store = useDisclaimerStore()
    expect(store.isAcknowledged).toBe(false)
    expect(store.shouldShowDisclaimer).toBe(true)
    expect(store.isCurrentVersionAcknowledged).toBe(false)
    expect(store.formattedAcknowledgmentDate).toBe('')
  })

  describe('initialize', () => {
    it('loads a saved acknowledgment of the current version', () => {
      localStorage.setItem(KEY, 'true')
      localStorage.setItem(TIMESTAMP_KEY, '1700000000000')
      localStorage.setItem(VERSION_KEY, '1.0.0')
      const store = useDisclaimerStore()

      store.initialize()

      expect(store.isAcknowledged).toBe(true)
      expect(store.acknowledgmentTimestamp).toBe(1700000000000)
      expect(store.disclaimerVersion).toBe('1.0.0')
      expect(store.isCurrentVersionAcknowledged).toBe(true)
      expect(store.shouldShowDisclaimer).toBe(false)
      expect(logService.debug).toHaveBeenCalledWith(
        'Disclaimer store initialized',
        expect.objectContaining({ isAcknowledged: true })
      )
    })

    it('shows the disclaimer again when the stored version is outdated', () => {
      localStorage.setItem(KEY, 'true')
      localStorage.setItem(VERSION_KEY, '0.9.0')
      const store = useDisclaimerStore()

      store.initialize()

      expect(store.isAcknowledged).toBe(true)
      expect(store.isCurrentVersionAcknowledged).toBe(false)
      expect(store.shouldShowDisclaimer).toBe(true)
      expect(logService.info).toHaveBeenCalledWith(
        'Disclaimer version mismatch, will show updated disclaimer',
        expect.objectContaining({ oldVersion: '0.9.0' })
      )
    })

    it('treats missing or non-true values as not acknowledged', () => {
      localStorage.setItem(KEY, 'false')
      const store = useDisclaimerStore()

      store.initialize()

      expect(store.isAcknowledged).toBe(false)
      expect(store.acknowledgmentTimestamp).toBeNull()
      expect(store.disclaimerVersion).toBeNull()
    })

    it('falls back to unacknowledged when localStorage throws', () => {
      const store = useDisclaimerStore()
      store.isAcknowledged = true
      stubFailingStorage('getItem', 'blocked')

      store.initialize()

      expect(store.isAcknowledged).toBe(false)
      expect(store.acknowledgmentTimestamp).toBeNull()
      expect(logService.error).toHaveBeenCalledWith(
        'Error loading disclaimer status from localStorage',
        expect.objectContaining({ error: 'blocked' })
      )
    })
  })

  describe('saveAcknowledgment', () => {
    it('persists acknowledgment, version and timestamp', () => {
      vi.spyOn(Date, 'now').mockReturnValue(1700000000000)
      const store = useDisclaimerStore()

      store.saveAcknowledgment()

      expect(localStorage.getItem(KEY)).toBe('true')
      expect(localStorage.getItem(TIMESTAMP_KEY)).toBe('1700000000000')
      expect(localStorage.getItem(VERSION_KEY)).toBe('1.0.0')
      expect(store.isAcknowledged).toBe(true)
      expect(store.acknowledgmentTimestamp).toBe(1700000000000)
      expect(store.disclaimerVersion).toBe('1.0.0')
      expect(store.formattedAcknowledgmentDate).not.toBe('')
    })

    it('logs and keeps state when storage fails', () => {
      const store = useDisclaimerStore()
      stubFailingStorage('setItem', 'quota')

      store.saveAcknowledgment()

      expect(store.isAcknowledged).toBe(false)
      expect(logService.error).toHaveBeenCalledWith(
        'Error saving disclaimer acknowledgment',
        expect.objectContaining({ error: 'quota' })
      )
    })
  })

  describe('resetAcknowledgment', () => {
    it('clears storage and state', () => {
      const store = useDisclaimerStore()
      store.saveAcknowledgment()

      store.resetAcknowledgment()

      expect(localStorage.getItem(KEY)).toBeNull()
      expect(localStorage.getItem(TIMESTAMP_KEY)).toBeNull()
      expect(localStorage.getItem(VERSION_KEY)).toBeNull()
      expect(store.isAcknowledged).toBe(false)
      expect(store.acknowledgmentTimestamp).toBeNull()
      expect(store.disclaimerVersion).toBeNull()
    })

    it('logs an error when storage removal fails', () => {
      const store = useDisclaimerStore()
      stubFailingStorage('removeItem', 'locked')

      store.resetAcknowledgment()

      expect(logService.error).toHaveBeenCalledWith(
        'Error resetting disclaimer acknowledgment',
        expect.objectContaining({ error: 'locked' })
      )
    })
  })

  describe('formattedAcknowledgmentDate', () => {
    it('formats the stored timestamp', () => {
      const store = useDisclaimerStore()
      store.acknowledgmentTimestamp = Date.UTC(2025, 0, 15, 12, 0)
      expect(store.formattedAcknowledgmentDate).toMatch(/2025/)
    })

    it('returns an empty string and logs when formatting throws', () => {
      const store = useDisclaimerStore()
      store.acknowledgmentTimestamp = 1
      vi.spyOn(Date.prototype, 'toLocaleDateString').mockImplementation(() => {
        throw new Error('bad locale')
      })

      expect(store.formattedAcknowledgmentDate).toBe('')
      expect(logService.error).toHaveBeenCalledWith(
        'Error formatting acknowledgment date',
        expect.objectContaining({ error: 'bad locale' })
      )
    })
  })

  describe('manual dialog flag', () => {
    it('shows and resets the manual display flag', () => {
      const store = useDisclaimerStore()
      store.showDisclaimerDialog()
      expect(store.showManually).toBe(true)

      store.resetShowManually()
      expect(store.showManually).toBe(false)
    })
  })
})
