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
import { createPinia, setActivePinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'

vi.mock('@/services/logService', () => ({
  logService: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }
}))

const KEY = 'form_recovery_anon_test-form'

/**
 * Mount a host component so the composable's lifecycle hooks run. The form's current data is the
 * server copy loaded at `version` (null: a new record; false: still loading).
 */
function mountRecovery<T extends object>(
  formData: Ref<T>,
  options: FormRecoveryOptions = {},
  version: string | null | false = null
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
  if (version !== false) api.setBaseline(JSON.parse(JSON.stringify(formData.value)), version)
  return { wrapper, api }
}

const saved = (data: unknown, ageMs = 0, baseVersion?: string | null) =>
  JSON.stringify({
    data,
    timestamp: new Date(Date.now() - ageMs).toISOString(),
    url: 'http://localhost/',
    formId: 'test-form',
    baseVersion
  })
const stored = () => JSON.parse(localStorage.getItem(KEY) ?? 'null')

describe('useFormRecovery', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
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
    const { api } = mountRecovery(form)

    await vi.advanceTimersByTimeAsync(10_000)
    expect(localStorage.getItem(KEY)).toBeNull()

    form.value.gene = 'TP53'
    await nextTick()

    const stored = JSON.parse(localStorage.getItem(KEY) ?? 'null')
    expect(stored.data).toEqual({ gene: 'TP53' })
    expect(api.lastSaved.value).toBe(stored.timestamp)
  })

  it('manual discard: forgets the offered draft and protects edits made right after it', async () => {
    localStorage.setItem(KEY, saved({ gene: 'mine' }, 1000))
    const form = ref({ gene: 'X1' })
    const { api } = mountRecovery(form)

    api.discardRecovery()
    expect(localStorage.getItem(KEY)).toBeNull()

    form.value.gene = 'changed'
    await nextTick()
    expect(stored().data).toEqual({ gene: 'changed' })
  })

  it('restoreRecovery replaces the form with stored data and hides the dialog', () => {
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

  it('keys drafts by user so another account never sees them, and sign-out wipes them', () => {
    const auth = useAuthStore()
    auth.user = { id: 'user-1' } as typeof auth.user
    localStorage.setItem('form_recovery_user-1_test-form', saved({ gene: 'A' }))

    const mine = mountRecovery(ref({ gene: '' }))
    expect(mine.api.showRecoveryDialog.value).toBe(true)

    auth.user = { id: 'user-2' } as typeof auth.user
    const theirs = mountRecovery(ref({ gene: '' }))
    expect(theirs.api.showRecoveryDialog.value).toBe(false)

    auth.clearAuth()
    expect(localStorage.getItem('form_recovery_user-1_test-form')).toBeNull()
  })

  describe('against the server copy (#436)', () => {
    it('stores nothing before the server copy is loaded, nor the unedited server copy', async () => {
      const form = ref<Record<string, unknown>>({})
      const { api } = mountRecovery(form, {}, false)

      form.value = { a: 'server' } // the load
      await vi.advanceTimersByTimeAsync(1000)
      expect(localStorage.getItem(KEY)).toBeNull()

      api.setBaseline({ a: 'server' }, 'v1')
      await vi.advanceTimersByTimeAsync(1000)
      expect(localStorage.getItem(KEY)).toBeNull()
    })

    it('offers a stored draft only once the server copy is loaded', () => {
      localStorage.setItem(KEY, saved({ a: 'mine' }, 1000, 'v1'))
      const { api } = mountRecovery(ref({ a: 'server' }), {}, false)
      expect(api.showRecoveryDialog.value).toBe(false)

      api.setBaseline({ a: 'server' }, 'v1')

      expect(api.showRecoveryDialog.value).toBe(true)
      expect(api.recoveryStale.value).toBe(false)
    })

    it('draft saved, server copy updated, reopen: flags the newer server copy, restores nothing', async () => {
      const form = ref<Record<string, unknown>>({ a: 'server v1' })
      const first = mountRecovery(form, {}, 'v1')
      form.value = { a: 'my edit' }
      await nextTick()
      expect(stored()).toMatchObject({ data: { a: 'my edit' }, baseVersion: 'v1' })
      first.wrapper.unmount()

      // Another tab or user saves v2, then the form reopens
      const reopened = ref<Record<string, unknown>>({ a: 'their edit' })
      const { api } = mountRecovery(reopened, {}, 'v2')

      expect(api.showRecoveryDialog.value).toBe(true)
      expect(api.recoveryStale.value).toBe(true)
      expect(reopened.value).toEqual({ a: 'their edit' })
    })

    it('drops a draft the server already has (same data, newer version, key order aside)', () => {
      localStorage.setItem(KEY, saved({ a: 1, b: { c: 2, d: 3 } }, 1000, 'v1'))
      const { api } = mountRecovery(ref({ b: { d: 3, c: 2 }, a: 1 }), {}, 'v2')

      expect(api.showRecoveryDialog.value).toBe(false)
      expect(localStorage.getItem(KEY)).toBeNull()
    })

    it('keeps the stored draft while the prompt is open', async () => {
      localStorage.setItem(KEY, saved({ a: 'mine' }, 1000, 'v1'))
      mountRecovery(ref({ a: 'server' }), {}, 'v1')

      await vi.advanceTimersByTimeAsync(10_000)

      expect(stored().data).toEqual({ a: 'mine' })
    })

    it('re-checks an open prompt when the server copy changes after it', () => {
      localStorage.setItem(KEY, saved({ a: 'mine' }, 1000, 'v1'))
      const { api } = mountRecovery(ref({ a: 'server' }), {}, 'v1')
      expect(api.recoveryStale.value).toBe(false)

      api.setBaseline({ a: 'newer' }, 'v2')
      expect(api.showRecoveryDialog.value).toBe(true)
      expect(api.recoveryStale.value).toBe(true)

      api.setBaseline({ a: 'mine' }, 'v3')
      expect(api.showRecoveryDialog.value).toBe(false)
      expect(api.recoveryData.value).toBeNull()
      expect(localStorage.getItem(KEY)).toBeNull()
    })

    it('new forms: a draft of an unsaved record is current, a draft without a version is not', () => {
      localStorage.setItem(KEY, saved({ a: 'mine' }, 1000, null))
      expect(mountRecovery(ref({}), {}, null).api.recoveryStale.value).toBe(false)

      localStorage.setItem(KEY, saved({ a: 'mine' }, 1000)) // stored before drafts had a version
      expect(mountRecovery(ref({ a: 'server' }), {}, 'v1').api.recoveryStale.value).toBe(true)
    })

    it('ignores key order and forgets the draft when edits are reverted', async () => {
      const form = ref<Record<string, unknown>>({ a: 1, b: 2 })
      mountRecovery(form, {}, 'v1')

      form.value = { b: 2, a: 1 }
      await nextTick()
      expect(localStorage.getItem(KEY)).toBeNull()

      form.value = { a: 9, b: 2 }
      await nextTick()
      expect(stored().data).toEqual({ a: 9, b: 2 })

      form.value = { a: 1, b: 2 }
      await nextTick()
      expect(localStorage.getItem(KEY)).toBeNull()
    })

    it('deleted fields: a deletion is a local edit and restore keeps the field deleted', async () => {
      const form = ref<Record<string, unknown>>({ a: 1, b: 2 })
      const first = mountRecovery(form, {}, 'v1')
      form.value = { a: 1 }
      await nextTick()
      first.wrapper.unmount()

      const reopened = ref<Record<string, unknown>>({ a: 1, b: 2 })
      const before = reopened.value
      const { api } = mountRecovery(reopened, {}, 'v1')
      api.restoreRecovery()

      expect(reopened.value).toEqual({ a: 1 })
      expect(reopened.value).not.toBe(before) // a new reference reaches reference watchers
    })
  })

  describe('across tabs and saves (#436 review)', () => {
    type Form = Ref<Record<string, unknown>>
    const tab = (data: Record<string, unknown>, version: string | null = 'v1') => {
      const form: Form = ref({ ...data })
      return { form, ...mountRecovery(form, {}, version) }
    }

    it('an idle tab never deletes the draft another tab wrote', async () => {
      const a = tab({ a: 1 })
      const b = tab({ a: 1 })

      b.form.value = { a: 2 }
      await nextTick()
      b.wrapper.unmount() // tab B crashes; tab A stays open, untouched
      await vi.advanceTimersByTimeAsync(60_000)

      expect(stored().data).toEqual({ a: 2 })
      a.wrapper.unmount()
    })

    it("both tabs wrote, one reverted: the other tab's newer draft stays", async () => {
      const a = tab({ a: 1 })
      const b = tab({ a: 1 })
      a.form.value = { a: 'A' }
      await nextTick()
      b.form.value = { a: 'B' }
      await nextTick()

      a.form.value = { a: 1 }
      await nextTick()
      a.form.value = {}
      await nextTick()

      expect(stored().data).toEqual({ a: 'B' })
    })

    it('submit or cancel in one tab keeps the draft of another', async () => {
      const a = tab({ a: 1 })
      const b = tab({ a: 1 })
      b.form.value = { a: 2 }
      await nextTick()

      a.api.clearRecovery()

      expect(stored().data).toEqual({ a: 2 })
    })

    it('manual discard keeps a newer draft another tab wrote after the offer', async () => {
      localStorage.setItem(KEY, saved({ a: 'mine' }, 1000, 'v1'))
      const a = tab({ a: 1 })
      const b = tab({ a: 1 })
      b.api.restoreRecovery()
      b.form.value = { a: 'mine, more' }
      await nextTick()

      a.api.discardRecovery()

      expect(stored().data).toEqual({ a: 'mine, more' })
    })

    it('emptying an edited field forgets the draft, so older text is never offered', async () => {
      const first = tab({ a: 'server' })
      first.form.value = { a: 'abc' }
      await nextTick()
      first.form.value = { a: '' }
      await nextTick()
      expect(localStorage.getItem(KEY)).toBeNull()
      first.wrapper.unmount()

      expect(tab({ a: 'server' }).api.showRecoveryDialog.value).toBe(false)
    })

    it('emptying a new form forgets its draft', async () => {
      const { form } = tab({}, null)
      form.value = { a: 'abc' }
      await nextTick()
      form.value = { a: '  ' }
      await nextTick()

      expect(localStorage.getItem(KEY)).toBeNull()
    })

    it('edit, save, edit, reload: the later edits are offered, bound to the saved version', async () => {
      const first = tab({ a: 1 })
      first.form.value = { a: 2 }
      await nextTick()

      first.api.markSaved({ a: 2 }, 'v2')
      expect(localStorage.getItem(KEY)).toBeNull()

      first.form.value = { a: 3 }
      await nextTick()
      expect(stored()).toMatchObject({ data: { a: 3 }, baseVersion: 'v2' })
      first.wrapper.unmount()

      const reopened = tab({ a: 2 }, 'v2')
      expect(reopened.api.showRecoveryDialog.value).toBe(true)
      expect(reopened.api.recoveryStale.value).toBe(false)
      expect(reopened.api.recoveryData.value).toEqual({ a: 3 })
    })

    it('edits made while the save was in flight stay stored, bound to the saved version', async () => {
      const { form, api } = tab({ a: 1 })
      form.value = { a: 2 }
      await nextTick()
      form.value = { a: 3 } // typed after the request left

      api.markSaved({ a: 2 }, 'v2')

      expect(stored()).toMatchObject({ data: { a: 3 }, baseVersion: 'v2' })
    })

    it('a late save cannot resurrect edits discarded while its request was in flight', async () => {
      const { form, api } = tab({ a: 1 })
      form.value = { a: 2 }
      await nextTick()
      form.value = { a: 3 } // typed after Save sent a:2
      await nextTick()
      expect(stored()).toMatchObject({ data: { a: 3 } })
      api.clearRecovery() // confirmed Cancel discards the newer local edits
      expect(localStorage.getItem(KEY)).toBeNull()

      api.markSaved({ a: 2 }, 'v2') // late response must respect the cancellation
      expect(localStorage.getItem(KEY)).toBeNull()
      form.value = { a: 4 }
      await nextTick()
      expect(localStorage.getItem(KEY)).toBeNull()
    })
  })
})
