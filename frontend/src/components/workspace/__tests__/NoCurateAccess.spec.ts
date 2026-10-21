import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import NoCurateAccess from '../NoCurateAccess.vue'

describe('NoCurateAccess', () => {
  it('explains the missing role and links back to the scope', () => {
    const w = mount(NoCurateAccess, { props: { scopeId: 's1' } })
    expect(w.text()).toContain('curator or admin role')
    expect(w.findComponent({ name: 'VBtn' }).props('to')).toBe('/scopes/s1')
  })

  it('offers a retry when the role could not be checked', async () => {
    const w = mount(NoCurateAccess, { props: { scopeId: 's1', failed: true } })
    expect(w.text()).toContain('could not check')
    await w.find('[data-testid=retry-access]').trigger('click')
    expect(w.emitted('retry')).toHaveLength(1)
  })
})
