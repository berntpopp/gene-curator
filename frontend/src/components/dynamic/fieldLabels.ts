import type { FieldSchema, JsonSchemaDocument } from './types'

/** `mode_of_inheritance` -> `Mode of inheritance` */
export function humanize(key: string): string {
  const words = key.replace(/_/g, ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/** Display title for a dotted field path: the schema title, else the humanized last segment. */
export function labelForPath(schema: JsonSchemaDocument, path: string): string {
  let node: FieldSchema | undefined
  let props = schema.properties as Record<string, FieldSchema> | undefined
  for (const segment of path.split('.')) {
    node = props?.[segment]
    props = node?.properties
  }
  return node?.title || node?.label || humanize(path.split('.').pop() ?? path)
}
