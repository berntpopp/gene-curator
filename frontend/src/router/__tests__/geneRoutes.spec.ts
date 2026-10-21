import { describe, it, expect } from 'vitest'
import router from '../index'

describe('gene routes', () => {
  it('redirects the old cross-scope summary URL to the gene page', () => {
    const route = router.getRoutes().find(r => r.path === '/genes/:geneId/summary')
    const redirect = route?.redirect as (to: { params: Record<string, string> }) => unknown
    expect(redirect({ params: { geneId: 'g1' } })).toEqual({
      name: 'GeneDetail',
      params: { id: 'g1' }
    })
  })
})
