import { describe, it, expect, vi } from 'vitest'
import { nextTick, ref } from 'vue'
import { createWorkspaceFrame } from '../useWorkspaceFrame'

function setup(save = vi.fn().mockResolvedValue(true)) {
  const frame = createWorkspaceFrame()
  const evidence = ref<Record<string, unknown>>({ a: 1 })
  const saving = ref(false)
  const savedAt = ref<number | null>(null)
  frame.attachForm({ evidence, saving, savedAt, save })
  frame.markClean()
  return { frame, evidence, saving, savedAt, save }
}

describe('workspace frame conflict', () => {
  it('shows conflict, keeps the leave guard on, and stops saving over the newer version', async () => {
    const save = vi.fn().mockResolvedValue(true)
    const frame = createWorkspaceFrame()
    const evidence = ref<Record<string, unknown>>({ a: 1 })
    const conflict = ref(false)
    frame.attachForm({
      evidence,
      saving: ref(false),
      savedAt: ref<number | null>(null),
      conflict,
      save
    })
    frame.markClean()
    evidence.value = { a: 2 }
    conflict.value = true
    await nextTick()

    expect(frame.state.value).toBe('conflict')
    expect(frame.dirty.value).toBe(true) // the unsaved-changes guard stays active
    expect(await frame.save()).toBe(false)
    expect(save).not.toHaveBeenCalled()
  })
})

