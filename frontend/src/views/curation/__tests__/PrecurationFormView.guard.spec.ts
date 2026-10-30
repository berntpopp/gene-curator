import { describe, it, expect, vi, beforeEach } from 'vitest'
import { defineComponent, h, inject, ref } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

// An unsaved precuration edit (a MONDO pick) asks before the page is left, like the curation form
vi.mock('@/api', () => ({
  genesAPI: { getGeneById: vi.fn().mockResolvedValue({ approved_symbol: 'PKD1' }) },
  scopesAPI: { getScopeById: vi.fn().mockResolvedValue({ default_workflow_pair_id: 'wp1' }) },
  schemasAPI: {
    getWorkflowPairs: vi.fn().mockResolvedValue([{ id: 'wp1', precuration_schema_id: 's1' }])
  }
}))
const leave = vi.hoisted(() => ({ hook: null as null | (() => Promise<boolean> | boolean) }))
const push = vi.hoisted(() => vi.fn())
vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => ({ params: { scopeId: 'sc1', geneId: 'g1' }, query: {} }),
  onBeforeRouteLeave: (hook: () => Promise<boolean>) => (leave.hook = hook)
}))
const confirm = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm }) }))

import { useScopesStore } from '@/stores/scopes'
import { WORKSPACE_FRAME } from '@/components/workspace/useWorkspaceFrame'
import PrecurationFormView from '@/views/curation/PrecurationFormView.vue'

const evidence = ref<Record<string, unknown>>({})
// Stands in for SchemaDrivenPrecurationForm's frame binding
const FormStub = defineComponent({
  name: 'SchemaDrivenPrecurationForm',
  emits: ['submit', 'cancel', 'saved'],
  setup() {
    const frame = inject(WORKSPACE_FRAME)!
    frame.attachForm({ evidence, saving: ref(false), savedAt: ref(null), save: vi.fn() })
    frame.markClean({})
    return () => h('div')
  }
})

async function mountView() {
  const wrapper = mount(PrecurationFormView, {
    global: { stubs: { SchemaDrivenPrecurationForm: FormStub } }
  })
  await flushPromises()
  return wrapper
}

describe('PrecurationFormView leave guard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue('curator' as never)
    evidence.value = {}
    confirm.mockReset().mockResolvedValue(false)
    push.mockReset()
  })

  it('leaves an untouched form without asking', async () => {
    await mountView()
    expect(await leave.hook!()).toBe(true)
    expect(confirm).not.toHaveBeenCalled()
  })

  it('asks before losing an unsaved edit, on route leave and tab close', async () => {
    await mountView()
    evidence.value = { disease: 'MONDO:0000001' }
    expect(await leave.hook!()).toBe(false)
    expect(confirm).toHaveBeenCalledWith(
      expect.objectContaining({ title: 'Leave without saving?' })
    )
    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
  })

  it('does not ask after a submit or a confirmed cancel', async () => {
    for (const done of ['submit', 'cancel']) {
      const wrapper = await mountView()
      evidence.value = { disease: 'MONDO:0000001' }
      wrapper.findComponent(FormStub).vm.$emit(done)
      expect(await leave.hook!()).toBe(true)
      wrapper.unmount()
    }
    expect(confirm).not.toHaveBeenCalled()
  })
})
