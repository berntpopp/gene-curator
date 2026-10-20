import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const replace = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ replace, back: vi.fn() })
}))

import CreateAssignment from '@/views/CreateAssignment.vue'

describe('CreateAssignment view', () => {
  beforeEach(() => replace.mockClear())

  it('shows the redirect message and redirects to scope selection on mount', () => {
    const wrapper = mount(CreateAssignment)
    expect(wrapper.text()).toContain('Redirecting to assignment creation flow')
    expect(replace).toHaveBeenCalledWith({ name: 'ScopeSelection' })
  })
})
