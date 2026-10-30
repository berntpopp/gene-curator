import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useValidationStore } from '@/stores/validation'
import { mount } from '@vue/test-utils'
import StageLine from '../StageLine.vue'
import SaveState from '../SaveState.vue'
import ScorePanel from '../ScorePanel.vue'
import type { ScoreSnapshot } from '../useWorkspaceFrame'

describe('StageLine', () => {
  it('marks earlier stages done, the current one current and later ones upcoming', () => {
    const w = mount(StageLine, { props: { stage: 'curation' } })
    const items = w.findAll('li')
    expect(items.map(i => i.text())).toEqual(['Precuration', 'Curation', 'Review', 'Active'])
    expect(items.map(i => i.classes().find(c => c.startsWith('stage--')))).toEqual([
      'stage--done',
      'stage--current',
      'stage--todo',
      'stage--todo'
    ])
    expect(w.find('[aria-current="step"]').text()).toBe('Curation')
  })

  it('adds a terminal Archived step after Active', () => {
    const w = mount(StageLine, { props: { stage: 'active', archived: true } })
    const items = w.findAll('li')
    expect(items.at(-1)!.text()).toBe('Archived')
    expect(w.find('[aria-current="step"]').text()).toBe('Archived')
    expect(items[3]!.classes()).toContain('stage--done')
  })

  it('has no current step for an unknown stage', () => {
    expect(
      mount(StageLine, { props: { stage: 'entry' } })
        .find('[aria-current]')
        .exists()
    ).toBe(false)
  })
})

describe('SaveState', () => {
  const text = (state: string, savedAt: number | null = null) =>
    mount(SaveState, { props: { state: state as never, savedAt } }).text()

  it('names every state', () => {
    expect(text('saved', new Date(2026, 9, 21, 14, 2).getTime())).toMatch(/^Saved 14[:.]02/)
    expect(text('saved')).toBe('Saved')
    expect(text('saving')).toBe('Saving…')
    expect(text('unsaved')).toBe('Unsaved changes')
    expect(text('failed')).toContain('Save failed')
    expect(text('conflict')).toContain('Edited elsewhere')
    // Local edits survive the reload and are offered back (#436): never claim they are lost
    expect(text('conflict')).toContain('your changes here are kept in this browser')
    expect(text('conflict')).not.toContain('lost')
  })

  it('conflict: says local changes survive the reload, and reloads on click', async () => {
    const reload = vi.fn()
    vi.stubGlobal('location', { ...window.location, reload })
    const w = mount(SaveState, { props: { state: 'conflict', savedAt: null } })
    expect(w.attributes('role')).toBe('alert')
    expect(w.text()).toContain('offered after the reload')
    expect(w.find('button').text()).toBe('Reload')
    await w.find('button').trigger('click')
    expect(reload).toHaveBeenCalledOnce()
    expect(w.emitted('retry')).toBeUndefined() // retrying would only conflict again
    vi.unstubAllGlobals()
  })

  it('is a polite live region and offers retry only after a failure', async () => {
    const ok = mount(SaveState, { props: { state: 'unsaved', savedAt: null } })
    expect(ok.attributes('role')).toBe('status')
    expect(ok.find('button').exists()).toBe(false)
    const bad = mount(SaveState, { props: { state: 'failed', savedAt: null } })
    await bad.find('button').trigger('click')
    expect(bad.emitted('retry')).toHaveLength(1)
  })
})

const score = (over: Partial<ScoreSnapshot> = {}): ScoreSnapshot => ({
  total: 7.5,
  trace: null,
  classification: 'Moderate',
  hasContradictory: false,
  ...over
})

describe('ScorePanel', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('lists the rows the score flags, next to the score', () => {
    useValidationStore().validationResults.form = {
      warnings: [
        { field: 'scoring', type: 'scoring', message: '2 evidence item(s) with invalid PMID' },
        { field: 'disease', type: 'quality', message: 'Disease is short' }
      ]
    } as never
    const w = mount(ScorePanel, { props: { score: score(), canSubmit: true, readonly: false } })
    const rows = w.find('[data-testid="score-flags"]')
    expect(rows.text()).toContain('2 evidence item(s) with invalid PMID')
    expect(rows.text()).not.toContain('Disease is short')
  })

  it('shows no flagged-rows list when the score flags nothing', () => {
    const w = mount(ScorePanel, { props: { score: score(), canSubmit: true, readonly: false } })
    expect(w.find('[data-testid="score-flags"]').exists()).toBe(false)
  })

  it('shows backend totals and verdict without guessed thresholds', () => {
    const w = mount(ScorePanel, { props: { score: score(), canSubmit: true, readonly: false } })
    expect(w.text()).toContain('7.50')
    expect(w.text()).toContain('Moderate')
    expect(w.text()).toContain('Score breakdown unavailable')
    expect(w.text()).not.toContain('/ 18')
    expect(w.text()).not.toContain('points to')
  })

  it('lists what blocks submitting and flags contradictory evidence', () => {
    const blocked = mount(ScorePanel, {
      props: { score: score({ hasContradictory: true }), canSubmit: false, readonly: false }
    })
    expect(blocked.text()).toContain('Before you submit')
    expect(blocked.text()).toContain('Complete the required evidence before submitting')
    expect(blocked.text()).toContain('Contradictory evidence is recorded')
    const ready = mount(ScorePanel, { props: { score: score(), canSubmit: true, readonly: false } })
    expect(ready.text()).not.toContain('Add at least one')
    expect(ready.text()).toContain('Ready to submit')
  })

  it('lists the rows that score 0 and the frame blocker while submit would refuse them', () => {
    const excluded = [
      { text: 'P1 scores 0: needs a variant', refused: true },
      { text: 'P2 scores 0: not scored (status review or contradicts)', refused: false }
    ]
    const w = mount(ScorePanel, {
      props: {
        score: score({ excluded }),
        canSubmit: false,
        readonly: false,
        blockers: ['Fix the rows that score 0 before submitting']
      }
    })
    expect(w.find('[data-testid="score-flags"]').text()).toContain('P1 scores 0: needs a variant')
    expect(w.text()).toContain('P2 scores 0')
    expect(w.text()).not.toContain('Ready to submit')
    expect(w.text()).toContain('Fix the rows that score 0 before submitting')
  })

  it('lists blockers such as an unknown PMID', () => {
    const w = mount(ScorePanel, {
      props: {
        score: score(),
        canSubmit: false,
        readonly: false,
        blockers: ['PMID 99 was not found']
      }
    })
    expect(w.text()).toContain('PMID 99 was not found')
    expect(w.text()).not.toContain('Add at least one')
  })

  it('hides the checklist when read-only', () => {
    const w = mount(ScorePanel, { props: { score: score(), canSubmit: false, readonly: true } })
    expect(w.text()).not.toContain('Before you submit')
  })
})
