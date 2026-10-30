/**
 * Field references outside a field's own definition, kept in step when the editor adds, removes
 * or renames a field: `ui_configuration.layout.tabs[].sections[].fields` (dotted paths; the
 * form shows only what the layout lists), conditions of other fields, and the scoring and
 * validation blocks (only reported: their path syntax is engine-specific).
 */

export interface LayoutRef {
  tab: number
  section: number
}

type Rec = Record<string, unknown>

const isRecord = (v: unknown): v is Rec => !!v && typeof v === 'object' && !Array.isArray(v)

/** First segment of a dotted path: the top-level field id */
export const topId = (path: string) => path.split('.')[0] ?? path

const isUnder = (path: string, id: string) => path === id || path.startsWith(`${id}.`)
const renamed = (path: string, from: string, to: string) =>
  isUnder(path, from) ? to + path.slice(from.length) : path

const tabsOf = (ui: unknown): Rec[] => {
  const layout = isRecord(ui) && isRecord(ui.layout) ? ui.layout : {}
  return Array.isArray(layout.tabs) ? layout.tabs.filter(isRecord) : []
}

const sectionAt = (ui: unknown, ref: LayoutRef): Rec | undefined => {
  const sections = tabsOf(ui)[ref.tab]?.sections
  const section: unknown = Array.isArray(sections) ? sections[ref.section] : undefined
  return isRecord(section) ? section : undefined
}

/** Tab sections that list fields (component-only sections such as ScoreSummary are skipped) */
export function layoutSections(ui: unknown) {
  return tabsOf(ui).flatMap((tab, t) =>
    (Array.isArray(tab.sections) ? tab.sections : []).flatMap((section: unknown, s) =>
      isRecord(section) && Array.isArray(section.fields)
        ? [
            {
              ref: { tab: t, section: s },
              label: `${String(tab.name ?? tab.id ?? `Tab ${t + 1}`)} › ${String(section.name ?? '')}`,
              paths: section.fields.map(String)
            }
          ]
        : []
    )
  )
}

/** Mutates `ui`: every layout field list */
const eachList = (ui: unknown, change: (fields: string[]) => string[]) => {
  for (const { ref } of layoutSections(ui)) {
    const section = sectionAt(ui, ref)!
    section.fields = change((section.fields as unknown[]).map(String))
  }
}

/** Show a new field in `ref`'s section, else in the last section that lists fields */
export function placeField(ui: unknown, id: string, ref?: LayoutRef): void {
  const target = ref ?? layoutSections(ui).at(-1)?.ref
  const section = target && sectionAt(ui, target)
  if (section) section.fields = [...(section.fields as string[]), id]
}

export const dropField = (ui: unknown, id: string) =>
  eachList(ui, fields => fields.filter(p => !isUnder(p, id)))

export const renameInLayout = (ui: unknown, from: string, to: string) =>
  eachList(ui, fields => fields.map(p => renamed(p, from, to)))

/** Put `ref`'s top-level entries in the order of `ids` (nested paths move with their field) */
export function orderLayout(ui: unknown, ref: LayoutRef, ids: string[]): void {
  const section = sectionAt(ui, ref)
  if (!Array.isArray(section?.fields)) return
  const rank = (p: string) => ids.indexOf(topId(p))
  section!.fields = [...(section!.fields as string[])].sort((a, b) => rank(a) - rank(b))
}

const CONDITIONS = ['show_when', 'visible_when', 'required_when']

/** Mutates `defs`: condition paths of every field (sections, columns, nested properties) */
export function renameConditions(defs: unknown, from: string, to: string): void {
  if (Array.isArray(defs)) return defs.forEach(d => renameConditions(d, from, to))
  if (!isRecord(defs)) return
  for (const key of CONDITIONS) {
    const cond = defs[key]
    if (isRecord(cond)) {
      defs[key] = Object.fromEntries(
        Object.entries(cond).map(([p, v]) => [renamed(p, from, to), v])
      )
    }
  }
  Object.values(defs).forEach(v => renameConditions(v, from, to))
}

/** Names of the blocks whose JSON mentions `id` as a whole path segment */
export function referencedIn(blocks: Record<string, unknown>, id: string): string[] {
  const escaped = id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pattern = new RegExp(`(^|[^A-Za-z0-9_])${escaped}([^A-Za-z0-9_]|$)`)
  return Object.entries(blocks)
    .filter(([, value]) => value != null && pattern.test(JSON.stringify(value)))
    .map(([name]) => name)
}
