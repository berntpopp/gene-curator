/**
 * Raw methodology config (`field_definitions` + `ui_configuration`, as stored in a methodology
 * version snapshot) -> the document DynamicForm renders. Keeps `evidence_data` paths as field keys.
 */
import type {
  Condition,
  FieldSchema,
  JsonSchemaDocument,
  ScoringConfiguration,
  SectionConfig,
  TabConfig
} from './types'

/** Seed vocabulary on top of FieldSchema (`label`, `help_text`, `options`, `item_schema`, ...) */
interface RawField extends Omit<FieldSchema, 'properties' | 'items' | 'columns'> {
  id?: string
  order?: number
  help_text?: string
  readonly?: boolean
  min?: number
  max?: number
  min_length?: number
  max_length?: number
  options?: Array<{ value: string; label?: string }>
  validation?: string
  external_source?: string
  ui_component?: string
  show_when?: Condition
  properties?: Record<string, RawField>
  items?: { properties?: Record<string, RawField> }
  item_schema?: Record<string, RawField>
  columns?: Record<string, RawField>
}

interface RawSection {
  id?: string
  label?: string
  description?: string
  fields?: RawField[]
}

const TYPES: Record<string, Partial<FieldSchema>> = {
  text: { type: 'string' },
  textarea: { type: 'string', multiline: true },
  enum: { type: 'string' },
  select: { type: 'string' },
  date: { type: 'string', format: 'date' },
  external_reference: { type: 'string' }
}

/** Ontology lookups by `external_source` (names in componentRegistry) */
const SOURCE_COMPONENTS: Record<string, string> = {
  mondo: 'MONDOAutocomplete',
  hpo: 'HPOInput',
  omim: 'OMIMAutocomplete'
}

/** Named `validation` formats used by the seeds */
const PATTERNS: Record<string, string> = {
  pmid_format: '^(PMID:?\\s*)?\\d{1,9}$',
  mondo_id_format: '^MONDO:\\d{6,9}$'
}

// jsonb does not keep key order: an `order` on fields restores it (fields without one keep their place)
const mapFields = (fields: Record<string, RawField>) =>
  Object.fromEntries(
    Object.entries(fields)
      .sort(([, a], [, b]) => (a.order ?? Infinity) - (b.order ?? Infinity))
      .map(([key, raw]) => [key, normalizeField(raw)])
  )

export function normalizeField(raw: RawField): FieldSchema {
  const { properties, items, item_schema, columns, options, ...rest } = raw
  const field: FieldSchema = {
    ...rest,
    ...TYPES[raw.type ?? ''],
    title: raw.title ?? raw.label,
    hint: raw.hint ?? raw.help_text,
    readOnly: raw.readOnly ?? raw.readonly,
    minimum: raw.minimum ?? raw.min,
    maximum: raw.maximum ?? raw.max,
    minLength: raw.minLength ?? raw.min_length,
    maxLength: raw.maxLength ?? raw.max_length,
    pattern: raw.pattern ?? PATTERNS[raw.validation ?? ''],
    // PMID cells get the Europe PMC lookup
    format: raw.format ?? (raw.validation === 'pmid_format' ? 'pmid' : undefined),
    component: raw.component ?? SOURCE_COMPONENTS[raw.external_source ?? ''],
    visible_when: raw.visible_when ?? raw.show_when
  }
  if (options) {
    field.enum = options.map(o => o.value)
    field.enumOptions = options
  }
  if (properties) field.properties = mapFields(properties)
  if (raw.type === 'evidence_table' || raw.ui_component === 'EvidenceTable') {
    field.type = 'evidence_table'
    field.columns = mapFields(columns ?? item_schema ?? items?.properties ?? {})
  } else if (item_schema ?? items?.properties) {
    field.items = { properties: mapFields(item_schema ?? items?.properties ?? {}) }
  }
  return field
}

const isRecord = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === 'object' && !Array.isArray(v)

/**
 * Both seeded shapes: a `{ key: field }` map (curation) and `sections[].fields[]` (precuration).
 * Steps come from `sections` or `ui_configuration.layout.tabs`; one step renders flat.
 */
export function normalizeDefinition(definition: Record<string, unknown>): JsonSchemaDocument {
  const raw = isRecord(definition.field_definitions) ? definition.field_definitions : {}
  const sections = (Array.isArray(raw.sections) ? raw.sections : []) as RawSection[]
  const properties: Record<string, FieldSchema> = {}
  for (const [key, value] of Object.entries(raw)) {
    if (key !== 'sections' && isRecord(value)) properties[key] = normalizeField(value as RawField)
  }
  for (const field of sections.flatMap(s => s.fields ?? [])) {
    if (field.id) properties[field.id] = normalizeField(field)
  }

  const ui = isRecord(definition.ui_configuration) ? definition.ui_configuration : {}
  const layout = (isRecord(ui.layout) ? ui.layout : {}) as { type?: string; tabs?: TabConfig[] }
  const tabs: TabConfig[] | undefined = sections.length
    ? sections.map((s, i) => ({
        id: s.id ?? `step-${i + 1}`,
        name: s.label ?? s.id ?? `Step ${i + 1}`,
        sections: [
          {
            name: s.label ?? '',
            help_text: s.description,
            fields: (s.fields ?? []).flatMap(f => (f.id ? [f.id] : []))
          }
        ]
      }))
    : layout.tabs?.map(tab => ({
        ...tab,
        // Component-only sections (ScoreSummary, LumpingSplittingSection) render via a slot
        sections: (tab.sections ?? []).flatMap((s: Partial<SectionConfig>) =>
          s.fields?.length || s.component ? [{ ...s, fields: s.fields ?? [] } as SectionConfig] : []
        )
      }))

  return {
    properties,
    scoring_configuration: (definition.scoring_configuration ?? undefined) as
      ScoringConfiguration | undefined,
    // One step is no tab layout (DynamicForm's tab view needs two): it renders flat
    ui_configuration: tabs && tabs.length > 1 ? { layout: { type: 'tabs', tabs } } : undefined
  }
}
