import { humanize } from '@/components/dynamic/fieldLabels'

const MOI_LABELS: Record<string, string> = {
  AD: 'Autosomal dominant',
  AR: 'Autosomal recessive',
  XLD: 'X-linked dominant',
  XLR: 'X-linked recessive',
  MT: 'Mitochondrial'
}

/** `AD` -> `Autosomal dominant`; free text is humanized; empty -> `Unknown`. */
export function formatInheritance(moi: string | null | undefined): string {
  const value = moi || ''
  return MOI_LABELS[value.toUpperCase()] || (value ? humanize(value.toLowerCase()) : 'Unknown')
}
