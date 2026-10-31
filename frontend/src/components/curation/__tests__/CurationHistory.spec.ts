/** #593: the history names who submitted and approved, and the AI agent of an MCP submit. */
import { describe, it, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const entries = [
  {
    id: 'a',
    item_id: 'c1',
    item_type: 'curation',
    from_stage: 'curation',
    to_stage: 'review',
    executed_by: 'u1',
    executed_by_name: 'Alice',
    executed_at: '2026-10-02T09:00:00Z',
    notes: null,
    metadata: {
      agent: { model: 'claude-opus-5-5', agent: 'Claude Code', tools_used: ['gnomad'] }
    }
  },
  {
    id: 'b',
    item_id: 'c1',
    item_type: 'curation',
    from_stage: 'review',
    to_stage: 'active',
    executed_by: 'u2',
    executed_by_name: 'Bob',
    executed_at: '2026-10-03T09:00:00Z',
    notes: 'Looks good',
    metadata: { decision: 'approve' }
  }
]
const fetchStageHistory = vi.fn(async () => entries)
vi.mock('@/stores/workflow', () => ({
  useWorkflowStore: () => ({ fetchStageHistory, getStageHistory: () => entries })
}))

import CurationHistory from '../CurationHistory.vue'

describe('CurationHistory', () => {
  it('lists submissions with the agent and approvals by a person', async () => {
    const w = mount(CurationHistory, { props: { curationId: 'c1' } })
    await flushPromises()
    expect(fetchStageHistory).toHaveBeenCalledWith('c1')
    const items = w.findAll('li').map(li => li.text().replace(/\s+/g, ' '))
    expect(items[0]).toMatch(/Submitted by Alice via Claude Code \(claude-opus-5-5\) using gnomad/)
    expect(items[1]).toMatch(/Approved by Bob/)
    expect(items[1]).toContain('Looks good')
  })
})
