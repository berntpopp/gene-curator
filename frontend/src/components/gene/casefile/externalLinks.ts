/** External resources for a gene, built from its symbol and HGNC id. */
export interface ExternalLink {
  label: string
  href: string
}

export function geneExternalLinks(
  symbol: string | null | undefined,
  hgncId: string | null | undefined
): ExternalLink[] {
  const sym = symbol ? encodeURIComponent(symbol) : ''
  const hgnc = hgncId && /^HGNC:\d+$/.test(hgncId) ? hgncId : ''
  return [
    hgnc && {
      label: 'HGNC',
      href: `https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/${hgnc}`
    },
    sym && { label: 'OMIM', href: `https://omim.org/search?search=${sym}` },
    hgnc && { label: 'ClinGen', href: `https://search.clinicalgenome.org/kb/genes/${hgnc}` },
    hgnc && { label: 'GenCC', href: `https://search.thegencc.org/genes/${hgnc}` },
    sym && {
      label: 'PanelApp',
      href: `https://panelapp.genomicsengland.co.uk/panels/entities/${sym}`
    },
    sym && { label: 'gnomAD', href: `https://gnomad.broadinstitute.org/gene/${sym}` },
    sym && { label: 'PubMed', href: `https://pubmed.ncbi.nlm.nih.gov/?term=${sym}%5Btiab%5D` }
  ].filter((l): l is ExternalLink => !!l)
}
