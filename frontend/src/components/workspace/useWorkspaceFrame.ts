/**
 * The curation workspace frame: one object the shell provides and the form fills in, so the
 * shell can show save state, own Ctrl+S and the leave guard, and host the score panel without
 * the form knowing about the layout. Forms use it optionally (`inject(WORKSPACE_FRAME, null)`).
 */
import { computed, ref, shallowRef, watch, type InjectionKey, type Ref } from 'vue'

export type SaveState = 'saved' | 'saving' | 'unsaved' | 'failed'

export interface ScoreSnapshot {
  genetic: number
  experimental: number
  total: number
  classification: string
  hasContradictory: boolean
  geneticBreakdown?: { caseLevel: number; segregation: number; caseControl: number }
  experimentalBreakdown?: {
    function: number
    functionalAlteration: number
    models: number
    rescue: number
  }
}

export interface FormBinding {
  evidence: Ref<unknown>
  saving: Ref<boolean>
  /** Set by the form after every successful save, including saves from its own buttons. */
  savedAt: Ref<number | null>
  /** Resolves true when the draft was saved. */
  save: () => Promise<boolean>
}

export interface SubmitBinding {
  canSubmit: Ref<boolean>
  run: () => void
}

export function createWorkspaceFrame() {
  const form = shallowRef<FormBinding | null>(null)
  const submitBinding = shallowRef<SubmitBinding | null>(null)
  const baseline = ref<string | null>(null)
  const failed = ref(false)
  const savedAt = ref<number | null>(null)
  const score = ref<ScoreSnapshot | null>(null)
  const meta = ref<{ disease?: string; moi?: string }>({})
  // Things that must be fixed before saving, by source (e.g. an unknown PMID in a table)
  const blockerMap = ref<Record<string, string>>({})
  const blockers = computed(() => Object.values(blockerMap.value))

  const snapshot = () => JSON.stringify(form.value?.evidence.value ?? null)
  const dirty = computed(() => baseline.value !== null && snapshot() !== baseline.value)
  const state = computed<SaveState>(() => {
    if (form.value?.saving.value) return 'saving'
    if (failed.value) return 'failed'
    return dirty.value ? 'unsaved' : 'saved'
  })

  /** Call once the form has loaded: what is on screen now counts as saved. */
  function markClean() {
    baseline.value = snapshot()
  }

  function attachForm(binding: FormBinding) {
    form.value = binding
    watch(binding.savedAt, at => {
      if (at === null) return
      failed.value = false
      savedAt.value = at
      markClean()
    })
  }

  async function save(): Promise<boolean> {
    const f = form.value
    if (!f || f.saving.value || blockers.value.length) return false
    const ok = await f.save().catch(() => false)
    failed.value = !ok
    if (ok) {
      savedAt.value ??= Date.now()
      markClean()
    }
    return ok
  }

  function attachSubmit(binding: SubmitBinding) {
    submitBinding.value = binding
  }

  const canSubmit = computed(() => !!submitBinding.value?.canSubmit.value && !blockers.value.length)

  function submit(): boolean {
    if (!canSubmit.value || !submitBinding.value) return false
    submitBinding.value.run()
    return true
  }

  return {
    state,
    dirty,
    savedAt,
    score,
    meta,
    blockers,
    setBlocker: (id: string, reason: string | null) => {
      const rest = Object.fromEntries(Object.entries(blockerMap.value).filter(([k]) => k !== id))
      blockerMap.value = reason ? { ...rest, [id]: reason } : rest
    },
    canSubmit,
    hasSubmit: computed(() => !!submitBinding.value),
    markClean,
    attachForm,
    attachSubmit,
    save,
    submit,
    setScore: (s: ScoreSnapshot | null) => (score.value = s),
    setMeta: (m: { disease?: string; moi?: string }) => (meta.value = m)
  }
}

export type WorkspaceFrame = ReturnType<typeof createWorkspaceFrame>
export const WORKSPACE_FRAME: InjectionKey<WorkspaceFrame> = Symbol('workspace-frame')
