/**
 * The workflow-stage builder's view of `workflow_states` (#282). Two stored shapes, as
 * `core/schema_rules.py: _check_workflow` reads them: a list `{ states: [{ name, ... }],
 * transitions: { name: [next] }, initial_state }` and the seeded stage map
 * `{ stage: { allowed_transitions: [next], ... } }`. Edits change a copy in place, so keys the
 * builder does not show survive and the code view round-trips.
 */
type Rec = Record<string, unknown>

const isRecord = (v: unknown): v is Rec => !!v && typeof v === 'object' && !Array.isArray(v)

export type WorkflowShape = 'list' | 'map' | null

export function shapeOf(wf: unknown): WorkflowShape {
  if (!isRecord(wf)) return null
  if (Array.isArray(wf.states)) return 'list'
  if ('states' in wf || 'transitions' in wf) return null
  return Object.values(wf).every(isRecord) ? 'map' : null
}

const states = (wf: Rec) => (wf.states as unknown[]).filter(isRecord)

export function stageNames(wf: unknown): string[] {
  const shape = shapeOf(wf)
  if (shape === 'list') return states(wf as Rec).map(s => String(s.name ?? ''))
  return shape === 'map' ? Object.keys(wf as Rec) : []
}

/** The object holding a stage's own keys (description, reviewers_required, ...). */
export function stageNode(wf: unknown, name: string): Rec | undefined {
  const shape = shapeOf(wf)
  if (shape === 'list') return states(wf as Rec).find(s => s.name === name)
  return shape === 'map' ? ((wf as Rec)[name] as Rec) : undefined
}

export function nextOf(wf: unknown, name: string): string[] {
  const list =
    shapeOf(wf) === 'list'
      ? (((wf as Rec).transitions as Rec | undefined) ?? {})[name]
      : stageNode(wf, name)?.allowed_transitions
  return Array.isArray(list) ? list.map(String) : []
}

/** Mutates `wf`. */
export function setNext(wf: Rec, name: string, next: string[]): void {
  if (shapeOf(wf) === 'list') wf.transitions = { ...((wf.transitions as Rec) ?? {}), [name]: next }
  else {
    const node = stageNode(wf, name)
    if (node) node.allowed_transitions = next
  }
}

/** Mutates `wf`; a name already used is ignored. */
export function addStage(wf: Rec, name: string): void {
  if (!name || stageNames(wf).includes(name)) return
  if (shapeOf(wf) === 'list') {
    ;(wf.states as unknown[]).push({ name })
    setNext(wf, name, [])
  } else wf[name] = { allowed_transitions: [] }
}

/** Mutates `wf`: the stage, its transitions and every transition into it. */
export function removeStage(wf: Rec, name: string): void {
  const list = shapeOf(wf) === 'list'
  for (const other of stageNames(wf)) {
    if (other !== name && nextOf(wf, other).includes(name)) {
      setNext(
        wf,
        other,
        nextOf(wf, other).filter(n => n !== name)
      )
    }
  }
  if (list) {
    wf.states = (wf.states as unknown[]).filter(s => !isRecord(s) || s.name !== name)
    const transitions = { ...((wf.transitions as Rec) ?? {}) }
    delete transitions[name]
    wf.transitions = transitions
    if (wf.initial_state === name) delete wf.initial_state
  } else delete wf[name]
}

/** JSON paths of a stage's own diagnostics (`_check_workflow` / `_check_stage_map`). */
export const stagePaths = (name: string) => [
  `workflow_states.${name}`,
  `workflow_states.transitions.${name}`
]
