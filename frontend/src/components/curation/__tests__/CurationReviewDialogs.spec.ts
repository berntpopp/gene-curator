import { afterEach, describe, expect, it } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import CurationReviewDialogs from '../CurationReviewDialogs.vue'

const base = {
  approveOpen: true,
  rejectOpen: false,
  geneSymbol: 'PKD1',
  classification: 'Strong',
  scores: { total: 9, genetic: 7, experimental: 2 },
  summary: 'Narrative text',
  counts: 'Genetic: 3 items',
  busy: false,
  errorDetail: null
}
let wrapper: VueWrapper
async function mountIt(props = {}) {
  wrapper = mount(CurationReviewDialogs, {
    props: { ...base, ...props },
    attachTo: document.body
  })
  await flushPromises()
}
const button = (label: string) =>
  [...document.body.querySelectorAll('button')].find(b => b.textContent?.trim() === label)
const vm = () => wrapper.vm as unknown as { approveComment: string; rejectComment: string }

afterEach(() => wrapper.unmount())

describe('CurationReviewDialogs', () => {
  it('shows the narrative and evidence counts in the approve dialog', async () => {
    await mountIt()
    expect(document.body.textContent).toContain('Narrative text')
    expect(document.body.textContent).toContain('Genetic: 3 items')
  })

  it('shows the API error inline inside the dialog', async () => {
    await mountIt({ errorDetail: 'Notification failed' })
    expect(document.body.textContent).toContain('Notification failed')
  })

  it('emits approve with the approve comment only', async () => {
    await mountIt()
    vm().rejectComment = 'other'
    vm().approveComment = 'LGTM'
    await flushPromises()
    button('Approve')?.click()
    expect(wrapper.emitted('approve')?.[0]).toEqual(['LGTM'])
  })

  it('requires feedback before requesting changes and says why', async () => {
    await mountIt({ approveOpen: false, rejectOpen: true })
    expect(document.body.textContent).toContain('Feedback is required')
    expect(button('Request Changes')?.disabled).toBe(true)
    vm().rejectComment = 'Fix PMID'
    await flushPromises()
    button('Request Changes')?.click()
    expect(wrapper.emitted('reject')?.[0]).toEqual(['Fix PMID'])
  })
})
