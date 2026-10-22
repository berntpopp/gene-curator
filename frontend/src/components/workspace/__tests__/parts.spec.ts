import { describe, it, expect, vi } from 'vitest'
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
  genetic: 6,
  experimental: 1.5,
  total: 7.5,
  classification: 'Moderate',
  hasContradictory: false,
  geneticBreakdown: { caseLevel: 4, segregation: 2, caseControl: 0 },
  experimentalBreakdown: { function: 1.5, functionalAlteration: 0, modelsAndRescue: 0 },
  ...over
})

describe('ScorePanel', () => {
  it('shows the one live score with the classification mark and band bar', () => {
    const w = mount(ScorePanel, { props: { score: score(), canSubmit: true, readonly: false } })
    expect(w.text()).toContain('7.5')
    expect(w.text()).toContain('/ 18')
    expect(w.text()).toContain('Moderate')
    const bar = w.find('[role="meter"]')
    expect(bar.attributes('aria-valuenow')).toBe('7.5')
    expect(bar.attributes('aria-valuemax')).toBe('18')
    expect(w.text()).toContain('4.5 points to Strong')
  })

  it('lists the categories with counted and max points', () => {
    const w = mount(ScorePanel, { props: { score: score(), canSubmit: true, readonly: false } })
    const rows = w.findAll('tbody tr').map(r =>
      r
        .findAll('td')
        .map(td => td.text())
        .join(' ')
    )
    expect(rows).toContain('Case-level 4.0 12')
    expect(rows).toContain('Segregation 2.0 3')
    expect(rows.find(r => r.startsWith('Genetic'))).toContain('6.0')
    expect(rows.find(r => r.startsWith('Experimental'))).toContain('1.5')
  })

  it('says how far the next band is, and nothing at the top band', () => {
    const top = mount(ScorePanel, {
      props: {
        score: score({ total: 13, classification: 'Strong' }),
        canSubmit: true,
        readonly: false
      }
    })
    expect(top.text()).not.toContain('points to')
    const none = mount(ScorePanel, {
      props: {
        score: score({ total: 0, classification: 'No Known Disease Relationship' }),
        canSubmit: false,
        readonly: false
      }
    })
    expect(none.text()).toContain('0.1 points to Limited')
  })

  it('lists what blocks submitting and flags contradictory evidence', () => {
    const blocked = mount(ScorePanel, {
      props: { score: score({ hasContradictory: true }), canSubmit: false, readonly: false }
    })
    expect(blocked.text()).toContain('Before you submit')
    expect(blocked.text()).toContain('Add at least one scored genetic evidence item')
    expect(blocked.text()).toContain('Contradictory evidence is recorded')
    const ready = mount(ScorePanel, { props: { score: score(), canSubmit: true, readonly: false } })
    expect(ready.text()).not.toContain('Add at least one')
    expect(ready.text()).toContain('Ready to submit')
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
