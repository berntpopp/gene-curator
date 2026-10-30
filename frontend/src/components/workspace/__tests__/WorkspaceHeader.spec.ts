import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import WorkspaceHeader from '../WorkspaceHeader.vue'

const router = createRouter({
  history: createMemoryHistory(),
  routes: [{ path: '/:p(.*)', component: { template: '<div/>' } }]
})

const base = {
  crumbs: [
    { text: 'Kidney genetics', to: '/scopes/s1' },
    { text: 'COL4A5', to: '/genes/g1' },
    { text: 'Curation' }
  ],
  title: 'COL4A5',
  subtitle: 'Alport syndrome',
  moi: 'X-linked',
  stage: 'curation',
  state: 'saved' as const,
  savedAt: null,
  readonly: false,
  showSubmit: true,
  canSubmit: true,
  saving: false
}

const mountHeader = (props: Record<string, unknown> = {}) =>
  mount(WorkspaceHeader, { props: { ...base, ...props }, global: { plugins: [router] } })

describe('WorkspaceHeader', () => {
  it('shows the breadcrumb with links for all but the current page', () => {
    const w = mountHeader()
    const nav = w.find('nav[aria-label="Breadcrumb"]')
    expect(nav.findAll('a').map(a => a.attributes('href'))).toEqual(['/scopes/s1', '/genes/g1'])
    expect(nav.find('[aria-current="page"]').text()).toBe('Curation')
  })

  it('shows title, disease, inheritance, stage line and save state', () => {
    const w = mountHeader({ state: 'unsaved' })
    expect(w.find('h1').text()).toContain('COL4A5')
    expect(w.text()).toContain('Alport syndrome')
    expect(w.text()).toContain('X-linked')
    expect(w.find('.stage-line').exists()).toBe(true)
    expect(w.text()).toContain('Unsaved changes')
  })

  it('emits save, submit and retry', async () => {
    const w = mountHeader({ state: 'failed' })
    await w.find('[data-testid="ws-save"]').trigger('click')
    await w.find('[data-testid="ws-submit"]').trigger('click')
    await w.find('.save-state button').trigger('click')
    expect(w.emitted('save')).toHaveLength(1)
    expect(w.emitted('submit')).toHaveLength(1)
    expect(w.emitted('retry')).toHaveLength(1)
  })

  it('says next to Submit why it is blocked', () => {
    const reason = 'Fix 1 unknown PMID before submitting: PMID 999 not found in Europe PMC'
    expect(mountHeader().find('[data-testid="ws-blockers"]').exists()).toBe(false)
    const w = mountHeader({ canSubmit: false, blockers: [reason] })
    expect(w.find('[data-testid="ws-blockers"]').text()).toBe(reason)
  })

  // #406: the click whose mousedown commits a cell's edit (making Submit allowed) must land;
  // browsers dispatch no click on a button that was disabled at mousedown
  it('marks submit unavailable without disabling it, and disables both actions when read-only', () => {
    const blocked = mountHeader({ canSubmit: false }).find('[data-testid="ws-submit"]')
    expect(blocked.attributes('aria-disabled')).toBe('true')
    expect(blocked.attributes('disabled')).toBeUndefined()
    const ro = mountHeader({ readonly: true })
    expect(ro.find('[data-testid="ws-save"]').attributes('disabled')).toBeDefined()
    expect(ro.find('[data-testid="ws-submit"]').attributes('disabled')).toBeDefined()
    expect(mountHeader({ showSubmit: false }).find('[data-testid="ws-submit"]').exists()).toBe(
      false
    )
  })

  it('labels a susceptibility entity only (W9 monkey)', () => {
    expect(mountHeader({ relationship: 'susceptibility' }).text()).toContain('Susceptibility')
    expect(mountHeader({ relationship: 'mendelian' }).text()).not.toContain('Susceptibility')
  })

  it('shows the inheritance in plain words', () => {
    const w = mountHeader({ moi: 'autosomal_dominant' })
    expect(w.text()).not.toContain('autosomal_dominant')
    expect(w.find('.ws-title__text').text()).toContain('Autosomal dominant')
  })

  // #267: the blocker text appearing or disappearing must never move the buttons
  // (a click whose mousedown commits a PMID cell would otherwise land beside Save draft)
  it('keeps the blocker message out of the button row', () => {
    // aria-describedby links Submit to the message; it does not change the layout
    const actions = (w: ReturnType<typeof mountHeader>) =>
      w.find('.ws-actions').element.outerHTML.replace(/ aria-describedby="[^"]*"/, '')
    const reason = 'Fix 1 unknown PMID before submitting: PMID 999 not found in Europe PMC'
    const blocked = mountHeader({ canSubmit: true, blockers: [reason] })
    expect(blocked.find('[data-testid="ws-blockers"]').text()).toBe(reason)
    expect(blocked.find('.ws-actions [data-testid="ws-blockers"]').exists()).toBe(false)
    expect(actions(blocked)).toBe(actions(mountHeader()))
  })

  it('preserves the pressed Save control when blur updates status and blockers', async () => {
    const w = mountHeader()
    const save = w.find('[data-testid="ws-save"]')
    await save.trigger('mousedown')
    await w.setProps({ state: 'unsaved', blockers: ['PMID 99 was not found'], canSubmit: false })
    expect(w.find('[data-testid="ws-save"]').element).toBe(save.element)
    await save.trigger('mouseup')
    await save.trigger('click')
    expect(w.emitted('save')).toHaveLength(1)
    expect(w.emitted('submit')).toBeUndefined()
  })
  it('describes Submit with the blocker text', () => {
    const w = mountHeader({ canSubmit: false, blockers: ['PMID 9 not found'] })
    const id = w.find('[data-testid="ws-blockers"]').attributes('id')
    expect(id).toBe('ws-blockers')
    expect(w.find('[data-testid="ws-submit"]').attributes('aria-describedby')).toBe(id)
    expect(mountHeader().find('[data-testid="ws-submit"]').attributes('aria-describedby')).toBe(
      undefined
    )
  })

  // A blocked Submit without blocker text (form invalid or empty) says why when clicked
  it('shows a reason when a blocked Submit without blockers is clicked', async () => {
    const w = mountHeader({ canSubmit: false })
    expect(w.find('[data-testid="ws-blockers"]').exists()).toBe(false)
    await w.find('[data-testid="ws-submit"]').trigger('click')
    const reason = w.find('[data-testid="ws-blockers"]')
    expect(reason.text()).toBe('Complete the required evidence before submitting')
    expect(w.find('[data-testid="ws-submit"]').attributes('aria-describedby')).toBe('ws-blockers')
    await w.setProps({ canSubmit: true })
    expect(w.find('[data-testid="ws-blockers"]').exists()).toBe(false)
  })
})
