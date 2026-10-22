import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import SchemaDrivenCurationForm from '../SchemaDrivenCurationForm.vue'

const deferred = <T>() => {
  let resolve!: (v: T) => void
  const promise = new Promise<T>(r => (resolve = r))
  return { promise, resolve }
}

const h = vi.hoisted(() => ({
  schema: null as unknown,
  curation: null as unknown,
  precuration: null as unknown,
  setBaseline: vi.fn()
}))
const store = vi.hoisted(() => ({ currentCuration: null as unknown }))

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }))
vi.mock('@/stores/schemas', () => ({
  useSchemasStore: () => ({
    getSchemaById: (id: string) => ({ id, name: 'Panel' }),
    fetchSchemaById: vi.fn(),
    fetchPinnedVersion: () => h.schema
  })
}))
vi.mock('@/stores/curations', () => ({
  useCurationsStore: () => ({
    get currentCuration() {
      return store.currentCuration
    },
    fetchCurationById: () => h.curation
  })
}))
vi.mock('@/stores/precurations', () => ({
  usePrecurationsStore: () => ({ fetchPrecurationById: () => h.precuration })
}))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast: vi.fn() }) }))
vi.mock('@/composables/useFormRecovery', () => ({
  useFormRecovery: () => ({
    showRecoveryDialog: ref(false),
    recoveryData: ref(null),
    recoveryTimestamp: ref(null),
    lastSaved: ref(null),
    restoreRecovery: vi.fn(),
    discardRecovery: vi.fn(),
    recoveryStale: ref(false),
    setBaseline: h.setBaseline,
    clearRecovery: vi.fn()
  })
}))
vi.mock('@/composables/useHistory', () => ({
  useHistory: () => ({
    canUndo: ref(false),
    canRedo: ref(false),
    recordAction: vi.fn(),
    undo: vi.fn(),
    redo: vi.fn(),
    clearHistory: vi.fn()
  })
}))

const stubs = {
  ErrorBoundary: { template: '<div><slot /></div>' },
  DynamicForm: true,
  FormActions: true,
  FormRecoveryDialog: true
}

describe('SchemaDrivenCurationForm loading', () => {
  beforeEach(() => vi.clearAllMocks())

  it('shows only a skeleton until curation, precuration and pinned version have all loaded', async () => {
    const schema = deferred<unknown>()
    const curation = deferred<unknown>()
    const precuration = deferred<unknown>()
    h.schema = schema.promise
    h.curation = curation.promise
    h.precuration = precuration.promise
    // fetchCurationById resolves with a curation that links a precuration; the store keeps it current
    const loaded = {
      id: 'c1',
      status: 'draft',
      evidence_data: { panel: 'server' },
      precuration_id: 'p1',
      lock_version: 4,
      updated_at: '2026-10-01T10:00:00Z'
    }
    store.currentCuration = null

    const wrapper = mount(SchemaDrivenCurationForm, {
      props: { schemaId: 's1', scopeId: 'sc1', curationId: 'c1' },
      global: { stubs }
    })
    const form = () => wrapper.find('dynamic-form-stub').exists()
    const skeleton = () => wrapper.find('.v-skeleton-loader').exists()

    store.currentCuration = loaded
    curation.resolve(loaded)
    await flushPromises()
    expect(skeleton()).toBe(true)
    expect(form()).toBe(false)

    precuration.resolve({ evidence_data: {} })
    await flushPromises()
    expect(skeleton()).toBe(true)
    expect(form()).toBe(false)
    expect(h.setBaseline).not.toHaveBeenCalled() // no draft is offered before the server copy

    schema.resolve({ id: 'v1', snapshot: {} })
    await flushPromises()
    expect(skeleton()).toBe(false)
    expect(form()).toBe(true)
    expect(wrapper.emitted('ready')).toHaveLength(1)
    // Local drafts are compared with the loaded curation and bound to its version (#436)
    expect(h.setBaseline).toHaveBeenCalledExactlyOnceWith(
      { panel: 'server' },
      '4@2026-10-01T10:00:00Z'
    )
  })

  it('compares a new curation with its re-curation prefill, unversioned (#436)', async () => {
    h.schema = { id: 'v1', snapshot: {} }
    h.curation = { evidence_data: { panel: 'active' } }
    mount(SchemaDrivenCurationForm, {
      props: { schemaId: 's1', scopeId: 'sc1', prefillFrom: 'c0' },
      global: { stubs }
    })
    await flushPromises()

    expect(h.setBaseline).toHaveBeenCalledExactlyOnceWith({ panel: 'active' }, null)
  })

  it('offers no draft while the saved curation could not be loaded (#436)', async () => {
    h.schema = { id: 'v1', snapshot: {} }
    h.curation = Promise.reject(new Error('down'))
    store.currentCuration = null
    mount(SchemaDrivenCurationForm, {
      props: { schemaId: 's1', scopeId: 'sc1', curationId: 'c1' },
      global: { stubs }
    })
    await flushPromises()

    expect(h.setBaseline).not.toHaveBeenCalled()
  })
})
