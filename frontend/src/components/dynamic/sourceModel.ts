/**
 * `source` cells (#593): where an evidence row comes from (VA-Spec Document plus the
 * provenance GeneFoundry returns). Same identifier formats as `backend/app/core/source_field.py`.
 */
import { safeHref } from './componentRegistry'

export interface Source {
  kind?: string
  id?: string
  url?: string
  title?: string
  retrieved_at?: string
  tool?: string
  record_sha256?: string
  citation?: string
}

export const SOURCE_KINDS: Array<{ value: string; title: string; pattern: RegExp }> = [
  { value: 'pmid', title: 'PMID', pattern: /^\d{1,10}$/ },
  { value: 'doi', title: 'DOI', pattern: /^10\.\d{4,9}\/\S+$/ },
  { value: 'clinvar', title: 'ClinVar', pattern: /^(VCV|RCV|SCV)\d{9}(\.\d+)?$/ },
  { value: 'clingen_allele', title: 'ClinGen allele', pattern: /^CA\d+$/ },
  { value: 'clingen_validity', title: 'ClinGen validity', pattern: /^CGGV:assertion_\S+$/ },
  { value: 'url', title: 'URL', pattern: /^https?:\/\/\S+$/ },
  { value: 'database', title: 'Database', pattern: /^\S.*$/ }
]

const LINKS: Record<string, (id: string) => string> = {
  pmid: id => `https://pubmed.ncbi.nlm.nih.gov/${id}/`,
  doi: id => `https://doi.org/${id}`,
  clinvar: id => `https://www.ncbi.nlm.nih.gov/clinvar/?term=${encodeURIComponent(id)}`,
  clingen_allele: id =>
    `https://reg.clinicalgenome.org/redmine/projects/registry/genboree_registry/by_caid?caid=${encodeURIComponent(id)}`,
  url: id => id
}

/** A cell holds one source or a list; blank values hold none */
export function sourceList(value: unknown): Source[] {
  const items = Array.isArray(value) ? value : value ? [value] : []
  return items.filter((s): s is Source => !!s && typeof s === 'object' && 'kind' in s)
}

/**
 * The kind an identifier is written in: `PMID:` and `doi:` prefixes are dropped, a bare number is
 * a PMID; text that fits no pattern is a database reference (the cell shows the kind it read).
 */
export function detectSource(raw: string): Required<Pick<Source, 'kind' | 'id'>> {
  const text = raw.trim()
  const prefixed = /^(pmid|doi):\s*(\S.*)$/i.exec(text)
  if (prefixed) return { kind: prefixed[1]!.toLowerCase(), id: prefixed[2]! }
  return { kind: SOURCE_KINDS.find(k => k.pattern.test(text))?.value ?? 'database', id: text }
}

/** Why an identifier is refused, or '' when it is fine */
export function sourceError(kind: string, id: string): string {
  const def = SOURCE_KINDS.find(k => k.value === kind)
  if (!def) return 'Pick a kind'
  if (!id.trim()) return 'Enter an id'
  return def.pattern.test(id.trim()) ? '' : `Not a valid ${def.title} id`
}

export function sourceHref(source: Source): string | undefined {
  const link = LINKS[source.kind ?? '']
  return safeHref(source.url) ?? (source.id && link ? safeHref(link(source.id)) : undefined)
}

export function sourceLabel(source: Source): string {
  const kind = SOURCE_KINDS.find(k => k.value === source.kind)?.title ?? source.kind
  return `${kind} ${source.id ?? ''}`.trim()
}

/** Tooltip: title, citation, tool and retrieval date as recorded */
export function sourceDetail(source: Source): string {
  return [
    source.title,
    source.citation,
    source.tool && `via ${source.tool}`,
    source.retrieved_at && `retrieved ${source.retrieved_at}`
  ]
    .filter(Boolean)
    .join(' · ')
}
