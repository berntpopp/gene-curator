/**
 * ScopeOverview Tests
 *
 * Scope information rows and the statistics cards, including the zero
 * fallbacks for missing counters.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScopeOverview from '../ScopeOverview.vue'

const scope = {
  name: 'kidney',
  display_name: 'Kidney Genetics',
  description: 'Renal genes',
  institution: 'Charité',
  is_public: true,
  is_active: true
}

describe('ScopeOverview', () => {
  it('shows the scope information rows', () => {
    const wrapper = mount(ScopeOverview, { props: { scope } })

    expect(wrapper.text()).toContain('kidney')
    expect(wrapper.text()).toContain('Kidney Genetics')
    expect(wrapper.text()).toContain('Renal genes')
    expect(wrapper.text()).toContain('Charité')
    expect(wrapper.text()).toContain('Public')
    expect(wrapper.text()).toContain('Active')
  })

  it('omits optional rows and shows private/inactive state', () => {
    const wrapper = mount(ScopeOverview, {
      props: {
        scope: { ...scope, description: '', institution: null, is_public: false, is_active: false }
      }
    })

    expect(wrapper.text()).not.toContain('Description')
    expect(wrapper.text()).not.toContain('Institution')
    expect(wrapper.text()).toContain('Private')
    expect(wrapper.text()).toContain('Inactive')
  })

  it('hides the statistics and activity cards without statistics', () => {
    const wrapper = mount(ScopeOverview, { props: { scope } })

    expect(wrapper.text()).not.toContain('Statistics')
    expect(wrapper.text()).not.toContain('Recent Activity')
  })

  it('shows the counters and treats missing ones as zero', () => {
    const wrapper = mount(ScopeOverview, {
      props: {
        scope,
        statistics: {
          total_genes_assigned: 12,
          genes_with_curator: 7,
          total_curations: 4,
          active_reviewers: 2,
          curations_last_30_days: 3
        }
      }
    })

    expect(wrapper.text()).toContain('Total Genes')
    expect(wrapper.text()).toContain('12')
    expect(wrapper.text()).toContain('Curations Created')
    expect(wrapper.text()).toContain('Total Precurations')
    expect(wrapper.text()).toContain('Active Reviewers')
    expect(wrapper.text()).toContain('Curations Activated')
  })
})
