import { describe, expect, it } from 'vitest'

// Phones show the route title in PhoneHeader; each view keeps its h1 for screen readers only.
const VIEWS = [
  'MyWork',
  'GeneAssignments',
  'FAQ',
  'NotFound',
  'GenesTable',
  'GeneCatalogueView',
  'UserManagement',
  'SchemaManagement',
  'WorkflowManagement',
  'scope/ScopeList',
  'curation/ReviewQueueView'
]
const sources = import.meta.glob<string>('/src/views/**/*.vue', {
  query: '?raw',
  import: 'default',
  eager: true
})
const app = import.meta.glob<string>('/src/App.vue', {
  query: '?raw',
  import: 'default',
  eager: true
})

describe('page title on phones', () => {
  it.each(VIEWS)('%s marks its h1 with page-title', name => {
    const text = sources[`/src/views/${name}.vue`]!
    expect(text).toMatch(/<h1 class="page-title /)
  })

  it('hides .page-title visually below md', () => {
    const css = Object.values(app)[0]!
    expect(css).toMatch(/@media \(max-width: 959\.98px\)\s*\{\s*\.has-phone-header \.page-title/)
  })

  it('is fully visually hidden, not just clipped', () => {
    const css = Object.values(app)[0]!
    for (const rule of ['clip-path: inset(50%)', 'margin: -1px', 'padding: 0', 'border: 0']) {
      expect(css).toContain(rule)
    }
  })
})
