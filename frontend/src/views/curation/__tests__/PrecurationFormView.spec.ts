import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api', () => ({
  genesAPI: { getGeneById: vi.fn() },
  scopesAPI: { getScopeById: vi.fn() },
  schemasAPI: { getWorkflowPairs: vi.fn() }
}))

const route = vi.hoisted(() => ({ params: {} as Record<string, string>, query: {} }))
const push = vi.hoisted(() => vi.fn())

vi.mock('@/api/precurations', () => ({
  precurationsAPI: {
    getPrecuration: vi.fn(),
    approvePrecuration: vi.fn(),
    rejectPrecuration: vi.fn()
  }
}))

const confirmMock = vi.hoisted(() => vi.fn())
vi.mock('@/composables/useConfirm', () => ({ useConfirm: () => ({ confirm: confirmMock }) }))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
  useRoute: () => route
}))

import { genesAPI, scopesAPI, schemasAPI } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import { precurationsAPI } from '@/api/precurations'
import PrecurationFormView from '@/views/curation/PrecurationFormView.vue'

describe('PrecurationFormView', () => {
  beforeEach(() => {
    route.params = { scopeId: 'sc1', geneId: 'g1' }
    setActivePinia(createPinia())
    vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue('curator' as never)
    vi.mocked(scopesAPI.getScopeById).mockResolvedValue({
      default_workflow_pair_id: 'wp1'
    } as never)
    vi.mocked(schemasAPI.getWorkflowPairs).mockResolvedValue([
      { id: 'wp1', precuration_schema_id: 'schema-1' }
    ] as never)
  })

  it('loads the scope, its precuration schema and the gene', async () => {
    vi.mocked(genesAPI.getGeneById).mockResolvedValue({ approved_symbol: 'BRCA1' } as never)
    const wrapper = mount(PrecurationFormView, {
      global: { stubs: { SchemaDrivenPrecurationForm: true } }
    })
    await flushPromises()
    expect(scopesAPI.getScopeById).toHaveBeenCalledWith('sc1')
    expect(genesAPI.getGeneById).toHaveBeenCalledWith('g1')
    expect(wrapper.text()).toContain('BRCA1')
    expect(wrapper.text()).not.toContain('Unknown')
    expect(wrapper.findComponent({ name: 'SchemaDrivenPrecurationForm' }).props('gene')).toEqual({
      symbol: 'BRCA1'
    })
  })

  it('shows an error when the gene cannot be loaded', async () => {
    vi.mocked(genesAPI.getGeneById).mockRejectedValue(new Error('404'))
    const wrapper = mount(PrecurationFormView, {
      global: { stubs: { SchemaDrivenPrecurationForm: true } }
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Could not load gene information: 404')
  })

  it.each([
    ['draft', 'me', 'sc1', false],
    ['rejected', 'me', 'sc1', false],
    ['submitted', 'me', 'sc1', true],
    ['approved', 'me', 'sc1', true],
    ['draft', 'other', 'sc1', true],
    ['draft', 'me', 'sc2', true]
  ])(
    'opens a %s precuration by %s in %s (readonly=%s)',
    async (status, createdBy, precScope, readonly) => {
      useAuthStore().user = { id: 'me' } as never
      route.params = { scopeId: 'sc1', precurationId: 'p1' }
      vi.mocked(precurationsAPI.getPrecuration).mockResolvedValue({
        id: 'p1',
        gene_id: 'g7',
        status,
        created_by: createdBy,
        scope_id: precScope
      } as never)
      vi.mocked(genesAPI.getGeneById).mockResolvedValue({ approved_symbol: 'PKD1' } as never)
      const wrapper = mount(PrecurationFormView, {
        global: { stubs: { SchemaDrivenPrecurationForm: true } }
      })
      await flushPromises()
      expect(genesAPI.getGeneById).toHaveBeenCalledWith('g7')
      const form = wrapper.findComponent({ name: 'SchemaDrivenPrecurationForm' })
      expect(form.props('precurationId')).toBe('p1')
      expect(form.props('readonly')).toBe(readonly)
      // A read-only form always says why its actions are disabled
      expect(wrapper.find('[data-testid="ws-readonly"]').exists()).toBe(readonly)
    }
  )

  it.each([
    ['submitted', 'in review'],
    ['in_review', 'in review'],
    ['approved', 'Read-only: this precuration is approved.'],
    ['archived', 'Read-only: this precuration is archived.']
  ])('says why a %s precuration is read-only', async (status, text) => {
    useAuthStore().user = { id: 'me' } as never
    route.params = { scopeId: 'sc1', precurationId: 'p1' }
    vi.mocked(precurationsAPI.getPrecuration).mockResolvedValue({
      id: 'p1',
      gene_id: 'g7',
      status,
      created_by: 'me',
      scope_id: 'sc1'
    } as never)
    vi.mocked(genesAPI.getGeneById).mockResolvedValue({ approved_symbol: 'PKD1' } as never)
    const wrapper = mount(PrecurationFormView, {
      global: { stubs: { SchemaDrivenPrecurationForm: true } }
    })
    await flushPromises()
    expect(wrapper.find('[data-testid="ws-readonly"]').text()).toContain(text)
  })

  it.each([
    ['rejected', 'Narrow the disease', true],
    ['submitted', 'Narrow the disease', false]
  ])('shows the reviewer reason on a %s precuration: %s (%s)', async (status, reason, shown) => {
    useAuthStore().user = { id: 'me' } as never
    route.params = { scopeId: 'sc1', precurationId: 'p1' }
    vi.mocked(precurationsAPI.getPrecuration).mockResolvedValue({
      id: 'p1',
      gene_id: 'g7',
      status,
      created_by: 'me',
      scope_id: 'sc1',
      computed_fields: { rejection_reason: reason }
    } as never)
    vi.mocked(genesAPI.getGeneById).mockResolvedValue({ approved_symbol: 'PKD1' } as never)
    const wrapper = mount(PrecurationFormView, {
      global: { stubs: { SchemaDrivenPrecurationForm: true } }
    })
    await flushPromises()
    const alert = wrapper.find('[data-testid=sent-back-reason]')
    expect(alert.exists()).toBe(shown)
    if (shown) expect(alert.text()).toContain(reason)
  })

  it('shows an error when the precuration cannot be loaded', async () => {
    route.params = { scopeId: 'sc1', precurationId: 'p1' }
    vi.mocked(precurationsAPI.getPrecuration).mockRejectedValue(new Error('404'))
    const wrapper = mount(PrecurationFormView, {
      global: { stubs: { SchemaDrivenPrecurationForm: true } }
    })
    await flushPromises()
    expect(wrapper.text()).toContain('Could not load precuration')
  })

  it('shows the workspace header: breadcrumb to the scope and gene, precuration stage', async () => {
    vi.mocked(scopesAPI.getScopeById).mockResolvedValue({
      display_name: 'Kidney genetics',
      default_workflow_pair_id: 'wp1'
    } as never)
    vi.mocked(genesAPI.getGeneById).mockResolvedValue({
      approved_symbol: 'BRCA1',
      hgnc_id: 'HGNC:1100'
    } as never)
    const wrapper = mount(PrecurationFormView, {
      global: {
        stubs: {
          SchemaDrivenPrecurationForm: true,
          'router-link': { props: ['to'], template: '<a :href="to"><slot /></a>' }
        }
      }
    })
    await flushPromises()
    const crumbs = wrapper.find('nav[aria-label="Breadcrumb"]')
    expect(crumbs.findAll('a').map(a => a.attributes('href'))).toEqual(['/scopes/sc1', '/genes/g1'])
    expect(crumbs.find('[aria-current="page"]').text()).toBe('Precuration')
    expect(wrapper.find('[aria-current="step"]').text()).toBe('Precuration')
    expect(wrapper.find('[data-testid="ws-save"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('HGNC')
  })

  describe('entry guard for a new precuration', () => {
    const mountNew = async (role: string) => {
      vi.mocked(genesAPI.getGeneById).mockResolvedValue({ approved_symbol: 'BRCA1' } as never)
      const fetchRole = vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue(role as never)
      const wrapper = mount(PrecurationFormView, {
        global: { stubs: { SchemaDrivenPrecurationForm: true } }
      })
      await flushPromises()
      return { wrapper, fetchRole }
    }

    it('shows a viewer the not-authorized notice, with no form', async () => {
      const { wrapper, fetchRole } = await mountNew('viewer')
      expect(fetchRole).toHaveBeenCalledWith('sc1')
      expect(wrapper.find('[data-testid=no-curate-access]').exists()).toBe(true)
      expect(wrapper.findComponent({ name: 'SchemaDrivenPrecurationForm' }).exists()).toBe(false)
    })

    it('never shows the form when the role lookup fails, and retries', async () => {
      vi.mocked(genesAPI.getGeneById).mockResolvedValue({ approved_symbol: 'BRCA1' } as never)
      const fetchRole = vi
        .spyOn(useScopesStore(), 'fetchUserRole')
        .mockRejectedValue(new Error('500'))
      const wrapper = mount(PrecurationFormView, {
        global: { stubs: { SchemaDrivenPrecurationForm: true } }
      })
      await flushPromises()
      expect(wrapper.text()).toContain('could not check')
      expect(wrapper.findComponent({ name: 'SchemaDrivenPrecurationForm' }).exists()).toBe(false)

      fetchRole.mockResolvedValue('curator' as never)
      await wrapper.find('[data-testid=retry-access]').trigger('click')
      await flushPromises()
      expect(wrapper.findComponent({ name: 'SchemaDrivenPrecurationForm' }).exists()).toBe(true)
    })

    it('shows a curator the form', async () => {
      const { wrapper } = await mountNew('curator')
      expect(wrapper.find('[data-testid=no-curate-access]').exists()).toBe(false)
      expect(wrapper.findComponent({ name: 'SchemaDrivenPrecurationForm' }).exists()).toBe(true)
    })

    it('still opens an existing precuration read-only for a reviewer', async () => {
      route.params = { scopeId: 'sc1', precurationId: 'p1' }
      vi.mocked(precurationsAPI.getPrecuration).mockResolvedValue({
        id: 'p1',
        gene_id: 'g1',
        created_by: 'x',
        scope_id: 'sc1',
        status: 'submitted'
      } as never)
      vi.mocked(genesAPI.getGeneById).mockResolvedValue({ approved_symbol: 'BRCA1' } as never)
      const fetchRole = vi
        .spyOn(useScopesStore(), 'fetchUserRole')
        .mockResolvedValue('reviewer' as never)
      const wrapper = mount(PrecurationFormView, {
        global: { stubs: { SchemaDrivenPrecurationForm: true } }
      })
      await flushPromises()
      // The role is read only to offer review actions, never to block opening it
      expect(fetchRole).toHaveBeenCalledTimes(1)
      expect(wrapper.find('[data-testid=no-curate-access]').exists()).toBe(false)
      expect(wrapper.findComponent({ name: 'SchemaDrivenPrecurationForm' }).exists()).toBe(true)
    })
  })

  describe('reviewing a submitted precuration (#390)', () => {
    const mountReview = async (role: string, createdBy = 'alice', status = 'submitted') => {
      useAuthStore().user = { id: 'bob' } as never
      route.params = { scopeId: 'sc1', precurationId: 'p1' }
      vi.mocked(precurationsAPI.getPrecuration).mockResolvedValue({
        id: 'p1',
        gene_id: 'g1',
        created_by: createdBy,
        scope_id: 'sc1',
        status
      } as never)
      vi.mocked(genesAPI.getGeneById).mockResolvedValue({ approved_symbol: 'BRCA1' } as never)
      vi.spyOn(useScopesStore(), 'fetchUserRole').mockResolvedValue(role as never)
      const wrapper = mount(PrecurationFormView, {
        global: {
          stubs: {
            SchemaDrivenPrecurationForm: true,
            VDialog: { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }
          }
        }
      })
      await flushPromises()
      return wrapper
    }

    it('shows the status to everyone', async () => {
      const wrapper = await mountReview('viewer')
      expect(wrapper.find('[data-testid=precuration-status]').text()).toContain('Submitted')
    })

    it.each([
      ['reviewer', 'alice', 'submitted', true],
      ['admin', 'alice', 'submitted', true],
      ['curator', 'alice', 'submitted', false],
      ['viewer', 'alice', 'submitted', false],
      ['reviewer', 'bob', 'submitted', false],
      ['reviewer', 'alice', 'approved', false]
    ])('%s on a precuration by %s (%s): review actions %s', async (role, by, status, shown) => {
      const wrapper = await mountReview(role, by, status)
      expect(wrapper.find('[data-testid=approve-precuration]').exists()).toBe(shown)
      expect(wrapper.find('[data-testid=reject-precuration]').exists()).toBe(shown)
    })

    it('approves after confirmation and returns to the review queue', async () => {
      confirmMock.mockResolvedValue(true)
      vi.mocked(precurationsAPI.approvePrecuration).mockResolvedValue({} as never)
      const wrapper = await mountReview('reviewer')
      await wrapper.find('[data-testid=approve-precuration]').trigger('click')
      await flushPromises()
      expect(precurationsAPI.approvePrecuration).toHaveBeenCalledWith('p1')
      expect(push).toHaveBeenCalledWith({ name: 'review-queue' })
    })

    it('requests changes with feedback and shows an API error in the dialog', async () => {
      vi.mocked(precurationsAPI.rejectPrecuration).mockRejectedValueOnce(new Error('Nope'))
      const wrapper = await mountReview('reviewer')
      await wrapper.find('[data-testid=reject-precuration]').trigger('click')
      await wrapper.find('textarea').setValue('Narrow the disease')
      await wrapper.find('[data-testid=reject-confirm]').trigger('click')
      await flushPromises()
      expect(precurationsAPI.rejectPrecuration).toHaveBeenCalledWith('p1', {
        reason: 'Narrow the disease'
      })
      expect(wrapper.text()).toContain('Nope')
      vi.mocked(precurationsAPI.rejectPrecuration).mockResolvedValue({} as never)
      await wrapper.find('[data-testid=reject-confirm]').trigger('click')
      await flushPromises()
      expect(push).toHaveBeenCalledWith({ name: 'review-queue' })
    })
  })
})
