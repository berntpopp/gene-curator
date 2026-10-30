import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ClassificationMark from '../ClassificationMark.vue'
import { registerClassifications } from '@/config/classification'

describe('ClassificationMark', () => {
  it('shows the label and filled bars for strength', () => {
    const w = mount(ClassificationMark, { props: { classification: 'Strong' } })
    expect(w.text()).toBe('Strong')
    expect(w.findAll('i.on')).toHaveLength(3)
    expect(w.classes()).not.toContain('cls-mark--hued')
  })

  it('hues only disputed and refuted', () => {
    expect(
      mount(ClassificationMark, { props: { classification: 'disputed' } }).classes()
    ).toContain('cls-mark--hued')
    expect(mount(ClassificationMark, { props: { classification: 'refuted' } }).classes()).toContain(
      'cls-mark--hued'
    )
  })

  it('renders unknown values as hollow neutral', () => {
    const w = mount(ClassificationMark, { props: { classification: null } })
    expect(w.text()).toBe('Not classified')
    expect(w.findAll('i.on')).toHaveLength(0)
  })
})

describe('ClassificationMark with a declared vocabulary', () => {
  it('hues a declared class by its tone', () => {
    registerClassifications([
      { key: 'refuted_risk', label: 'No association', order: 5, tone: 'refuted' }
    ])
    const w = mount(ClassificationMark, { props: { classification: 'refuted_risk' } })
    expect(w.text()).toBe('No association')
    expect(w.classes()).toContain('cls-mark--hued')
  })
})
