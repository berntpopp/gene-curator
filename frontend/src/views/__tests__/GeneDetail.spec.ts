import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises, RouterLinkStub } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('@/api', () => ({
  genesAPI: { getGeneById: vi.fn() },
  externalValidationAPI: { fetchHGNCGene: vi.fn() }
}))

vi.mock('@/api/geneSummary', () => ({
  geneSummaryAPI: { getPublicSummary: vi.fn(), getFullSummary: vi.fn() }
}))

const { push, back } = vi.hoisted(() => ({ push: vi.fn(), back: vi.fn() }))
vi.mock('vue-router', async () => {
  const { reactive } = await import('vue')
  const route = reactive({ params: { id: 'gene-1' } })
  return { useRoute: () => route, useRouter: () => ({ push, back }) }
})

import { genesAPI, externalValidationAPI } from '@/api'
import { geneSummaryAPI } from '@/api/geneSummary'
import { useGenesStore } from '@/stores/genes'
import { useAuthStore } from '@/stores/auth'
import GeneDetail from '@/views/GeneDetail.vue'
import { useRoute } from 'vue-router'

const localGene = {
  id: 'gene-1',
  hgnc_id: 'HGNC:1100',
  approved_symbol: 'BRCA1',
  chromosome: '17',
  location: '17q21.31',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-02T00:00:00Z',
  alias_symbols: ['RNF53'],
  previous_symbols: []
}

const scope = (over = {}) => ({
  scope_id: 's1',
  scope_name: 'Kidney genetics',
  is_public: true,
  classification: 'definitive',
  curation_id: 'c1',
  disease_name: 'Polycystic kidney disease 1',
  mode_of_inheritance: 'AD',
  stage: 'active',
  in_progress: false,
  genetic_score: 10,
  experimental_score: 6,
  total_score: 16,
  last_updated: '2026-10-17T10:00:00Z',
  curator_count: 1,
  evidence_count: 3,
  ...over
})
const summaryOf = (scopes: unknown[], over = {}) => ({
  gene_id: 'gene-1',
  public_scopes_count: scopes.length,
  classification_summary: { definitive: scopes.length },
  consensus_classification: 'definitive',
  has_conflicts: false,
  scope_summaries: scopes,
  last_updated: '2026-10-17T10:00:00Z',
  ...over
})

const mountView = () => mount(GeneDetail, { global: { stubs: { RouterLink: RouterLinkStub } } })

