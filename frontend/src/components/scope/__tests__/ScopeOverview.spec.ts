/**
 * ScopeOverview Tests
 *
 * Scope information rows and the statistics cards, including the zero
 * fallbacks for missing counters.
 */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScopeOverview from '../ScopeOverview.vue'

const scope = { institution: 'Charité' }

describe('ScopeOverview', () => {
  it('shows methodology, scope admins and institution in a definition list', () => {
    const wrapper = mount(ScopeOverview, {
      props: { scope, methodology: 'ClinGen SOP v11', admins: ['Mara König', 'Bob'] }
    })

    expect(wrapper.find('dl').exists()).toBe(true)
    expect(wrapper.text()).toContain('ClinGen SOP v11')
    expect(wrapper.text()).toContain('Mara König, Bob')
    expect(wrapper.text()).toContain('Charité')
    expect(wrapper.text()).not.toContain('Visibility')
  })

  it('shows dashes without methodology or admins and omits the institution', () => {
    const wrapper = mount(ScopeOverview, { props: { scope: { institution: null } } })

    expect(wrapper.text()).toContain('Methodology—')
    expect(wrapper.text()).toContain('Scope admins—')
    expect(wrapper.text()).not.toContain('Institution')
  })

  it('hides the statistics and activity cards without statistics', () => {
    const wrapper = mount(ScopeOverview, { props: { scope } })

    expect(wrapper.text()).not.toContain('Statistics')
    expect(wrapper.text()).not.toContain('Recent Activity')
  })

  it('shows only recent activity, not a second copy of the dashboard tiles', () => {
    const wrapper = mount(ScopeOverview, {
      props: { scope, statistics: { total_genes_assigned: 12, curations_last_30_days: 3 } }
    })

    expect(wrapper.text()).not.toContain('Total Genes')
    expect(wrapper.text()).toContain('Curations Created')
    expect(wrapper.text()).toContain('Curations Activated')
  })
})
