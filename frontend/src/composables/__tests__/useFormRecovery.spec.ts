import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { defineComponent, h, nextTick, ref } from 'vue'
import type { Ref } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import {
  useFormRecovery,
  type FormRecoveryOptions,
  type UseFormRecoveryReturn
} from '../useFormRecovery'
import { logService } from '@/services/logService'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const KEY = 'form_recovery_test-form'

/** Mount a host component so the composable's lifecycle hooks run. */
function mountRecovery<T extends object>(
  formData: Ref<T>,
  options: FormRecoveryOptions = {}
): { wrapper: VueWrapper; api: UseFormRecoveryReturn } {
  let api: UseFormRecoveryReturn | undefined
  const wrapper = mount(
    defineComponent({
      setup() {
        api = useFormRecovery('test-form', formData, options)
        return () => h('div')
      }
    })
  )
  if (!api) throw new Error('composable not initialised')
  return { wrapper, api }
}

const saved = (data: unknown, ageMs = 0) =>
  JSON.stringify({
    data,
    timestamp: new Date(Date.now() - ageMs).toISOString(),
    url: 'http://localhost/',
    formId: 'test-form'
  })

describe('useFormRecovery', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.clearAllMocks()
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-06-01T12:00:00Z'))
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('shows no recovery dialog when nothing is stored', () => {
    const { api } = mountRecovery(ref({ gene: '' }))

    expect(api.showRecoveryDialog.value).toBe(false)
    expect(api.recoveryData.value).toBeNull()
  })

  it('offers recovery when recent, non-empty data is stored', () => {
    localStorage.setItem(KEY, saved({ gene: 'BRCA1' }, 60_000))
    const { api } = mountRecovery(ref({ gene: '' }))

    expect(api.showRecoveryDialog.value).toBe(true)
    expect(api.recoveryData.value).toEqual({ gene: 'BRCA1' })
    expect(api.recoveryTimestamp.value).toEqual(expect.any(String))
  })

  it('removes stored data that is empty or older than maxAge', () => {
    localStorage.setItem(KEY, saved({ gene: '  ' }))
    mountRecovery(ref({ gene: '' }))
    expect(localStorage.getItem(KEY)).toBeNull()

    localStorage.setItem(KEY, saved({ gene: 'OLD' }, 2_000))
    const { api } = mountRecovery(ref({ gene: '' }), { maxAge: 1_000 })
    expect(api.showRecoveryDialog.value).toBe(false)
    expect(localStorage.getItem(KEY)).toBeNull()
  })

  it('logs an error for corrupt stored data', () => {
    localStorage.setItem(KEY, '{not json')
    const { api } = mountRecovery(ref({ gene: '' }))

    expect(api.showRecoveryDialog.value).toBe(false)
    expect(logService.error).toHaveBeenCalledWith(
      'Failed to check recovery data',
      expect.objectContaining({ formId: 'test-form' })
    )
  })

  it('auto-saves meaningful form data and skips empty forms', async () => {
    const form = ref({ gene: '' })
    const { api } = mountRecovery(form, { saveInterval: 1000 })

    await vi.advanceTimersByTimeAsync(1000)
    expect(localStorage.getItem(KEY)).toBeNull()

    form.value.gene = 'TP53'
    await nextTick()

    const stored = JSON.parse(localStorage.getItem(KEY) ?? 'null')
    expect(stored.data).toEqual({ gene: 'TP53' })
    expect(api.lastSaved.value).toBe(stored.timestamp)
  })

  it('does not save while paused after discard', async () => {
    const form = ref({ gene: 'X1' })
    const { api } = mountRecovery(form, { saveInterval: 1000 })

    api.discardRecovery()
    form.value.gene = 'changed'
    await nextTick()
    expect(localStorage.getItem(KEY)).toBeNull()

    // Pause lifts after the 10 second grace period
    await vi.advanceTimersByTimeAsync(10_000)
    await vi.advanceTimersByTimeAsync(1000)
    expect(localStorage.getItem(KEY)).not.toBeNull()
  })

  it('restoreRecovery merges stored data into the form and hides the dialog', () => {
    localStorage.setItem(KEY, saved({ gene: 'BRCA2', rationale: 'r' }, 1000))
    const form = ref<{ gene: string; rationale?: string }>({ gene: '' })
    const { api } = mountRecovery(form)

    api.restoreRecovery()

    expect(form.value).toEqual({ gene: 'BRCA2', rationale: 'r' })
    expect(api.showRecoveryDialog.value).toBe(false)
  })

  it('restoreRecovery does nothing without recovery data', () => {
    const form = ref({ gene: '' })
    const { api } = mountRecovery(form)

    api.restoreRecovery()

    expect(form.value).toEqual({ gene: '' })
  })

  it('discardRecovery removes stored data and clears recovery state', () => {
    localStorage.setItem(KEY, saved({ gene: 'BRCA2' }, 1000))
    const { api } = mountRecovery(ref({ gene: '' }))

    api.discardRecovery()

    expect(localStorage.getItem(KEY)).toBeNull()
    expect(api.recoveryData.value).toBeNull()
    expect(api.recoveryTimestamp.value).toBeNull()
    expect(api.showRecoveryDialog.value).toBe(false)
  })

  it('clearRecovery removes stored data and resets lastSaved', async () => {
    const form = ref({ gene: 'A' })
    const { api } = mountRecovery(form)
    form.value.gene = 'B'
    await nextTick()
    expect(api.lastSaved.value).not.toBeNull()

    api.clearRecovery()

    expect(localStorage.getItem(KEY)).toBeNull()
    expect(api.lastSaved.value).toBeNull()
  })

  it('resumeAutoSave lifts the pause immediately', async () => {
    const form = ref({ gene: 'A' })
    const { api } = mountRecovery(form)
    api.clearRecovery() // pauses auto-save

    form.value.gene = 'C'
    await nextTick()
    expect(localStorage.getItem(KEY)).toBeNull()

    api.resumeAutoSave()
    form.value.gene = 'D'
    await nextTick()
    expect(localStorage.getItem(KEY)).not.toBeNull()
  })

  it('reports storage write failures without throwing', async () => {
    const setItem = vi.spyOn(localStorage, 'setItem').mockImplementation(() => {
      throw new Error('quota exceeded')
    })
    const form = ref({ gene: 'A' })
    mountRecovery(form)

    form.value.gene = 'B'
    await nextTick()

    expect(logService.error).toHaveBeenCalledWith(
      'Failed to save form',
      expect.objectContaining({ error: 'quota exceeded' })
    )
    setItem.mockRestore()
  })

  it('stops the auto-save timer on unmount', async () => {
    const clearSpy = vi.spyOn(globalThis, 'clearInterval')
    const form = ref({ gene: 'A' })
    const { wrapper } = mountRecovery(form)

    wrapper.unmount()

    expect(clearSpy).toHaveBeenCalled()
    clearSpy.mockRestore()
  })
})