describe('workspace frame save state', () => {
  it('is saved until the evidence changes, then unsaved', async () => {
    const { frame, evidence } = setup()
    expect(frame.state.value).toBe('saved')
    expect(frame.dirty.value).toBe(false)
    evidence.value = { a: 2 }
    await nextTick()
    expect(frame.state.value).toBe('unsaved')
    evidence.value = { a: 1 }
    await nextTick()
    expect(frame.state.value).toBe('saved')
  })

  it('shows saving while the form saves', async () => {
    const { frame, saving, evidence } = setup()
    evidence.value = { a: 2 }
    saving.value = true
    expect(frame.state.value).toBe('saving')
  })

  it('goes saved with a time after a successful save()', async () => {
    const { frame, evidence, save } = setup()
    evidence.value = { a: 2 }
    expect(await frame.save()).toBe(true)
    expect(save).toHaveBeenCalledTimes(1)
    expect(frame.state.value).toBe('saved')
    expect(frame.savedAt.value).toBeTypeOf('number')
  })

  it('goes failed when save() fails, stays failed on edits, and recovers on retry', async () => {
    const save = vi.fn().mockResolvedValueOnce(false).mockResolvedValueOnce(true)
    const { frame, evidence } = setup(save)
    evidence.value = { a: 2 }
    await frame.save()
    expect(frame.state.value).toBe('failed')
    evidence.value = { a: 3 }
    await nextTick()
    expect(frame.state.value).toBe('failed')
    await frame.save()
    expect(frame.state.value).toBe('saved')
  })

  it('treats a throwing save as failed', async () => {
    const { frame, evidence } = setup(vi.fn().mockRejectedValue(new Error('x')))
    evidence.value = { a: 2 }
    expect(await frame.save()).toBe(false)
    expect(frame.state.value).toBe('failed')
  })

  it('goes clean when the form reports a save of its own (savedAt)', async () => {
    const { frame, evidence, savedAt } = setup()
    evidence.value = { a: 2 }
    await nextTick()
    savedAt.value = 123
    await nextTick()
    expect(frame.state.value).toBe('saved')
    expect(frame.savedAt.value).toBe(123)
  })

  it('does not start a second save while one runs, and ignores save() with no form', async () => {
    const { frame, saving, save } = setup()
    saving.value = true
    expect(await frame.save()).toBe(false)
    expect(save).not.toHaveBeenCalled()
    expect(await createWorkspaceFrame().save()).toBe(false)
  })

  it('holds score, meta and a submit handler from the form', () => {
    const frame = createWorkspaceFrame()
    expect(frame.submit()).toBe(false)
    const run = vi.fn()
    frame.attachSubmit({ canSubmit: ref(true), run })
    expect(frame.submit()).toBe(true)
    expect(run).toHaveBeenCalled()
    frame.attachSubmit({ canSubmit: ref(false), run })
    expect(frame.submit()).toBe(false)
    frame.setMeta({ disease: 'Alport syndrome', moi: 'X-linked' })
    expect(frame.meta.value.disease).toBe('Alport syndrome')
  })

  it('keeps edits made while a save is in flight unsaved', async () => {
    const evidence = ref<Record<string, unknown>>({ a: 1 })
    const saving = ref(false)
    const savedAt = ref<number | null>(null)
    let finish!: () => void
    const save = vi.fn(async () => {
      saving.value = true
      await new Promise<void>(r => (finish = r))
      saving.value = false
      return true
    })
    const frame = createWorkspaceFrame()
    frame.attachForm({ evidence, saving, savedAt, save })
    frame.markClean()
    evidence.value = { a: 2 }
    const pending = frame.save()
    evidence.value = { a: 3 } // typed while the request runs
    finish()
    await pending
    expect(frame.state.value).toBe('unsaved')
    expect(frame.dirty.value).toBe(true)
  })

  it('also keeps in-flight edits unsaved when the form reports its own save', async () => {
    const { frame, evidence, saving, savedAt } = setup()
    evidence.value = { a: 2 }
    saving.value = true
    await nextTick()
    evidence.value = { a: 3 }
    saving.value = false
    savedAt.value = 5
    await nextTick()
    expect(frame.state.value).toBe('unsaved')
  })

  it('blocks only submit on a blocker, never saving', async () => {
    const { frame, save } = setup()
    frame.attachSubmit({ canSubmit: ref(true), run: vi.fn() })
    frame.setBlocker('t1', 'PMID 99 not found in Europe PMC')
    expect(frame.blockers.value).toEqual(['PMID 99 not found in Europe PMC'])
    expect(frame.canSubmit.value).toBe(false)
    expect(frame.submit()).toBe(false)
    expect(await frame.save()).toBe(true)
    expect(save).toHaveBeenCalledTimes(1)
    frame.setBlocker('t1', null)
    expect(frame.blockers.value).toEqual([])
    expect(frame.canSubmit.value).toBe(true)
  })

  it('blocks submit with the score panel reason while submit would refuse a row', () => {
    const { frame } = setup()
    frame.attachSubmit({ canSubmit: ref(true), run: vi.fn() })
    const score = (refused: boolean) =>
      ({
        classification: 'Limited',
        hasContradictory: false,
        excluded: [{ text: 'P1', refused }]
      }) as never
    frame.setScore(score(false)) // not_scored is the curator's choice: submit allowed
    expect(frame.canSubmit.value).toBe(true)
    frame.setScore(score(true))
    expect(frame.blockers.value).toEqual(['Fix the rows that score 0 before submitting'])
    expect(frame.canSubmit.value).toBe(false)
    expect(frame.submit()).toBe(false)
  })

  it('keeps in-flight edits unsaved when the form sets savedAt during a frame-started save', async () => {
    const evidence = ref<Record<string, unknown>>({ a: 1 })
    const saving = ref(false)
    const savedAt = ref<number | null>(null)
    let finish!: () => void
    const save = vi.fn(async () => {
      saving.value = true
      await new Promise<void>(r => (finish = r))
      savedAt.value = 99 // what SchemaDrivenCurationForm.onSaved does
      saving.value = false
      return true
    })
    const frame = createWorkspaceFrame()
    frame.attachForm({ evidence, saving, savedAt, save })
    frame.markClean()
    evidence.value = { a: 2 }
    const pending = frame.save()
    evidence.value = { a: 3 }
    finish()
    await pending
    expect(frame.state.value).toBe('unsaved')
  })
})
