import { humanize } from '@/components/dynamic/fieldLabels'

const MOI_LABELS: Record<string, string> = {
  AD: 'Autosomal dominant',
  AR: 'Autosomal recessive',
  XL: 'X-linked',
  XLD: 'X-linked dominant',
  XLR: 'X-linked recessive',
  MT: 'Mitochondrial',
  SD: 'Semidominant'
}

/** `AD` -> `Autosomal dominant`; free text is humanized; empty -> `Unknown`. */
export function formatInheritance(moi: string | null | undefined): string {
  const value = moi || ''
  return MOI_LABELS[value.toUpperCase()] || (value ? humanize(value.toLowerCase()) : 'Unknown')
}

/** The relationship type on an entity line (#539): `Susceptibility`, else '' (Mendelian is the default). */
export const relationshipLabel = (type: string | null | undefined): string =>
  type === 'susceptibility' ? 'Susceptibility' : ''
