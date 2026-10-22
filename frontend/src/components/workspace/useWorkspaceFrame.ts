/**
 * The curation workspace frame: one object the shell provides and the form fills in, so the
 * shell can show save state, own Ctrl+S and the leave guard, and host the score panel without
 * the form knowing about the layout. Forms use it optionally (`inject(WORKSPACE_FRAME, null)`).
 */
import { computed, ref, shallowRef, watch, type InjectionKey, type Ref } from 'vue'

import type { EvidenceScores } from '@/views/curation/curationScores'

export type SaveState = 'saved' | 'saving' | 'unsaved' | 'failed' | 'conflict'

export interface ScoreSnapshot extends EvidenceScores {
  classification: string
  hasContradictory: boolean
}

export interface FormBinding {
  evidence: Ref<unknown>
  saving: Ref<boolean>
  /** Set by the form after every successful save, including saves from its own buttons. */
  savedAt: Ref<number | null>
  /** Another tab saved a newer version: saving is blocked until the page is reloaded. */
  conflict?: Ref<boolean>
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
  // What was on screen when the current save started: edits typed during the request stay unsaved
  let inflight: string | null = null
  const savedAt = ref<number | null>(null)
  const score = ref<ScoreSnapshot | null>(null)
  const scorePending = ref(false)
  const meta = ref<{ disease?: string; moi?: string }>({})
  // Things that must be fixed before saving, by source (e.g. an unknown PMID in a table)
  const blockerMap = ref<Record<string, string>>({})
  const blockers = computed(() => Object.values(blockerMap.value))

  const snapshot = () => JSON.stringify(form.value?.evidence.value ?? null)
  const dirty = computed(() => baseline.value !== null && snapshot() !== baseline.value)
  const state = computed<SaveState>(() => {
    if (form.value?.saving.value) return 'saving'
    if (form.value?.conflict?.value) return 'conflict'
    if (failed.value) return 'failed'
    return dirty.value ? 'unsaved' : 'saved'
  })

  /** Call once the form has loaded: what is on screen now counts as saved. */
  function markClean() {
    baseline.value = snapshot()
  }

  function markSaved() {
    baseline.value = inflight ?? snapshot()
  }

  function attachForm(binding: FormBinding) {
    form.value = binding
    watch(
      binding.saving,
      on => {
        if (on) inflight = snapshot()
      },
      { flush: 'sync' }
    )
    watch(binding.savedAt, at => {
      if (at === null) return
      failed.value = false
      savedAt.value = at
      markSaved()
    })
  }

  async function save(): Promise<boolean> {
    const f = form.value
    // Never save over the newer version another tab stored; the dirty flag keeps the leave guard on
    if (!f || f.saving.value || f.conflict?.value) return false
    const ok = await f.save().catch(() => false)
    failed.value = !ok
    if (ok) {
      savedAt.value ??= Date.now()
      markSaved()
    }
    inflight = null
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
    scorePending,
    setScorePending: (pending: boolean) => (scorePending.value = pending),
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
