import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import VersionMoveDialog from '../VersionMoveDialog.vue'
import { moveToVersion } from '@/api/methodologyImport'

const { showError, showSuccess } = vi.hoisted(() => ({ showError: vi.fn(), showSuccess: vi.fn() }))
vi.mock('@/composables/useNotifications', () => ({ showError, showSuccess }))
vi.mock('@/api/methodologyImport', () => ({ moveToVersion: vi.fn() }))
const post = vi.mocked(moveToVersion)

const item = {
  kind: 'curation',
  id: 'c1',
  gene: 'PKD1',
  status: 'active',
  from_version: 1,
  to_version: 2,
  dropped: ['old_note'],
  missing_required: [],
  old_class: 'strong',
  new_class: 'moderate',
  back_to: 'review'
}
const plan = () => ({ dry_run: true, schema_id: 'sc', to_version: 2, items: [item] })

const button = (text: string) =>
  [...document.body.querySelectorAll('button')].find(b => b.textContent?.includes(text))!

const openDialog = async () => {
  const wrapper = mount(VersionMoveDialog, {
    props: { schemaId: 'sc', schemaName: 'KGDB curation' },
    attachTo: document.body
  })
  await wrapper.find('button').trigger('click')
  await flushPromises()
  return wrapper
}

beforeEach(() => {
  vi.clearAllMocks()
  setActivePinia(createPinia())
})
afterEach(() => {
  document.body.innerHTML = ''
})

describe('VersionMoveDialog', () => {
  it('shows the dry-run plan, then applies the same target version', async () => {
    post.mockResolvedValueOnce(plan() as never)
    await openDialog()
    expect(post).toHaveBeenCalledWith('sc', true, undefined)
    expect(document.body.textContent).toContain('strong → moderate')
    expect(document.body.textContent).toContain('Copy to review')
    expect(document.body.textContent).toContain('Dropped: old_note')

    post.mockResolvedValueOnce({ ...plan(), dry_run: false } as never)
    button('Move').click()
    await flushPromises()
    expect(post).toHaveBeenLastCalledWith('sc', false, 2)
    expect(showSuccess).toHaveBeenCalledWith('1 moved to version 2; 1 need review again')
  })

  it('reports a stale plan (409) and keeps the dialog open', async () => {
    post.mockResolvedValueOnce(plan() as never)
    await openDialog()
    post.mockRejectedValueOnce({ response: { status: 409, data: { detail: 'plan again' } } })
    button('Move').click()
    await flushPromises()
    expect(showError).toHaveBeenCalled()
    expect(document.body.textContent).toContain('Move KGDB curation')
  })

  it('shows new required fields, precurations and an empty plan', async () => {
    const pre = { ...item, id: 'p1', kind: 'precuration', back_to: null, dropped: [] }
    const old = { ...item, id: 'o1', back_to: null, skipped: 'This scope is inactive' }
    const draft = { ...item, missing_required: ['new_req'], back_to: 'draft' }
    post.mockResolvedValueOnce({ ...plan(), items: [draft, pre, old] } as never)
    await openDialog()
    expect(document.body.textContent).toContain('Now required: new_req')
    expect(document.body.textContent).toContain('Copy to draft')
    expect(document.body.textContent).toContain('Moves')
    expect(document.body.textContent).toContain('Skipped')
    document.body.innerHTML = ''

    post.mockResolvedValueOnce({ ...plan(), items: [] } as never)
    await openDialog()
    expect(document.body.textContent).toContain('nothing to move')
  })

  it('reports a failed dry run without opening', async () => {
    post.mockRejectedValueOnce(new Error('offline'))
    await openDialog()
    expect(showError).toHaveBeenCalled()
    expect(document.body.textContent).not.toContain('Move KGDB curation')
  })
})
