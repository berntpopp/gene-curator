/**
 * Condition semantics of the form engine (#433); the backend copy is
 * `backend/app/crud/precuration_required.py`, both run the table in `__tests__/conditionCases.json`.
 *
 * - `{ path: value, ... }` holds when every entry holds: an array means "one of", anything else
 *   equals. Equality is strict: `true` is not `1`, `'1'` is not `1`.
 * - Paths are dotted from the root of the form data, for nested fields too; a numeric segment
 *   (`rows.0.kind`) indexes an array. A missing value is not `null`.
 * - No condition (absent or null) holds. A malformed one (not an object, or a value that is an
 *   object or a nested array) also holds: the field stays shown and, for `required_when`,
 *   required, so a schema typo never drops a required check.
 * - `visible_when` wins over its alias `show_when`; a field under a hidden parent is hidden, and a
 *   hidden field is never required.
 */
import type { InjectionKey, Ref } from 'vue'
import type { FieldSchema } from './types'

/** Root form data, provided by DynamicForm for nested fields (condition paths start at the root) */
export const FORM_DATA: InjectionKey<Ref<Record<string, unknown>>> = Symbol('formData')

const INDEX = /^(0|[1-9]\d*)$/

const isRecord = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === 'object' && !Array.isArray(v)

const isScalar = (v: unknown) => v === null || ['string', 'number', 'boolean'].includes(typeof v)

/** Value at a dot-notation path of the form data; undefined when missing (null is a value) */
export function valueAt(data: unknown, path: string): unknown {
  let value = data
  for (const key of path.split('.')) {
    // `in` lets Vue track keys added later (it does not track hasOwn); hasOwn drops inherited ones
    if (isRecord(value) && key in value && Object.hasOwn(value, key)) value = value[key]
    else if (Array.isArray(value) && INDEX.test(key) && Number(key) < value.length) {
      value = value[Number(key)]
    } else return undefined
  }
  return value
}

/** Whether the condition holds for the data (semantics above) */
export function conditionHolds(condition: unknown, data: unknown): boolean {
  const wellFormed =
    isRecord(condition) &&
    Object.values(condition).every(v => isScalar(v) || (Array.isArray(v) && v.every(isScalar)))
  if (!wellFormed) return true // no condition, or malformed: shown and required, never skipped
  return Object.entries(condition).every(([path, expected]) => {
    const actual = valueAt(data, path)
    return Array.isArray(expected) ? expected.includes(actual) : actual === expected
  })
}

interface Conditional {
  visible_when?: unknown
  show_when?: unknown
  required_when?: unknown
}

/** The field's own `visible_when` (or `show_when`) holds */
export const isVisible = (field: Conditional, data: unknown) =>
  conditionHolds(field.visible_when ?? field.show_when, data)

/** The field has a `required_when` and it holds */
export const requiredWhenHolds = (field: Conditional, data: unknown) =>
  field.required_when != null && conditionHolds(field.required_when, data)

/** The field as the current data shows it: null when hidden, otherwise with `required` resolved */
export function resolveField(field: FieldSchema, data: unknown): FieldSchema | null {
  if (!isVisible(field, data)) return null
  if (field.required_when == null) return field
  return { ...field, required: !!field.required || requiredWhenHolds(field, data) }
}
