import { describe, it, expect, vi } from 'vitest'
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
  precuration: null as unknown
}))
const store = vi.hoisted(() => ({ currentCuration: null as unknown }))

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('vue-router', () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }) }))
vi.mock('@/stores/schemas', () => ({
  useSchemasStore: () => ({
    getSchemaById: (id: string) => ({ id, name: 'Panel', use_dynamic_form: false }),
    fetchSchemaById: () => h.schema
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
vi.mock('@/stores/validation', () => ({
  useValidationStore: () => ({ generateJsonSchema: vi.fn() })
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

describe('SchemaDrivenCurationForm loading', () => {
  it('shows only a skeleton until schema, curation and precuration have all loaded', async () => {
    const schema = deferred<void>()
    const curation = deferred<unknown>()
    const precuration = deferred<unknown>()
    h.schema = schema.promise
    h.curation = curation.promise
    h.precuration = precuration.promise
    // fetchCurationById resolves with a curation that links a precuration; the store keeps it current
    const loaded = { id: 'c1', status: 'draft', evidence_data: {}, precuration_id: 'p1' }
    store.currentCuration = null

    const wrapper = mount(SchemaDrivenCurationForm, {
      props: { schemaId: 's1', scopeId: 'sc1', curationId: 'c1' },
      global: {
        stubs: {
          ErrorBoundary: { template: '<div><slot /></div>' },
          ClinGenCurationForm: true,
          DynamicForm: true,
          FormActions: true,
          ScorePreview: true,
          FormRecoveryDialog: true
        }
      }
    })
    const form = () => wrapper.find('clin-gen-curation-form-stub').exists()
    const skeleton = () => wrapper.find('.v-skeleton-loader').exists()

    schema.resolve()
    await flushPromises()
    expect(skeleton()).toBe(true)
    expect(form()).toBe(false)

    store.currentCuration = loaded
    curation.resolve(loaded)
    await flushPromises()
    expect(skeleton()).toBe(true)
    expect(form()).toBe(false)

    precuration.resolve({ evidence_data: {} })
    await flushPromises()
    expect(skeleton()).toBe(false)
    expect(form()).toBe(true)
    expect(wrapper.emitted('ready')).toHaveLength(1)
  })
})
