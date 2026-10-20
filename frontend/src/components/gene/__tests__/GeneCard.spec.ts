import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import GeneCard from '../GeneCard.vue'
import type { GeneRow } from '../types'
import type { GeneWorkflowStatus } from '../useGeneWorkflowStatus'

function gene(overrides: Partial<GeneRow> = {}): GeneRow {
  return {
    assignment_id: 'a-1',
    gene_id: 'g-1',
    gene_symbol: 'BRCA1',
    gene_name: 'BRCA1 DNA repair',
    gene_hgnc_id: 'HGNC:1100',
    curator_id: 'u-1',
    curator_name: 'Ada',
    priority: 'high',
    assignment_notes: '',
    status: 'in_progress',
    due_date: '2025-06-01',
    progress: 25,
    ...overrides
  }
}

function workflow(
  overrides: Partial<Record<keyof GeneWorkflowStatus, unknown>> = {}
): GeneWorkflowStatus {
  return {
    hasPrecuration: () => false,
    isPrecurationApproved: () => false,
    ...overrides
  } as unknown as GeneWorkflowStatus
}

describe('GeneCard', () => {
  it('renders symbol, status, curator, priority, due date and progress', () => {
    const wrapper = mount(GeneCard, { props: { gene: gene(), workflow: workflow() } })

    expect(wrapper.text()).toContain('BRCA1')
    expect(wrapper.text()).toContain('BRCA1 DNA repair')
    expect(wrapper.text()).toContain('In Progress')
    expect(wrapper.text()).toContain('Ada')
    expect(wrapper.text()).toContain('High')
    expect(wrapper.text()).toContain('Due:')
    expect(wrapper.text()).toContain('25%')
  })

  it('shows Unassigned and omits the due date when there is none', () => {
    const wrapper = mount(GeneCard, {
      props: { gene: gene({ curator_name: '', due_date: null }), workflow: workflow() }
    })

    expect(wrapper.text()).toContain('Unassigned')
    expect(wrapper.text()).not.toContain('Due:')
  })

  it('offers Start Precuration when none exists', async () => {
    const wrapper = mount(GeneCard, { props: { gene: gene(), workflow: workflow() } })

    const start = wrapper.findAll('button').find(b => b.text().includes('Start Precuration'))
    expect(start).toBeDefined()
    await start!.trigger('click')
    expect(wrapper.emitted('start-precuration')?.[0]).toEqual([gene()])
  })

  it('offers Complete Precuration when a precuration exists but is not approved', async () => {
    const wrapper = mount(GeneCard, {
      props: { gene: gene(), workflow: workflow({ hasPrecuration: () => true }) }
    })

    const button = wrapper.findAll('button').find(b => b.text().includes('Complete Precuration'))
    await button!.trigger('click')
    expect(wrapper.emitted('complete-precuration')).toHaveLength(1)
  })

  it('offers Start Curation when the precuration is approved', async () => {
    const wrapper = mount(GeneCard, {
      props: {
        gene: gene(),
        workflow: workflow({ hasPrecuration: () => true, isPrecurationApproved: () => true })
      }
    })

    const button = wrapper.findAll('button').find(b => b.text().includes('Start Curation'))
    await button!.trigger('click')
    expect(wrapper.emitted('start-curation')).toHaveLength(1)
  })

  it('emits view when the View button is clicked', async () => {
    const wrapper = mount(GeneCard, { props: { gene: gene(), workflow: workflow() } })

    await wrapper
      .findAll('button')
      .find(b => b.text().includes('View'))!
      .trigger('click')

    expect(wrapper.emitted('view')?.[0]).toEqual([gene()])
  })

  it('emits view when the symbol link is clicked', async () => {
    const wrapper = mount(GeneCard, { props: { gene: gene(), workflow: workflow() } })
    const spy = vi.fn()
    wrapper.vm.$emit = spy as never

    await wrapper.find('a.gene-link').trigger('click')

    expect(wrapper.emitted('view')).toHaveLength(1)
  })
})
