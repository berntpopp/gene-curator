import type { Condition, FieldSchema } from './types'

/** Value at a dot-notation path of the form data */
export function valueAt(data: unknown, path: string): unknown {
  return path
    .split('.')
    .reduce<unknown>(
      (value, key) => (value as Record<string, unknown> | null | undefined)?.[key],
      data
    )
}

/** Every entry holds: an array means "one of", anything else means "equals" */
export function conditionHolds(condition: Condition, data: unknown): boolean {
  return Object.entries(condition).every(([path, expected]) => {
    const actual = valueAt(data, path)
    return Array.isArray(expected) ? expected.includes(actual) : actual === expected
  })
}

/** The field as the current data shows it: null when hidden, otherwise with `required` resolved */
export function resolveField(field: FieldSchema, data: unknown): FieldSchema | null {
  if (field.visible_when && !conditionHolds(field.visible_when, data)) return null
  if (!field.required_when) return field
  return { ...field, required: !!field.required || conditionHolds(field.required_when, data) }
}
