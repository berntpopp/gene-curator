import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScopeStageStrip from '../ScopeStageStrip.vue'

const counts = { unassigned: 4, precuration: 3, curation: 6, review: 2, active: 18 }

describe('ScopeStageStrip', () => {
  it('shows a count per stage', () => {
    const w = mount(ScopeStageStrip, { props: { counts } })
    expect(w.find('[data-testid=stage-curation]').text()).toContain('6')
    expect(w.find('[data-testid=stage-active]').text()).toContain('18')
  })

  it('selects a stage on click and clears it on a second click', async () => {
    const w = mount(ScopeStageStrip, { props: { counts } })
    await w.find('[data-testid=stage-review]').trigger('click')
    expect(w.emitted('update:modelValue')![0]).toEqual(['review'])
    await w.setProps({ modelValue: 'review' })
    expect(w.find('[data-testid=stage-review]').attributes('aria-pressed')).toBe('true')
    await w.find('[data-testid=stage-review]').trigger('click')
    expect(w.emitted('update:modelValue')![1]).toEqual([undefined])
  })
})
