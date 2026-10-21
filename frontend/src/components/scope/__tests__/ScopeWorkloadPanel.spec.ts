import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScopeWorkloadPanel from '../ScopeWorkloadPanel.vue'

const g = (id: string | null, name: string, stage: string) => ({
  curator_id: id,
  curator_name: name,
  stage
})

describe('ScopeWorkloadPanel', () => {
  it('counts open genes per curator, busiest first, ignoring active and unassigned', () => {
    const w = mount(ScopeWorkloadPanel, {
      props: {
        genes: [
          g('1', 'Alice', 'curation'),
          g('2', 'Carol', 'precuration'),
          g('2', 'Carol', 'review'),
          g('2', 'Carol', 'active'),
          g(null, '', 'unassigned')
        ]
      }
    })
    const rows = w.findAll('tbody tr').map(r => r.text())
    expect(rows).toEqual(['Carol2', 'Alice1'])
  })

  it('says so when nothing is assigned', () => {
    const w = mount(ScopeWorkloadPanel, { props: { genes: [g(null, '', 'unassigned')] } })
    expect(w.text()).toContain('No genes are assigned')
  })
})
