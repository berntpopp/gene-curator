import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import GeneRowActions from '../GeneRowActions.vue'
import type { GeneRow } from '../types'
import type { GeneWorkflowStatus } from '../useGeneWorkflowStatus'

const gene: GeneRow = {
  assignment_id: 'a-1',
  gene_id: 'g-1',
  gene_symbol: 'BRCA1',
  gene_hgnc_id: '',
  curator_id: null,
  curator_name: '',
  priority: 'medium',
  assignment_notes: '',
  stage: 'precuration',
  due_date: null,
  updated_at: '2026-10-20T00:00:00Z'
}

function workflow(overrides: Record<string, unknown> = {}): GeneWorkflowStatus {
  return {
    hasPrecuration: () => false,
    isPrecurationApproved: () => false,
    hasCuration: () => false,
    isCurationActive: () => false,
    getCurationStatusLabel: () => 'No Curation',
    ...overrides
  } as unknown as GeneWorkflowStatus
}

// v-menu needs visualViewport (not in happy-dom), so render its content inline.
const inlineMenu = {
  VMenu: { template: '<div><slot name="activator" :props="{}" /><slot /></div>' }
}

function menuItems(wrapper: ReturnType<typeof mount>) {
  return wrapper.findAll('.v-list-item')
}

describe('GeneRowActions', () => {
  it('shows precuration start and admin actions when the user can manage genes', () => {
    const wrapper = mount(GeneRowActions, {
      props: {
        gene,
        workflow: workflow(),
        canAssignGenes: true,
        canReassign: true,
        canRemoveGenes: true
      },
      global: { stubs: inlineMenu }
    })

    const text = wrapper.text()
    expect(text).toContain('Start Precuration')
    expect(text).toContain('Reassign')
    expect(text).toContain('Edit Assignment')
    expect(text).toContain('Remove from Scope')
  })

  it('hides assignment and removal actions for read-only users', () => {
    const wrapper = mount(GeneRowActions, {
      props: { gene, workflow: workflow(), canAssignGenes: true, canRemoveGenes: false },
      global: { stubs: inlineMenu }
    })

    const text = wrapper.text()
    expect(text).toContain('Start Precuration')
    expect(text).not.toContain('Reassign')
    expect(text).not.toContain('Remove from Scope')
  })

  it('hides Reassign and Edit Assignment unless the user may reassign', () => {
    const wrapper = mount(GeneRowActions, {
      props: { gene, workflow: workflow(), canAssignGenes: true, canRemoveGenes: false },
      global: { stubs: inlineMenu }
    })

    expect(wrapper.text()).not.toContain('Reassign')
    expect(wrapper.text()).not.toContain('Edit Assignment')
  })

  it('offers Complete Precuration instead of Start when a precuration is pending', () => {
    const wrapper = mount(GeneRowActions, {
      props: {
        gene,
        workflow: workflow({ hasPrecuration: () => true }),
        canAssignGenes: true,
        canRemoveGenes: false
      },
      global: { stubs: inlineMenu }
    })

    expect(wrapper.text()).toContain('Complete Precuration')
    expect(wrapper.text()).not.toContain('Start Precuration')
  })

  it('shows a disabled curation hint until the precuration is approved', () => {
    const wrapper = mount(GeneRowActions, {
      props: { gene, workflow: workflow(), canAssignGenes: true, canRemoveGenes: false },
      global: { stubs: inlineMenu }
    })

    expect(wrapper.text()).toContain('requires approved precuration')
  })

  it('emits the chosen action with the gene', async () => {
    const wrapper = mount(GeneRowActions, {
      props: {
        gene,
        workflow: workflow({
          hasPrecuration: () => true,
          isPrecurationApproved: () => true,
          hasCuration: () => true,
          getCurationStatusLabel: () => 'Active'
        }),
        canAssignGenes: true,
        canReassign: true,
        canRemoveGenes: true
      },
      global: { stubs: inlineMenu }
    })

    const click = async (label: string) => {
      const item = menuItems(wrapper).find(i => i.text().includes(label))
      expect(item, label).toBeDefined()
      await item!.trigger('click')
    }

    await click('View Curation')
    await click('Reassign')
    await click('Edit Assignment')
    await click('Remove from Scope')

    expect(wrapper.emitted('view-curation')?.[0]).toEqual([gene])
    expect(wrapper.emitted('reassign')?.[0]).toEqual([gene])
    expect(wrapper.emitted('edit-assignment')?.[0]).toEqual([gene])
    expect(wrapper.emitted('remove')?.[0]).toEqual([gene])
  })

  it('offers Start Curation once the precuration is approved and no curation exists', async () => {
    const wrapper = mount(GeneRowActions, {
      props: {
        gene,
        workflow: workflow({ hasPrecuration: () => true, isPrecurationApproved: () => true }),
        canAssignGenes: true,
        canRemoveGenes: false
      },
      global: { stubs: inlineMenu }
    })

    await menuItems(wrapper)
      .find(i => i.text().includes('Start Curation'))!
      .trigger('click')

    expect(wrapper.emitted('start-curation')?.[0]).toEqual([gene])
  })

  it('emits start and complete precuration actions', async () => {
    const start = mount(GeneRowActions, {
      props: { gene, workflow: workflow(), canAssignGenes: true, canRemoveGenes: false },
      global: { stubs: inlineMenu }
    })
    await menuItems(start)
      .find(i => i.text().includes('Start Precuration'))!
      .trigger('click')
    expect(start.emitted('start-precuration')?.[0]).toEqual([gene])

    const complete = mount(GeneRowActions, {
      props: {
        gene,
        workflow: workflow({ hasPrecuration: () => true }),
        canAssignGenes: true,
        canRemoveGenes: false
      },
      global: { stubs: inlineMenu }
    })
    await menuItems(complete)
      .find(i => i.text().includes('Complete Precuration'))!
      .trigger('click')
    expect(complete.emitted('complete-precuration')?.[0]).toEqual([gene])
  })

  it('disables the start actions with the given reason', () => {
    const wrapper = mount(GeneRowActions, {
      props: {
        gene,
        workflow: workflow(),
        canAssignGenes: true,
        canRemoveGenes: false,
        startBlockedReason: 'This scope has no methodology yet'
      },
      global: { stubs: inlineMenu }
    })

    const start = menuItems(wrapper).find(i => i.text().includes('Start Precuration'))
    expect(start?.classes()).toContain('v-list-item--disabled')
    expect(start?.text()).toContain('This scope has no methodology yet')
  })

  it.each([
    ['no precuration', workflow()],
    ['open precuration', workflow({ hasPrecuration: () => true })],
    [
      'approved precuration',
      workflow({ hasPrecuration: () => true, isPrecurationApproved: () => true })
    ]
  ])('hides start/complete/curation actions from non-curators (%s)', (_name, wf) => {
    const wrapper = mount(GeneRowActions, {
      props: { gene, workflow: wf, canAssignGenes: false, canRemoveGenes: false },
      global: { stubs: inlineMenu }
    })
    expect(wrapper.text()).not.toMatch(
      /Start Precuration|Complete Precuration|Start Curation|Curation \(requires/
    )
  })

  it('offers a re-curation for an active curation to users who may curate', async () => {
    const active = workflow({
      hasCuration: () => true,
      isCurationActive: () => true,
      getCurationStatusLabel: () => 'Active'
    })
    const mk = (canAssignGenes: boolean) =>
      mount(GeneRowActions, {
        props: { gene, workflow: active, canAssignGenes, canRemoveGenes: false },
        global: { stubs: inlineMenu }
      })
    const wrapper = mk(true)
    const item = menuItems(wrapper).find(i => i.text().includes('Start re-curation'))
    await item!.trigger('click')
    expect(wrapper.emitted('start-recuration')).toEqual([[gene]])
    expect(mk(false).text()).not.toContain('Start re-curation')
  })
})
