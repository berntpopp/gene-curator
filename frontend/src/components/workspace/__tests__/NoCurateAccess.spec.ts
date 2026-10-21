import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import NoCurateAccess from '../NoCurateAccess.vue'

describe('NoCurateAccess', () => {
  it('explains the missing role and links back to the scope', () => {
    const w = mount(NoCurateAccess, { props: { scopeId: 's1' } })
    expect(w.text()).toContain('curator or admin role')
    expect(w.findComponent({ name: 'VBtn' }).props('to')).toBe('/scopes/s1')
  })
})
