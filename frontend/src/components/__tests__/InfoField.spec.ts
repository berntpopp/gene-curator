/**
 * InfoField Component Tests
 *
 * @see src/components/InfoField.vue
 */

import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import InfoField from '../InfoField.vue'

describe('InfoField', () => {
  it('renders the label and value', () => {
    const wrapper = mount(InfoField, { props: { label: 'Gene Symbol', value: 'BRCA1' } })

    expect(wrapper.text()).toContain('Gene Symbol')
    expect(wrapper.text()).toContain('BRCA1')
  })

  it('shows an em dash when the value is empty', () => {
    const wrapper = mount(InfoField, { props: { label: 'Chromosome' } })

    expect(wrapper.text()).toContain('—')
  })

  it('applies monospace styling only when requested', () => {
    const plain = mount(InfoField, { props: { label: 'HGNC', value: 'HGNC:1100' } })
    const mono = mount(InfoField, { props: { label: 'HGNC', value: 'HGNC:1100', monospace: true } })

    expect(plain.find('.font-monospace').exists()).toBe(false)
    expect(mono.find('.font-monospace').exists()).toBe(true)
  })
})
