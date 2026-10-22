// Submitting a new curation moves /new -> its edit page while the form is dirty: never a leave prompt
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent, h, ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory, RouterView, type Router } from 'vue-router'
import { useCurationSubmission } from '../useCurationSubmission'
import { useUnsavedGuard } from '@/components/workspace/useUnsavedGuard'

const confirm = vi.hoisted(() => vi.fn())
const curationsStore = vi.hoisted(() => ({
  createCuration: vi.fn(),
  submitCuration: vi.fn(),
  error: null
}))
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm }) }))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('@/stores/curations', () => ({ useCurationsStore: () => curationsStore }))
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast: vi.fn() }) }))

let api: ReturnType<typeof useCurationSubmission>
let mounts = 0
const evidence = ref<Record<string, unknown>>({})

// Stands in for CurationFormView: one component on both routes, dirty until submitted
const Host = defineComponent({
  setup() {
    mounts++
    const dirty = ref(true)
    useUnsavedGuard(dirty)
    api = useCurationSubmission({
      curationId: () => (routerRef.currentRoute.value.params.curationId as string) || undefined,
      geneId: () => 'gene-1',
      scopeId: () => 's1',
      workflowPairId: () => 'wp-1',
      evidenceData: evidence,
      lockVersion: ref(0),
      canSubmit: () => true,
      clearRecovery: vi.fn(),
      markSaved: vi.fn(),
      clearHistory: vi.fn(),
      onSaved: vi.fn(),
      onSubmit: id => {
        dirty.value = false
        routerRef.push({ name: 'curation-detail', params: { scopeId: 's1', curationId: id } })
      }
    })
    return () => h('div')
  }
})

// The real split: the form owns the submission and emits `submit`; the view navigates
const Form = defineComponent({
  emits: ['submit'],
  setup(_, { emit }) {
    api = useCurationSubmission({
      curationId: () => (routerRef.currentRoute.value.params.curationId as string) || undefined,
      geneId: () => 'gene-1',
      scopeId: () => 's1',
      workflowPairId: () => 'wp-1',
      evidenceData: evidence,
      lockVersion: ref(0),
      canSubmit: () => true,
      clearRecovery: vi.fn(),
      markSaved: vi.fn(),
      clearHistory: vi.fn(),
      onSaved: vi.fn(),
      onSubmit: id => emit('submit', id)
    })
    return () => h('div')
  }
})
const View = defineComponent({
  setup() {
    const dirty = ref(true)
    useUnsavedGuard(dirty)
    return () =>
      h(Form, {
        onSubmit: (id: string) => {
          dirty.value = false
          routerRef.push({ name: 'curation-detail', params: { scopeId: 's1', curationId: id } })
        }
      })
  }
})

let routerRef: Router

async function setup(component = Host, keyed = false) {
  routerRef = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/scopes/:scopeId/genes/:geneId/curation/new', component },
      {
        path: '/scopes/:scopeId/curations/:curationId/edit',
        name: 'curation-edit',
        component
      },
      { path: '/scopes/:scopeId/curations/:curationId', name: 'curation-detail', component }
    ]
  })
  await routerRef.push('/scopes/s1/genes/gene-1/curation/new')
  // App.vue keys the routed view by fullPath, so any URL change remounts it
  const Keyed = () =>
    h(RouterView, null, {
      default: ({ Component, route }: { Component: unknown; route: { fullPath: string } }) =>
        h(Component as never, { key: route.fullPath })
    })
  mount(keyed ? Keyed : RouterView, { global: { plugins: [routerRef] } })
  await flushPromises()
}

describe('submitting a new curation and the leave guard', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    mounts = 0
    evidence.value = { disease: 'typed but not saved' }
    curationsStore.createCuration.mockResolvedValue({ id: 'c-new', lock_version: 0 })
  })

  it('opens the detail page after a successful submit without a prompt', async () => {
    curationsStore.submitCuration.mockResolvedValue({ lock_version: 1 })
    await setup()

    await api.handleSubmit()
    await flushPromises()

    expect(confirm).not.toHaveBeenCalled()
    expect(routerRef.currentRoute.value.fullPath).toBe('/scopes/s1/curations/c-new')
  })

  it('moves to the edit page of the created curation when submit is refused, keeps the form, retries on it', async () => {
    curationsStore.submitCuration.mockRejectedValueOnce(new Error('422'))
    await setup()

    await api.handleSubmit()
    await flushPromises()

    expect(confirm).not.toHaveBeenCalled()
    expect(routerRef.currentRoute.value.fullPath).toBe('/scopes/s1/curations/c-new/edit')
    expect(mounts).toBe(1) // same form instance: what the user typed is still there
    expect(evidence.value).toEqual({ disease: 'typed but not saved' })

    // The bypass is one navigation only: really leaving the dirty form still asks
    confirm.mockResolvedValue(false)
    await routerRef.push('/scopes/s1/curations/zzz')
    await flushPromises()
    expect(confirm).toHaveBeenCalledTimes(1)
    expect(routerRef.currentRoute.value.fullPath).toBe('/scopes/s1/curations/c-new/edit')
    confirm.mockClear()

    curationsStore.submitCuration.mockResolvedValue({ lock_version: 1 })
    await api.handleSubmit()
    await flushPromises()
    expect(curationsStore.createCuration).toHaveBeenCalledTimes(1)
    expect(curationsStore.submitCuration).toHaveBeenLastCalledWith('c-new', { lock_version: 0 })
    expect(confirm).not.toHaveBeenCalled()
  })

  it('submit of a new curation ends on the detail page when the view is keyed by URL', async () => {
    curationsStore.submitCuration.mockResolvedValue({ lock_version: 1 })
    await setup(View, true)

    await api.handleSubmit()
    await flushPromises()

    expect(confirm).not.toHaveBeenCalled()
    expect(routerRef.currentRoute.value.fullPath).toBe('/scopes/s1/curations/c-new')
  })
})
