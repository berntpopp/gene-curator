import { describe, it, expect } from 'vitest'
import { formatInheritance } from '../inheritance'

describe('formatInheritance', () => {
  it.each([
    ['AD', 'Autosomal dominant'],
    ['xlr', 'X-linked recessive'],
    ['MT', 'Mitochondrial'],
    ['Autosomal dominant', 'Autosomal dominant'],
    ['', 'Unknown'],
    [undefined, 'Unknown']
  ])('%s -> %s', (moi, label) => {
    expect(formatInheritance(moi)).toBe(label)
  })
})
