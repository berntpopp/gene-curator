/** Schema labels and scalar values shared by readonly evidence and review diffs. */
export type ValueOption = string | number | { value?: unknown; label?: string }

export function formatValue(v: unknown, options?: ValueOption[]): string {
  if (v === null || v === undefined || v === '') return '—'
  const option = options?.find(o => (typeof o === 'object' ? o.value : o) === v)
  if (typeof option === 'object' && option.label) return option.label
  if (typeof v === 'boolean') return v ? 'Yes' : 'No'
  return typeof v === 'object' ? JSON.stringify(v) : String(v)
}
