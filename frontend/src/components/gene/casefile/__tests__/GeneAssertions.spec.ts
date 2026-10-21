import { describe, it, expect, vi } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import GeneAssertions from '../GeneAssertions.vue'
import type { Schema } from '@/types/api'

type ScopeSummary = Schema<'ScopeSummary'>

const row = (over: Partial<ScopeSummary> = {}): ScopeSummary => ({
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
  experimental_score: 6.5,
  total_score: 16.5,
  last_updated: '2026-10-17T10:00:00Z',
  curator_count: 2,
  evidence_count: 5,
  ...over
})

const mountIt = (scopes: ScopeSummary[], linked = true) =>
  mount(GeneAssertions, {
    props: { scopes, linked },
    global: { stubs: { RouterLink: RouterLinkStub } }
  })

describe('GeneAssertions', () => {
  it('shows scope, disease, MOI, stage, classification, score and date per scope', () => {
    const wrapper = mountIt([row()])
    const text = wrapper.text()
    expect(text).toContain('Kidney genetics')
    expect(text).toContain('Polycystic kidney disease 1')
    expect(text).toContain('AD')
    expect(text).toContain('Active')
    expect(text).toContain('Definitive')
    expect(text).toContain('16.5')
    expect(text).toContain('2026-10-17')
  })

  it('links the scope and the curation when signed in', () => {
    const links = mountIt([row()]).findAllComponents(RouterLinkStub)
    const targets = links.map(l => l.props('to'))
    expect(targets).toContainEqual({ name: 'scope-dashboard', params: { scopeId: 's1' } })
    expect(targets).toContainEqual({
      name: 'curation-detail',
      params: { scopeId: 's1', curationId: 'c1' }
    })
  })

  it('shows no links for signed-out visitors', () => {
    const wrapper = mountIt([row()], false)
    expect(wrapper.findAllComponents(RouterLinkStub)).toHaveLength(0)
    expect(wrapper.text()).toContain('Kidney genetics')
  })

  it('marks a member in-progress curation and tolerates missing fields', () => {
    const wrapper = mountIt([
      row({
        in_progress: true,
        stage: 'review',
        curation_id: null,
        disease_name: null,
        mode_of_inheritance: null,
        classification: null
      })
    ])
    expect(wrapper.text()).toContain('In review')
    expect(wrapper.text()).toContain('in progress')
    expect(wrapper.text()).toContain('—')
    expect(wrapper.findAllComponents(RouterLinkStub).map(l => l.props('to'))).toEqual([
      { name: 'scope-dashboard', params: { scopeId: 's1' } }
    ])
  })

  it('renders an active and an in-progress row of the same scope without key clashes', async () => {
    const warn = vi.fn()
    const wrapper = mount(GeneAssertions, {
      props: {
        scopes: [row({ scope_id: 's0' }), row({ scope_id: 'sA' }), row({ scope_id: 's9' })],
        linked: true
      },
      global: { stubs: { RouterLink: RouterLinkStub }, config: { warnHandler: warn } }
    })
    // Vue only checks keys when it patches an existing list
    await wrapper.setProps({
      scopes: [
        row({ scope_id: 's0' }),
        row(),
        row({ curation_id: 'c2', stage: 'curation', in_progress: true }),
        row({ scope_id: 's9' })
      ]
    })
    expect(warn).not.toHaveBeenCalled()
    expect(wrapper.findAll('tbody tr')).toHaveLength(4)
  })
})
