import { describe, it, expect } from 'vitest'
import { geneExternalLinks } from '../externalLinks'

describe('geneExternalLinks', () => {
  it('builds one link per resource from symbol and HGNC id', () => {
    const links = geneExternalLinks('PKD1', 'HGNC:9008')
    expect(links.map(l => l.label)).toEqual([
      'HGNC',
      'OMIM',
      'ClinGen',
      'GenCC',
      'PanelApp',
      'gnomAD',
      'PubMed'
    ])
    const byLabel = Object.fromEntries(links.map(l => [l.label, l.href]))
    expect(byLabel.HGNC).toContain('hgnc_id/HGNC:9008')
    expect(byLabel.ClinGen).toContain('HGNC:9008')
    expect(byLabel.GenCC).toContain('HGNC:9008')
    expect(byLabel.OMIM).toContain('search=PKD1')
    expect(byLabel.gnomAD).toContain('/gene/PKD1')
    expect(byLabel.PubMed).toContain('PKD1')
  })

  it('encodes the symbol and skips links that need a missing identifier', () => {
    expect(geneExternalLinks('A B/C', null).map(l => l.label)).toEqual([
      'OMIM',
      'PanelApp',
      'gnomAD',
      'PubMed'
    ])
    expect(geneExternalLinks('A B/C', null)[0]?.href).toContain('A%20B%2FC')
    expect(geneExternalLinks('', 'HGNC:1').map(l => l.label)).toEqual(['HGNC', 'ClinGen', 'GenCC'])
  })
})
