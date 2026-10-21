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

  it('disables submit when not allowed and hides actions when read-only', () => {
    expect(
      mountHeader({ canSubmit: false }).find('[data-testid="ws-submit"]').attributes('disabled')
    ).toBeDefined()
    const ro = mountHeader({ readonly: true })
    expect(ro.find('[data-testid="ws-save"]').exists()).toBe(false)
    expect(ro.find('[data-testid="ws-submit"]').exists()).toBe(false)
    expect(mountHeader({ showSubmit: false }).find('[data-testid="ws-submit"]').exists()).toBe(
      false
    )
  })

  it('disables save while blocked', () => {
    const w = mountHeader({ saveBlocked: true })
    expect(w.find('[data-testid="ws-save"]').attributes('disabled')).toBeDefined()
  })
})
