import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AgreementBanner from '../AgreementBanner.vue'

const mountIt = (props: InstanceType<typeof AgreementBanner>['$props']) =>
  mount(AgreementBanner, { props })

describe('AgreementBanner', () => {
  it('says scopes agree, naming the classification', () => {
    const wrapper = mountIt({
      scopeCount: 2,
      hasConflicts: false,
      consensus: 'definitive',
      classifications: { definitive: 2 }
    })
    expect(wrapper.text()).toContain('Both scopes agree')
    expect(wrapper.text()).toContain('Definitive')
    expect(wrapper.find('[role="status"]').exists()).toBe(true)
  })

  it('names the count when more than two scopes agree', () => {
    const wrapper = mountIt({
      scopeCount: 3,
      hasConflicts: false,
      consensus: 'strong',
      classifications: { strong: 3 }
    })
    expect(wrapper.text()).toContain('All 3 scopes agree')
  })

  it('shows a disagreement banner listing the classifications', () => {
    const wrapper = mountIt({
      scopeCount: 3,
      hasConflicts: true,
      consensus: null,
      classifications: { definitive: 1, disputed: 2 }
    })
    expect(wrapper.text()).toContain('Scopes disagree')
    expect(wrapper.text()).toContain('Definitive')
    expect(wrapper.text()).toContain('Disputed')
    expect(wrapper.find('[role="alert"]').exists()).toBe(true)
  })

  it('renders nothing for a single scope', () => {
    expect(mountIt({ scopeCount: 1, hasConflicts: false, classifications: {} }).html()).toBe(
      '<!--v-if-->'
    )
  })
})
