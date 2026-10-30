import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScopeWorkloadPanel from '../ScopeWorkloadPanel.vue'

const g = (id: string | null, name: string, stage: string) => ({
  curator_id: id,
  curator_name: name,
  stage
})

describe('ScopeWorkloadPanel', () => {
  it('counts assigned and open genes per curator, busiest first, ignoring unassigned', () => {
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
    expect(rows).toEqual(['Carol32', 'Alice11'])
  })

  it('lists a curator whose only assigned gene is active (W9 monkey)', () => {
    const w = mount(ScopeWorkloadPanel, { props: { genes: [g('1', 'Alice', 'active')] } })
    expect(w.findAll('tbody tr').map(r => r.text())).toEqual(['Alice10'])
    expect(w.text()).not.toContain('No genes are assigned')
  })

  it('says so when nothing is assigned', () => {
    const w = mount(ScopeWorkloadPanel, { props: { genes: [g(null, '', 'unassigned')] } })
    expect(w.text()).toContain('No genes are assigned')
  })
})
