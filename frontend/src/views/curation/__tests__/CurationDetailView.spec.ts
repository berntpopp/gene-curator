import { useWorkflowStore } from '@/stores/workflow'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

const router = vi.hoisted(() => ({ push: vi.fn(), back: vi.fn() }))

vi.mock('@/api', () => ({
  curationsAPI: { getCuration: vi.fn() },
  workflowAPI: { transitionCuration: vi.fn() },
  schemasAPI: { getWorkflowPairById: vi.fn(), getSchemaById: vi.fn() }
}))

vi.mock('vue-router', () => ({
  useRouter: () => router,
  useRoute: () => ({ params: { scopeId: 'sc1', curationId: 'c1' } })
}))

import { curationsAPI } from '@/api'
import { workflowAPI, schemasAPI } from '@/api'
import { useAuthStore } from '@/stores/auth'
import CurationDetailView from '@/views/curation/CurationDetailView.vue'
import CurationEvidenceReadonly from '@/components/curation/CurationEvidenceReadonly.vue'
import CurationReviewDialogs from '@/components/curation/CurationReviewDialogs.vue'

const openDialogStub = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }

describe('CurationDetailView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(curationsAPI.getCuration).mockReset()
    router.push.mockReset()
    router.back.mockReset()
  })

  it('shows a loading card while the curation is fetched', async () => {
    vi.mocked(curationsAPI.getCuration).mockReturnValue(new Promise(() => {}))
    const wrapper = mount(CurationDetailView, { global: { stubs: { DynamicForm: true } } })
    await flushPromises()
    expect(curationsAPI.getCuration).toHaveBeenCalledWith('c1')
    expect(wrapper.find('.v-progress-circular').exists()).toBe(true)
  })

  it('shows an error message when the curation cannot be loaded', async () => {
    vi.mocked(curationsAPI.getCuration).mockRejectedValue(new Error('500'))
    const wrapper = mount(CurationDetailView, { global: { stubs: { DynamicForm: true } } })
    await flushPromises()
    expect(wrapper.text()).toContain('Failed to load curation details')
  })

  it.each([
    [{ contradictory_evidence: [{ pmid: '1' }] }, 'Disputed'],
    [{ replicated_over_time: true }, 'No known disease relationship'],
    [{}, 'No known disease relationship']
  ])('classifies evidence %j as %s', async (extra, label) => {
    vi.mocked(curationsAPI.getCuration).mockResolvedValue({
      id: 'c1',
      workflow_stage: 'curation',
      status: 'draft',
      evidence_data: { ...extra }
    } as never)
    const wrapper = mount(CurationDetailView, { global: { stubs: { DynamicForm: true } } })
    await flushPromises()
    expect(wrapper.text()).toContain(label)
  })

  const load = async (curation: Record<string, unknown>, engine = 'clingen_sop_v11') => {
    vi.mocked(schemasAPI.getWorkflowPairById).mockResolvedValue({
      curation_schema_id: 's1'
    } as never)
    vi.mocked(schemasAPI.getSchemaById).mockResolvedValue({
      scoring_configuration: { engine }
    } as never)
    vi.mocked(curationsAPI.getCuration).mockResolvedValue({
      id: 'c1',
      workflow_stage: 'review',
      status: 'in_review',
      gene_symbol: 'PKD1',
      disease_name: 'ADPKD',
      evidence_data: {},
      workflow_pair_id: 'wp',
      ...curation
    } as never)
    const wrapper = mount(CurationDetailView, {
      global: { stubs: { DynamicForm: true, VDialog: openDialogStub } }
    })
    await flushPromises()
    return wrapper
  }

  it('renders ClinGen evidence rows read-only for the reviewer (#238)', async () => {
    const wrapper = await load({
      can_review: true,
      evidence_data: {
        evidence_summary: 'Narrative',
        genetic_evidence: { segregation: [{ pmid: '1' }] }
      }
    })
    expect(wrapper.findComponent(CurationEvidenceReadonly).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'DynamicForm' }).exists()).toBe(false)
  })

  it('keeps the generic form for non-ClinGen schemas', async () => {
    const wrapper = await load({ evidence_data: { foo: 1 } }, 'other')
    expect(wrapper.findComponent(CurationEvidenceReadonly).exists()).toBe(false)
  })

  it('explains the 4-eyes wait to the author of a curation in review (#242)', async () => {
    useAuthStore().user = { id: 'me' } as never
    const wrapper = await load({ created_by: 'me', can_review: false })
    expect(wrapper.text()).toContain('Waiting for review by another scope reviewer (4-eyes)')
    expect(wrapper.text()).not.toContain('No actions available')
  })

  it('puts Delete after a divider, below the review actions (#242)', async () => {
    const wrapper = await load({ can_review: true, can_delete: true })
    const html = wrapper.html()
    expect(html.indexOf('Request changes')).toBeLessThan(html.indexOf('data-test="delete"'))
    expect(wrapper.find('.workflow-actions .v-divider').exists()).toBe(true)
  })

  it('titles the page with gene and disease and humanises snake_case inheritance (#242)', async () => {
    const wrapper = await load({ mode_of_inheritance: 'autosomal_recessive' })
    expect(wrapper.find('h1').text()).toBe('PKD1 – ADPKD')
    expect(wrapper.text()).toContain('Autosomal recessive')
  })

  it.each([
    [{ back: '/review-queue' }, 'back'],
    [null, 'push']
  ])('goes back via history state %j (#242)', async (state, expected) => {
    window.history.replaceState(state, '')
    const wrapper = await load({})
    await wrapper.find('button[aria-label="Go back"]').trigger('click')
    if (expected === 'back') expect(router.back).toHaveBeenCalled()
    else
      expect(router.push).toHaveBeenCalledWith({
        name: 'scope-dashboard',
        params: { scopeId: 'sc1' }
      })
  })

  it('shows the API detail inside the approve dialog when approving fails (#237)', async () => {
    vi.mocked(workflowAPI.transitionCuration).mockRejectedValue({
      response: { data: { detail: 'Notification step failed' } }
    })
    const wrapper = await load({ can_review: true })
    const dialogs = wrapper.findComponent(CurationReviewDialogs)
    dialogs.vm.$emit('approve', 'ok')
    await flushPromises()
    expect(dialogs.props('errorDetail')).toBe('Notification step failed')
  })

  it('refreshes the shared review badge count after a transition', async () => {
    vi.mocked(workflowAPI.transitionCuration).mockResolvedValue({} as never)
    const refresh = vi.spyOn(useWorkflowStore(), 'fetchPendingReviewCount').mockResolvedValue(0)
    const wrapper = await load({ can_review: true })
    wrapper.findComponent(CurationReviewDialogs).vm.$emit('approve', 'ok')
    await flushPromises()
    expect(refresh).toHaveBeenCalled()
  })

  it('requests changes with the comment from the dialog (#242)', async () => {
    vi.mocked(workflowAPI.transitionCuration).mockResolvedValue({} as never)
    const wrapper = await load({ can_review: true })
    wrapper.findComponent(CurationReviewDialogs).vm.$emit('reject', 'Fix it')
    await flushPromises()
    expect(workflowAPI.transitionCuration).toHaveBeenCalledWith('c1', {
      target_stage: 'curation',
      notes: 'Fix it'
    })
  })

  it('gives an empty ClinGen draft the ClinGen view', async () => {
    const wrapper = await load({ status: 'draft', evidence_data: {} })
    expect(wrapper.findComponent(CurationEvidenceReadonly).exists()).toBe(true)
  })

  it('opens the submit and delete confirmation dialogs with the gene name', async () => {
    const wrapper = await load({ can_review: true, can_delete: true })
    const vm = wrapper.vm as unknown as { showSubmitDialog: boolean; showDeleteDialog: boolean }
    vm.showSubmitDialog = true
    await flushPromises()
    expect(wrapper.text()).toContain('Submit this curation for PKD1 for review?')
    vm.showSubmitDialog = false
    vm.showDeleteDialog = true
    await flushPromises()
    expect(wrapper.text()).toContain('This action cannot be undone.')
  })
})