describe('GeneDetail view', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(genesAPI.getGeneById).mockReset()
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockReset()
    vi.mocked(geneSummaryAPI.getPublicSummary).mockReset().mockResolvedValue(null)
    vi.mocked(geneSummaryAPI.getFullSummary).mockReset()
    push.mockReset()
    back.mockReset()
  })

  it('shows a loading state while the gene is fetched', () => {
    vi.mocked(genesAPI.getGeneById).mockReturnValue(new Promise(() => {}))
    const wrapper = mountView()
    expect(wrapper.text()).toContain('Loading gene information...')
  })

  it('shows an error when the gene cannot be loaded', async () => {
    vi.mocked(genesAPI.getGeneById).mockRejectedValue(new Error('404'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('Failed to load gene information')
    expect(wrapper.text()).toContain('Failed to load gene details')
  })

  it.each([400, 422])('says "Gene not found" for an invalid id (%i)', async status => {
    vi.mocked(genesAPI.getGeneById).mockRejectedValue({ response: { status } })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('Gene not found')
    expect(wrapper.text()).not.toContain('Retry')
  })

  it('says "Gene not found" with a catalogue link on a 404', async () => {
    vi.mocked(genesAPI.getGeneById).mockRejectedValue({ response: { status: 404 } })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).toContain('Gene not found')
    expect(wrapper.text()).not.toContain('Retry')
  })

  it('offers Retry on other failures and reloads the gene', async () => {
    vi.mocked(genesAPI.getGeneById)
      .mockRejectedValueOnce({ response: { status: 500 } })
      .mockResolvedValueOnce(localGene as never)
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({ results: [] } as never)
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).not.toContain('Gene not found')
    await wrapper.find('button.retry').trigger('click')
    await flushPromises()
    expect(wrapper.find('h1').text()).toBe('BRCA1')
  })

  it('does not call HGNC when signed out (the endpoint needs login)', async () => {
    vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
    const wrapper = mountView()
    await flushPromises()
    expect(externalValidationAPI.fetchHGNCGene).not.toHaveBeenCalled()
    expect(wrapper.find('h1').text()).toBe('BRCA1')
  })

  it('renders HGNC data when the lookup succeeds', async () => {
    useAuthStore().isAuthenticated = true
    vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({
      results: [
        { hgnc_id: 'HGNC:1100', symbol: 'BRCA1', name: 'BRCA1 DNA repair', status: 'Approved' }
      ]
    } as never)
    const wrapper = mountView()
    await flushPromises()
    expect(externalValidationAPI.fetchHGNCGene).toHaveBeenCalledWith('HGNC:1100')
    expect(wrapper.find('h1').text()).toBe('BRCA1')
    expect(wrapper.text()).toContain('BRCA1 DNA repair')
    expect(wrapper.text()).toContain('RNF53')
  })

  it('keeps showing local data when the HGNC lookup fails', async () => {
    useAuthStore().isAuthenticated = true
    vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockRejectedValue(new Error('down'))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('h1').text()).toBe('BRCA1')
    expect(wrapper.text()).not.toContain('Failed to load gene information')
    expect(wrapper.text()).toContain('17q21.31')
  })

  it('loads the gene for the route id via the store', async () => {
    vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({ results: [] } as never)
    mountView()
    await flushPromises()
    expect(genesAPI.getGeneById).toHaveBeenCalledWith('gene-1')
    expect(useGenesStore().currentGene).toEqual(localGene)
  })

  it('reloads when the route id changes', async () => {
    vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({ results: [] } as never)
    mountView()
    await flushPromises()
    expect(genesAPI.getGeneById).toHaveBeenLastCalledWith('gene-1')

    useRoute().params = { id: 'gene-2' }
    await flushPromises()
    expect(genesAPI.getGeneById).toHaveBeenLastCalledWith('gene-2')
  })

  it('renders the local gene at once while a slow HGNC lookup is still pending', async () => {
    vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
    vi.mocked(externalValidationAPI.fetchHGNCGene).mockReturnValue(new Promise(() => {}))
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.text()).not.toContain('Loading gene information')
    expect(wrapper.find('h1').text()).toBe('BRCA1')
    expect(wrapper.text()).toContain('17q21.31')
  })

  describe('out-of-order responses', () => {
    const deferred = <T>() => {
      let resolve!: (v: T) => void
      const promise = new Promise<T>(r => (resolve = r))
      return { promise, resolve }
    }

    it('ignores a slow gene A response after navigating to gene B', async () => {
      useRoute().params = { id: 'gene-1' }
      const a = deferred<unknown>()
      const b = deferred<unknown>()
      vi.mocked(genesAPI.getGeneById).mockImplementation(
        ((id: string) => (id === 'gene-1' ? a : b).promise) as never
      )
      vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({ results: [] } as never)
      const wrapper = mountView()
      useRoute().params = { id: 'gene-2' }
      await flushPromises()
      b.resolve({ ...localGene, id: 'gene-2', approved_symbol: 'TP53', hgnc_id: 'HGNC:11998' })
      await flushPromises()
      a.resolve(localGene)
      await flushPromises()
      expect(wrapper.find('h1').text()).toBe('TP53')
      expect(externalValidationAPI.fetchHGNCGene).not.toHaveBeenCalledWith('HGNC:1100')
      expect(geneSummaryAPI.getPublicSummary).not.toHaveBeenCalledWith('gene-1')
    })

    it('ignores a slow gene A summary after navigating to gene B', async () => {
      useRoute().params = { id: 'gene-1' }
      const a = deferred<unknown>()
      vi.mocked(genesAPI.getGeneById).mockImplementation((async (id: string) =>
        id === 'gene-1'
          ? localGene
          : { ...localGene, id: 'gene-2', approved_symbol: 'TP53' }) as never)
      vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({ results: [] } as never)
      vi.mocked(geneSummaryAPI.getPublicSummary).mockImplementation(((id: string) =>
        id === 'gene-1' ? a.promise : Promise.resolve(null)) as never)
      const wrapper = mountView()
      await flushPromises()
      useRoute().params = { id: 'gene-2' }
      await flushPromises()
      a.resolve(summaryOf([scope()]))
      await flushPromises()
      expect(wrapper.text()).toContain('No curations yet')
      expect(wrapper.text()).not.toContain('Kidney genetics')
    })
  })

  describe('curations', () => {
    beforeEach(() => {
      vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
      vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({ results: [] } as never)
    })

    it('signed out: loads the public summary and shows unlinked assertions', async () => {
      vi.mocked(geneSummaryAPI.getPublicSummary).mockResolvedValue(summaryOf([scope()]) as never)
      const wrapper = mountView()
      await flushPromises()
      expect(geneSummaryAPI.getFullSummary).not.toHaveBeenCalled()
      expect(wrapper.text()).toContain('Kidney genetics')
      expect(wrapper.text()).toContain('Polycystic kidney disease 1')
      expect(wrapper.findAll('a[href]').every(a => a.attributes('target') === '_blank')).toBe(true)
    })

    it('signed in: loads the full summary with a link to the curation', async () => {
      useAuthStore().isAuthenticated = true
      vi.mocked(geneSummaryAPI.getFullSummary).mockResolvedValue(
        summaryOf(
          [scope(), scope({ scope_id: 's2', scope_name: 'Cystic panel', curation_id: 'c2' })],
          {
            total_scopes_curated: 3
          }
        ) as never
      )
      const wrapper = mountView()
      await flushPromises()
      expect(geneSummaryAPI.getPublicSummary).not.toHaveBeenCalled()
      expect(wrapper.text()).toContain('Both scopes agree')
      expect(wrapper.text()).not.toContain('you cannot see.')
      expect(wrapper.findAllComponents(RouterLinkStub).map(l => l.props('to'))).toContainEqual({
        name: 'curation-detail',
        params: { scopeId: 's1', curationId: 'c1' }
      })
    })

    it('counts only active rows: an in-progress row in the same scope is not a second scope', async () => {
      vi.mocked(geneSummaryAPI.getPublicSummary).mockResolvedValue(
        summaryOf([scope(), scope({ stage: 'curation', in_progress: true, curation_id: 'c9' })], {
          classification_summary: { definitive: 1 }
        }) as never
      )
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).not.toContain('Both scopes agree')
      expect(wrapper.findAll('tbody tr')).toHaveLength(2)
    })

    it('shows a disagreement banner', async () => {
      vi.mocked(geneSummaryAPI.getPublicSummary).mockResolvedValue(
        summaryOf([scope(), scope({ scope_id: 's2', classification: 'disputed' })], {
          has_conflicts: true,
          consensus_classification: null,
          classification_summary: { definitive: 1, disputed: 1 }
        }) as never
      )
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).toContain('Scopes disagree')
    })

    it.each([
      [false, 'No public scope has curated this gene.'],
      [true, 'No scope you can see has curated this gene.']
    ])('empty state (signed in: %s)', async (signedIn, message) => {
      useAuthStore().isAuthenticated = signedIn
      vi.mocked(geneSummaryAPI.getFullSummary).mockRejectedValue({ response: { status: 404 } })
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).toContain('No curations yet')
      expect(wrapper.text()).toContain(message)
    })

    it('a failing summary does not hide the gene and offers a retry', async () => {
      vi.mocked(geneSummaryAPI.getPublicSummary).mockRejectedValueOnce(new Error('down'))
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.find('h1').text()).toBe('BRCA1')
      expect(wrapper.text()).toContain('Could not load the curations for this gene.')
      vi.mocked(geneSummaryAPI.getPublicSummary).mockResolvedValue(summaryOf([scope()]) as never)
      await wrapper
        .findAll('button')
        .find(b => b.text() === 'Retry')!
        .trigger('click')
      await flushPromises()
      expect(wrapper.text()).toContain('Kidney genetics')
    })
  })

  describe('page chrome', () => {
    beforeEach(() => {
      vi.mocked(genesAPI.getGeneById).mockResolvedValue(localGene as never)
      vi.mocked(externalValidationAPI.fetchHGNCGene).mockResolvedValue({ results: [] } as never)
    })

    it('links to more than HGNC, safely', async () => {
      const wrapper = mountView()
      await flushPromises()
      const links = wrapper.findAll('nav a')
      expect(links.map(l => l.text())).toEqual(
        expect.arrayContaining(['HGNC', 'OMIM', 'ClinGen', 'GenCC', 'PanelApp', 'gnomAD', 'PubMed'])
      )
      expect(links.every(l => l.attributes('rel') === 'noopener noreferrer')).toBe(true)
    })

    it('shows the internal id only to admins', async () => {
      const wrapper = mountView()
      await flushPromises()
      expect(wrapper.text()).not.toContain('gene-1')
      useAuthStore().user = { id: 'u', role: 'admin' } as never
      await flushPromises()
      expect(wrapper.text()).toContain('gene-1')
    })

    it('Back returns to where the user came from, else to the catalogue', async () => {
      const wrapper = mountView()
      await flushPromises()
      window.history.replaceState({ back: '/scopes/s1' }, '')
      await wrapper.find('button[aria-label="Back"]').trigger('click')
      expect(back).toHaveBeenCalled()
      window.history.replaceState({}, '')
      await wrapper.find('button[aria-label="Back"]').trigger('click')
      expect(push).toHaveBeenCalledWith({ name: 'GeneCatalogue' })
    })
  })
})
