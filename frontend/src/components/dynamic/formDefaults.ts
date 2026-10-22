import type { FieldSchema } from './types'

type Data = Record<string, unknown>
const isObject = (value: unknown): value is Data =>
  value !== null && typeof value === 'object' && !Array.isArray(value)

/** Declared scalar defaults only: existing answers and evidence rows are never rewritten. */
export function withDeclaredDefaults(data: Data, fields: Record<string, FieldSchema> = {}): Data {
  let result = data
  for (const [key, field] of Object.entries(fields)) {
    if (field.readOnly || ['array', 'evidence_table'].includes(field.type ?? '')) continue
    const present = Object.hasOwn(data, key)
    let value = data[key]
    if (field.properties && (!present || isObject(value))) {
      const nested = withDeclaredDefaults(isObject(value) ? value : {}, field.properties)
      if (Object.keys(nested).length) value = nested
    } else if (
      !present &&
      (field.default === null || ['boolean', 'number', 'string'].includes(typeof field.default))
    ) {
      value = field.default
    }
    if (value !== data[key]) {
      if (result === data) result = { ...data }
      result[key] = value
    }
  }
  return result
}
