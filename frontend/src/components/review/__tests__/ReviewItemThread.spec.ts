import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ReviewItemThread from '../ReviewItemThread.vue'

describe('ReviewItemThread input', () => {
  it('limits a query to the API maximum and shows a counter', () => {
    const w = mount(ReviewItemThread, {
      props: { queries: [], me: 'u', creatorId: 'c', canReply: true }
    })
    expect(w.find('textarea').attributes('maxlength')).toBe('2000')
    expect(w.text()).toContain('/ 2000')
  })
})
