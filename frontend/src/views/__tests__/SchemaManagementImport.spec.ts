import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import SchemaManagement from '@/views/SchemaManagement.vue'
import { useSchemasStore } from '@/stores/schemas'
import { useMethodologyImportStore } from '@/stores/methodologyImport'
import { importMethodology } from '@/api/methodologyImport'
import { call, vmOf } from './vm'

const { logger, showError, showSuccess } = vi.hoisted(() => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
  showError: vi.fn(),
  showSuccess: vi.fn()
}))
vi.mock('vue-router', async importOriginal => ({
  ...(await importOriginal<typeof import('vue-router')>()),
  useRouter: () => ({ push: vi.fn() })
}))
vi.mock('@/composables/useLogger', () => ({ useLogger: () => logger }))
vi.mock('@/composables/useNotifications', () => ({ showError, showSuccess }))
vi.mock('@/api/methodologyImport', () => ({ importMethodology: vi.fn() }))
const post = vi.mocked(importMethodology)

const bundle = { schemas: [{ name: 'KGDB curation' }], workflow_pairs: [] }
const plan = (errors: string[] = [], action = 'create') => ({
  dry_run: true,
  errors,
  items: [{ kind: 'schema', name: 'KGDB curation', version: '1.0.0', action }]
})

const fileEvent = (text: string | null) => {
  const input = document.createElement('input')
  const files = text === null ? [] : [{ name: 'kgdb.json', text: async () => text }]
  Object.defineProperty(input, 'files', { value: files })
  return { target: input } as unknown as Event
}

async function mountView() {
  const schemas = useSchemasStore()
  const fetch = vi.spyOn(schemas, 'fetchSchemas').mockResolvedValue(undefined as never)
  const w = mount(SchemaManagement, { attachTo: document.body })
  await flushPromises()
  return { w, vm: vmOf(w), fetch }
}

describe('SchemaManagement methodology import', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })
  afterEach(() => {
    document.body.innerHTML = ''
  })

  it('shows the dry-run plan first and writes only on confirm', async () => {
    post.mockResolvedValueOnce(plan() as never)
    const { vm, fetch } = await mountView()
    await call(vm, 'onImportFile', fileEvent(JSON.stringify(bundle)))
    expect(post).toHaveBeenCalledWith(bundle, true)
    expect(vm.importDialog).toBe(true)
    await flushPromises()
    expect(document.body.textContent).toContain('KGDB curation')
    expect(document.body.textContent).toContain('Nothing is written until you confirm')

    const done = plan()
    done.items[0] = { ...done.items[0]!, action: 'new_version', methodology_version: 3 } as never
    post.mockResolvedValueOnce({ ...done, dry_run: false } as never)
    await call(vm, 'confirmImport')
    expect(post).toHaveBeenLastCalledWith(bundle, false)
    expect(showSuccess).toHaveBeenCalledWith('KGDB curation published as version 3')
    expect(vm.importDialog).toBe(false)
    expect(fetch).toHaveBeenCalledTimes(2)
  })

  it('says when a re-import changes nothing', async () => {
    post.mockResolvedValue(plan([], 'unchanged') as never)
    const { vm } = await mountView()
    await call(vm, 'onImportFile', fileEvent(JSON.stringify(bundle)))
    await call(vm, 'confirmImport')
    expect(showSuccess).toHaveBeenCalledWith('Already up to date; nothing changed')
  })

  it('lists validator errors and blocks the import', async () => {
    post.mockResolvedValueOnce(plan(['scoring_configuration.tests[0]: expected class']) as never)
    const { vm } = await mountView()
    await call(vm, 'onImportFile', fileEvent(JSON.stringify(bundle)))
    await flushPromises()
    expect(document.body.textContent).toContain('The file cannot be imported')
    expect(document.body.textContent).toContain('expected class')
  })

  it('anchors each error to its row: Refused or Blocked (Wave 10 polish)', async () => {
    const refused = plan(['schema KGDB curation: has unpublished edits'], 'refused')
    refused.items.push(
      { kind: 'workflow_pair', name: 'KGDB pair', version: '1', action: 'create' },
      { kind: 'scope_default', name: 'kidney', version: '', action: 'update' }
    )
    refused.errors.push('scope_default: no scope kidney')
    post.mockResolvedValueOnce(refused as never)
    const { vm } = await mountView()
    await call(vm, 'onImportFile', fileEvent(JSON.stringify(bundle)))
    await flushPromises()
    const rows = [...document.body.querySelectorAll('tbody tr')]
      .map(r => r.textContent ?? '')
      .filter(t => /KGDB|kidney/.test(t))
    expect(rows[0]).toContain('has unpublished edits')
    expect(rows[0]).toContain('Refused')
    expect(rows[1]).toContain('Create')
    expect(rows[2]).toContain('Blocked')
    expect(rows[2]).toContain('no scope kidney')
  })

  it('names created pairs in the success message', async () => {
    const created = plan()
    created.items = [{ kind: 'workflow_pair', name: 'KGDB pair', version: '1', action: 'create' }]
    post.mockResolvedValue(created as never)
    const { vm } = await mountView()
    await call(vm, 'onImportFile', fileEvent(JSON.stringify(bundle)))
    await call(vm, 'confirmImport')
    expect(showSuccess).toHaveBeenCalledWith('Workflow pair KGDB pair created')
  })

  it('rejects a file that is not JSON without calling the server', async () => {
    const { vm } = await mountView()
    await call(vm, 'onImportFile', fileEvent('{ nope'))
    expect(post).not.toHaveBeenCalled()
    expect(showError).toHaveBeenCalledWith('The file is not valid JSON')
    await call(vm, 'onImportFile', fileEvent(null))
    expect(post).not.toHaveBeenCalled()
  })

  it('shows the server report when the confirmed import is refused', async () => {
    post.mockResolvedValueOnce(plan() as never)
    const { vm } = await mountView()
    await call(vm, 'onImportFile', fileEvent(JSON.stringify(bundle)))
    post.mockRejectedValueOnce({
      response: { status: 422, data: { detail: plan(['changed meanwhile']) } }
    })
    await call(vm, 'confirmImport')
    expect(showError).toHaveBeenCalled()
    expect(useMethodologyImportStore().plan!.errors).toEqual(['changed meanwhile'])
    expect(vm.importDialog).toBe(true)
  })

  it('reports a failed dry run', async () => {
    post.mockRejectedValueOnce({
      response: { status: 403, data: { detail: 'Not enough permissions' } }
    })
    const { vm } = await mountView()
    await call(vm, 'onImportFile', fileEvent(JSON.stringify(bundle)))
    expect(showError).toHaveBeenCalledWith('Not enough permissions')
    expect(vm.importDialog).toBe(false)
  })

  it('shows why the server refused the file shape (e.g. more than 50 schemas)', async () => {
    post.mockRejectedValueOnce({
      response: {
        status: 422,
        data: { detail: [{ loc: ['body', 'schemas'], msg: 'List should have at most 50 items' }] }
      }
    })
    const { vm } = await mountView()
    await call(vm, 'onImportFile', fileEvent(JSON.stringify(bundle)))
    expect(showError).toHaveBeenCalledWith(expect.stringContaining('at most 50 items'))
    expect(vm.importDialog).toBe(false)
  })
})
