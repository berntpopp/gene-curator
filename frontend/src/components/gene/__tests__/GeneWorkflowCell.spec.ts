import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import GeneWorkflowCell from '../GeneWorkflowCell.vue'
import type { GeneRow } from '../types'
import type { GeneWorkflowStatus } from '../useGeneWorkflowStatus'

describe('GeneWorkflowCell', () => {
  it('labels a submitted curation with the shared status label', () => {
    const workflow = {
      isCurationActive: () => false,
      hasPrecuration: () => false,
      isPrecurationApproved: () => false,
      hasCuration: () => true,
      getCuration: () => ({ status: 'submitted' }),
      getCurationStatusLabel: () => ''
    } as unknown as GeneWorkflowStatus
    const wrapper = mount(GeneWorkflowCell, {
      props: { gene: { gene_id: 'g' } as GeneRow, workflow }
    })
    expect(wrapper.text()).toContain('Submitted')
    expect(wrapper.text()).not.toContain('Awaiting Review')
  })
})
