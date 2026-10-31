import { humanize } from '@/components/dynamic/fieldLabels'

const MOI_LABELS: Record<string, string> = {
  AD: 'Autosomal dominant',
  AR: 'Autosomal recessive',
  XL: 'X-linked',
  XLD: 'X-linked dominant',
  XLR: 'X-linked recessive',
  MT: 'Mitochondrial',
  SD: 'Semidominant',
  // HPO mode-of-inheritance terms, as the precuration stores them (monkey B18)
  'HP:0000006': 'Autosomal dominant',
  'HP:0000007': 'Autosomal recessive',
  'HP:0001417': 'X-linked',
  'HP:0001423': 'X-linked dominant',
  'HP:0001419': 'X-linked recessive',
  'HP:0001427': 'Mitochondrial',
  'HP:0032113': 'Semidominant'
}

/** `AD` -> `Autosomal dominant`; free text is humanized; empty -> `Unknown`. */
export function formatInheritance(moi: string | null | undefined): string {
  const value = moi || ''
  if (MOI_LABELS[value.toUpperCase()]) return MOI_LABELS[value.toUpperCase()]!
  // An ontology id ("HP:0000006") is shown as written, never re-cased
  return /^[A-Z]+:\d+$/.test(value) ? value : value ? humanize(value.toLowerCase()) : 'Unknown'
}

/** The relationship type on an entity line (#539): `Susceptibility`, else '' (Mendelian is the default). */
export const relationshipLabel = (type: string | null | undefined): string =>
  type === 'susceptibility' ? 'Susceptibility' : ''
