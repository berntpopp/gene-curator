import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PubmedLinkButton from '../PubmedLinkButton.vue'
import PubmedLinkChip from '@/components/forms/PubmedLinkChip.vue'

const href = (pmid: unknown) =>
  mount(PubmedLinkButton, { props: { pmid } }).find('a').attributes('href')

describe('PubMed chip', () => {
  it('links "PMID: 123" like the button does', () => {
    const w = mount(PubmedLinkChip, { props: { pmid: 'PMID: 31000001' } })
    expect(w.find('a').attributes('href')).toBe('https://pubmed.ncbi.nlm.nih.gov/31000001')
  })
})

describe('PubMed links', () => {
  it('link a numeric PMID, also when typed as "PMID: 123"', () => {
    expect(href('31000001')).toBe('https://pubmed.ncbi.nlm.nih.gov/31000001')
    expect(href(' PMID: 31000001 ')).toBe('https://pubmed.ncbi.nlm.nih.gov/31000001')
    expect(href(31000001)).toBe('https://pubmed.ncbi.nlm.nih.gov/31000001')
  })

  it.each(['abc%_', '12ab', '1234567890', '../x', 'javascript:alert(1)', '', null, undefined])(
    'offer no link for %s',
    pmid => {
      expect(mount(PubmedLinkButton, { props: { pmid } }).find('a').exists()).toBe(false)
      expect(
        mount(PubmedLinkChip, { props: { pmid: pmid as string } })
          .find('a')
          .exists()
      ).toBe(false)
    }
  )
})
