import { useWorkCountsStore } from '@/stores/workCounts'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

const router = vi.hoisted(() => ({ push: vi.fn(), back: vi.fn() }))

vi.mock('@/api', () => ({
  curationsAPI: { getCuration: vi.fn(), submitCuration: vi.fn() },
  workflowAPI: { transitionCuration: vi.fn() },
  schemasAPI: { getWorkflowPairById: vi.fn(), getSchemaById: vi.fn() }
}))

vi.mock('@/api/reviewComments', () => ({
  reviewCommentsAPI: {
    getDiff: vi.fn().mockResolvedValue({ baseline: null, items: [] }),
    list: vi.fn().mockResolvedValue([]),
    create: vi.fn(),
    update: vi.fn(),
    myPendingItemIds: vi.fn()
  }
}))

vi.mock('vue-router', () => ({
  useRouter: () => router,
  useRoute: () => ({ params: { scopeId: 'sc1', curationId: 'c1' } })
}))

import { curationsAPI } from '@/api'
import { useNotificationsStore } from '@/stores/notifications'
import { workflowAPI, schemasAPI } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import CurationDetailView from '@/views/curation/CurationDetailView.vue'
import CurationEvidenceReadonly from '@/components/curation/CurationEvidenceReadonly.vue'
import ApproveChecklistDialog from '@/components/review/ApproveChecklistDialog.vue'
import RequestChangesDialog from '@/components/review/RequestChangesDialog.vue'
import ReviewDiff from '@/components/review/ReviewDiff.vue'

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

  it.each([403, 404])(
    'says not found, with no Export, when the load is %i (#403)',
    async status => {
      vi.mocked(curationsAPI.getCuration).mockRejectedValue({ response: { status } })
      const wrapper = mount(CurationDetailView, { global: { stubs: { DynamicForm: true } } })
      await flushPromises()
      expect(wrapper.text()).toContain('Curation not found')
      expect(wrapper.text()).not.toContain('Failed to load')
      expect(wrapper.text()).not.toContain('Export')
    }
  )

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

  describe('re-curation entry point', () => {
    const recurate = (w: Awaited<ReturnType<typeof load>>) => w.find('[data-testid="recurate"]')

    it('offers a curator to start a re-curation from the active curation', async () => {
      vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue('curator' as never)
      const wrapper = await load({ workflow_stage: 'active', status: 'active', gene_id: 'g1' })
      await recurate(wrapper).trigger('click')
      expect(router.push).toHaveBeenCalledWith({
        name: 'gene-curation-create',
        params: { scopeId: 'sc1', geneId: 'g1' },
        query: { from: 'c1' }
      })
    })

    it('hides it from viewers and for curations that are not active', async () => {
      const role = vi.spyOn(useScopesStore(), 'fetchUserRole')
      role.mockResolvedValue('viewer' as never)
      expect(recurate(await load({ workflow_stage: 'active', gene_id: 'g1' })).exists()).toBe(false)
      role.mockResolvedValue('curator' as never)
      expect(recurate(await load({ gene_id: 'g1' })).exists()).toBe(false)
    })
  })

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

  it('links a reviewer to the AI second view, nobody else (#530)', async () => {
    const link = (w: Awaited<ReturnType<typeof load>>) =>
      w.findAllComponents({ name: 'VBtn' }).find(b => b.text() === 'AI second view')
    expect(link(await load({ can_review: true }))?.props('to')).toEqual({
      name: 'llm-second-view',
      params: { scopeId: 'sc1', curationId: 'c1' }
    })
    expect(link(await load({ can_review: false }))).toBeUndefined()
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

  it('names a susceptibility relationship next to the inheritance only (#539)', async () => {
    const mendelian = await load({ mode_of_inheritance: 'AD', relationship_type: 'mendelian' })
    expect(mendelian.text()).not.toContain('Susceptibility')
    expect(mendelian.text()).not.toContain('Not specified')
    const sus = await load({ mode_of_inheritance: 'AD', relationship_type: 'susceptibility' })
    expect(sus.text()).toContain('Susceptibility')
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

  it('shows the stored score and verdict, not a client recalculation (#266)', async () => {
    // Client SOP caps would give 4 model points (Limited); the pinned model stored 9.6 Moderate
    const wrapper = await load({
      can_review: true,
      evidence_data: {
        experimental_evidence: { models: { non_human_model_organism: [{ points: 4 }] } }
      },
      computed_verdict: 'moderate',
      computed_scores: {
        total_score: 9.6,
        genetic_evidence_total: 8.6,
        experimental_evidence_total: 1,
        trace: {
          sections: [
            { key: 'genetic_evidence', score: 8.6, cap: 12 },
            {
              key: 'experimental_evidence',
              score: 1,
              cap: 2,
              categories: [{ key: 'models', score: 1 }]
            }
          ]
        }
      }
    })
    expect(wrapper.text()).toContain('9.60')
    expect(wrapper.text()).toContain('Moderate')
    const dialog = wrapper.findComponent(ApproveChecklistDialog)
    expect(dialog.props('classification')).toBe('Moderate')
    expect(dialog.props('total')).toBe('9.60')
    // Caps come from the pinned model's trace, not the SOP defaults
    const row = wrapper.findAll('tr').find(row => row.text().includes('Experimental evidence'))!
    expect(row.findAll('th,td').map(cell => cell.text())).toEqual([
      'Experimental evidence',
      '—',
      'Unavailable',
      '1.00',
      '2'
    ])
    expect(wrapper.text()).not.toContain('/ 6')
  })

  it('leads with the final classification and gives the reviewer both (#533)', async () => {
    const wrapper = await load({
      can_review: true,
      computed_verdict: 'moderate',
      final_classification: 'Disputed',
      curator_classification_rationale: 'Contradicting cohort'
    })
    expect(wrapper.find('[data-testid=calculated-classification]').text()).toContain('Moderate')
    const dialog = wrapper.findComponent(ApproveChecklistDialog)
    expect(dialog.props('classification')).toBe('Disputed')
    expect(dialog.props('calculated')).toBe('Moderate')
    expect(dialog.props('rationale')).toBe('Contradicting cohort')
  })

  it('shows no caps and unknown breakdown rows for a legacy row without trace (#266)', async () => {
    const wrapper = await load({ computed_scores: { total_score: 5 }, computed_verdict: 'limited' })
    expect(wrapper.text()).not.toContain('max')
    expect(wrapper.text()).toContain('—')
    expect(wrapper.text()).not.toContain('0.00 /')
  })

  it('shows the API detail inside the approve dialog when approving fails (#237)', async () => {
    vi.mocked(workflowAPI.transitionCuration).mockRejectedValue({
      response: { data: { detail: 'Notification step failed' } }
    })
    const wrapper = await load({ can_review: true })
    const dialog = wrapper.findComponent(ApproveChecklistDialog)
    dialog.vm.$emit('approve', 'ok')
    await flushPromises()
    expect(dialog.props('error')).toBe('Notification step failed')
  })

  it('refreshes the shared review badge count after a transition', async () => {
    vi.mocked(workflowAPI.transitionCuration).mockResolvedValue({} as never)
    const refresh = vi.spyOn(useWorkCountsStore(), 'fetch').mockResolvedValue(undefined)
    const wrapper = await load({ can_review: true })
    wrapper.findComponent(ApproveChecklistDialog).vm.$emit('approve', 'ok')
    await flushPromises()
    expect(refresh).toHaveBeenCalled()
  })

  it('requests changes with the comment from the dialog (#242)', async () => {
    vi.mocked(workflowAPI.transitionCuration).mockResolvedValue({} as never)
    const wrapper = await load({ can_review: true })
    wrapper.findComponent(RequestChangesDialog).vm.$emit('reject', 'Fix it')
    await flushPromises()
    expect(workflowAPI.transitionCuration).toHaveBeenCalledWith('c1', {
      target_stage: 'curation',
      notes: 'Fix it'
    })
  })

  it('shows reviewers the evidence diff with Accept and Query controls (#279)', async () => {
    useAuthStore().user = { id: 'bob' } as never
    const wrapper = await load({ can_review: true, created_by: 'alice' })
    const diff = wrapper.findComponent(ReviewDiff)
    expect(diff.exists()).toBe(true)
    expect(diff.props('reviewer')).toBe(true)
    expect(diff.props('canReply')).toBe(true)
  })

  it('never gives the curation creator Accept or Approve, even with can_review (D1)', async () => {
    useAuthStore().user = { id: 'alice' } as never
    const wrapper = await load({ can_review: true, created_by: 'alice', can_edit: true })
    expect(wrapper.findComponent(ReviewDiff).props('reviewer')).toBe(false)
    expect(wrapper.findComponent(ReviewDiff).props('canReply')).toBe(true)
    expect(wrapper.text()).not.toContain('Approve')
    expect(wrapper.text()).toContain('Waiting for review by another scope reviewer (4-eyes)')
  })

  it('replaces Approve with the remaining count once this reviewer approved (#430)', async () => {
    useAuthStore().user = { id: 'bob' } as never
    vi.mocked(workflowAPI.transitionCuration).mockResolvedValue({ to_stage: 'review' } as never)
    const wrapper = await load({ can_review: true, created_by: 'alice' })
    const approveButton = () => wrapper.findAll('button').find(b => b.text() === 'Approve')
    expect(approveButton()).toBeDefined()
    vi.mocked(curationsAPI.getCuration).mockResolvedValue({
      id: 'c1',
      status: 'in_review',
      created_by: 'alice',
      can_review: true,
      has_approved: true,
      approvals_remaining: 1
    } as never)
    wrapper.findComponent(ApproveChecklistDialog).vm.$emit('approve', 'ok')
    await flushPromises()
    expect(wrapper.text()).toContain('You approved; 1 more needed')
    expect(approveButton()).toBeUndefined()
    expect(wrapper.text()).not.toContain('No actions available')
    // only Approve is gated: request changes, replies and item actions stay
    expect(wrapper.text()).toContain('Request changes')
    expect(wrapper.findComponent(ReviewDiff).props('reviewer')).toBe(true)
    expect(wrapper.findComponent(ReviewDiff).props('canReply')).toBe(true)
  })

  it('keeps Approve when the recorded approval leaves none needed, so it can activate (#430)', async () => {
    useAuthStore().user = { id: 'bob' } as never
    const wrapper = await load({
      can_review: true,
      created_by: 'alice',
      has_approved: true,
      approvals_remaining: 0
    })
    expect(wrapper.findAll('button').some(b => b.text() === 'Approve')).toBe(true)
    expect(wrapper.text()).not.toContain('You approved')
  })

  it('keeps the approval note next to other actions such as Delete (#430)', async () => {
    const wrapper = await load({ has_approved: true, approvals_remaining: 1, can_delete: true })
    expect(wrapper.text()).toContain('You approved; 1 more needed')
  })

  it('opens the approve checklist with the unreviewed items as blockers', async () => {
    useAuthStore().user = { id: 'bob' } as never
    const wrapper = await load({ can_review: true, created_by: 'alice' })
    const approve = wrapper.findAll('button').find(b => b.text() === 'Approve')!
    await approve.trigger('click')
    expect(wrapper.findComponent(ApproveChecklistDialog).props('modelValue')).toBe(true)
  })

  // #406: the approve blocker names the record like the diff does, not by its position
  it('names approve blockers by their record label', async () => {
    useAuthStore().user = { id: 'bob' } as never
    const { reviewCommentsAPI } = await import('@/api/reviewComments')
    vi.mocked(reviewCommentsAPI.getDiff).mockResolvedValueOnce({
      baseline: null,
      items: [{ path: 'g.null_variants[0].points', change: 'changed', before: 1, after: 2 }]
    } as never)
    const wrapper = await load({
      can_review: true,
      created_by: 'alice',
      evidence_data: { g: { null_variants: [{ proband_label: 'Patient 1', points: 2 }] } }
    })
    const blockers = wrapper.findComponent(ApproveChecklistDialog).props('blockers')
    expect(blockers.map((b: { label: string }) => b.label)).toEqual(['Null variants · Patient 1'])
  })

  it('prefills request changes with the open queries as to-dos', async () => {
    useAuthStore().user = { id: 'bob' } as never
    const { useReviewStore } = await import('@/stores/review')
    const wrapper = await load({ can_review: true, created_by: 'alice' })
    useReviewStore().comments = [
      {
        id: 'q',
        kind: 'query',
        status: 'open',
        item_path: 'summary',
        body: 'Explain',
        author_id: 'bob'
      },
      {
        id: 'r',
        kind: 'query',
        status: 'open',
        item_path: 'summary',
        body: 'My reply',
        author_id: 'alice'
      }
    ] as never
    await flushPromises()
    expect(wrapper.findComponent(RequestChangesDialog).props('todos')).toBe('- Summary: Explain')
  })

  it('blocks approval while the review has not loaded (failed load)', async () => {
    const { reviewCommentsAPI } = await import('@/api/reviewComments')
    vi.mocked(reviewCommentsAPI.getDiff).mockRejectedValueOnce({ response: { status: 500 } })
    useAuthStore().user = { id: 'bob' } as never
    const wrapper = await load({ can_review: true, created_by: 'alice' })
    const blockers = wrapper.findComponent(ApproveChecklistDialog).props('blockers')
    expect(blockers).toHaveLength(1)
    expect(blockers[0]!.label).toContain('not loaded')
  })

  it('shows a curator the queries after changes were requested (draft)', async () => {
    useAuthStore().user = { id: 'alice' } as never
    const wrapper = await load({ status: 'draft', created_by: 'alice', can_edit: true })
    expect(wrapper.findComponent(ReviewDiff).props('onlyWithComments')).toBe(true)
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
    expect(wrapper.text()).toContain('This cannot be undone.')
    expect(wrapper.find('[data-testid=delete-recurate]').exists()).toBe(false)
  })

  it('names the impact of deleting an active curation and offers re-curation (#392)', async () => {
    vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue('admin' as never)
    const wrapper = await load({
      workflow_stage: 'active',
      status: 'active',
      gene_id: 'g1',
      can_delete: true
    })
    const vm = wrapper.vm as unknown as { showDeleteDialog: boolean }
    vm.showDeleteDialog = true
    await flushPromises()
    expect(wrapper.text()).toContain('Delete the active curation for PKD1?')
    expect(wrapper.text()).toContain('without an active classification')
    await wrapper.find('[data-testid=delete-recurate]').trigger('click')
    expect(router.push).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'gene-curation-create', query: { from: 'c1' } })
    )
  })

  it('uses flat outlined cards without decorative title icons (#392)', async () => {
    const wrapper = await load({ can_review: true, can_delete: true })
    const cards = wrapper.findAll('.v-card').filter(c => !c.element.closest('.v-overlay'))
    expect(cards.length).toBeGreaterThan(0)
    for (const c of cards) expect(c.classes()).toContain('v-card--variant-outlined')
    expect(wrapper.findAll('.v-card-title .v-icon')).toHaveLength(0)
  })

  it('toasts a refused submit as a readable sentence, not raw validation JSON', async () => {
    const wrapper = await load({ can_review: false })
    vi.mocked(curationsAPI.submitCuration).mockRejectedValue({
      response: { data: { detail: [{ loc: ['body', 'notes'], msg: 'Field required' }] } }
    })
    const toast = vi.spyOn(useNotificationsStore(), 'addToast')
    await (wrapper.vm as unknown as { submitForReview: () => Promise<void> }).submitForReview()
    expect(toast).toHaveBeenCalledWith('Failed to submit: Notes: Field required.', 'error')
  })
})
