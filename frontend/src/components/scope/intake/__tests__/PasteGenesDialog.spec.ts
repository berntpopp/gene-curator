import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PasteGenesDialog from '../PasteGenesDialog.vue'
import { geneResolveAPI } from '@/api/geneResolve'
import { assignmentsAPI } from '@/api/assignments'

const addToast = vi.hoisted(() => vi.fn())
vi.mock('@/stores/notifications', () => ({ useNotificationsStore: () => ({ addToast }) }))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))
vi.mock('@/api/geneResolve', () => ({ geneResolveAPI: { resolve: vi.fn() } }))
vi.mock('@/api/genes', () => ({ genesAPI: { bulkCreateGenes: vi.fn(), searchGenes: vi.fn() } }))
vi.mock('@/api/assignments', () => ({ assignmentsAPI: { bulkAssignGenes: vi.fn() } }))

const resolve = vi.mocked(geneResolveAPI.resolve)
const bulkAssign = vi.mocked(assignmentsAPI.bulkAssignGenes)
const local = (n: number) => ({
  hgnc_id: `HGNC:${n}`,
  symbol: `G${n}`,
  name: `gene ${n}`,
  gene_id: `g${n}`
})

const response = {
  items: [
    {
      input: 'G1',
      index: 0,
      status: 'resolved',
      match_type: 'symbol',
      source: 'local',
      candidates: [local(1)]
    },
    {
      input: 'old',
      index: 1,
      status: 'resolved',
      match_type: 'previous_symbol',
      candidates: [local(2)]
    },
    { input: 'g1', index: 2, status: 'resolved', candidates: [local(1)], duplicate_of: 0 },
    {
      input: 'AMB',
      index: 3,
      status: 'ambiguous',
      candidates: [local(3), { ...local(4), gene_id: null }]
    },
    { input: 'NOPE', index: 4, status: 'not_found', reason: 'lookup_cap' }
  ],
  counts: { resolved: 3, ambiguous: 1, not_found: 1 }
}

const dialogStub = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }

function mountDialog() {
  setActivePinia(createPinia())
  return mount(PasteGenesDialog, {
    props: { modelValue: true, scopeId: 's1' },
    attachTo: document.body,
    global: { stubs: { VDialog: dialogStub } }
  })
}

async function resolved() {
  resolve.mockResolvedValue(response as never)
  const w = mountDialog()
  await w.find('textarea').setValue('G1\nold, g1 AMB NOPE')
  await w.find('[data-testid=resolve]').trigger('click')
  await flushPromises()
  return w
}

describe('PasteGenesDialog', () => {
  beforeEach(() => {
    ;[resolve, bulkAssign].forEach(m => m.mockReset())
    addToast.mockReset()
  })

  it('counts pasted entries and disables Resolve for an empty or oversized list', async () => {
    const w = mountDialog()
    expect(w.find('[data-testid=resolve]').attributes('disabled')).toBeDefined()
    await w.find('textarea').setValue('A,B C')
    expect(w.find('[data-testid=paste-count]').text()).toBe('3 entries')
    await w.find('textarea').setValue('A')
    expect(w.find('[data-testid=paste-count]').text()).toBe('1 entry')
    await w.find('textarea').setValue(Array.from({ length: 1001 }, (_, i) => `G${i}`).join(' '))
    expect(w.text()).toContain('At most 1000')
    expect(w.find('[data-testid=resolve]').attributes('disabled')).toBeDefined()
  })

  it('sends the parsed symbols and summarises the outcome', async () => {
    const w = await resolved()
    expect(resolve).toHaveBeenCalledWith(['G1', 'old', 'g1', 'AMB', 'NOPE'])
    expect(w.find('[data-testid=summary]').attributes('role')).toBe('status')
    expect(w.find('[data-testid=summary]').text()).toContain(
      '3 resolved, 1 ambiguous, 1 not found, 1 repeated'
    )
    expect(w.text()).toContain('previous symbol')
    expect(w.text()).toContain('Repeats G1')
    expect(w.find('[data-testid=not-found]').text()).toContain('too many')
  })

  it('adds only the included genes, once an ambiguous one is chosen', async () => {
    bulkAssign.mockResolvedValue({ total_created: 3, total_skipped: 0, total_errors: 0 } as never)
    const w = await resolved()
    expect(w.find('[data-testid=add]').text()).toContain('Add 2 genes to scope')

    w.findAllComponents({ name: 'VSelect' })[0]!.vm.$emit('update:modelValue', 'HGNC:3')
    await flushPromises()
    expect(w.find('[data-testid=add]').text()).toContain('Add 3 genes to scope')

    await w.find('[data-testid=add]').trigger('click')
    await flushPromises()

    expect(bulkAssign.mock.calls[0]![0].gene_ids).toEqual(['g1', 'g2', 'g3'])
    expect(addToast).toHaveBeenCalledWith('3 genes added', 'success')
    expect(w.emitted('added')).toHaveLength(1)
    expect(w.emitted('update:modelValue')![0]).toEqual([false])
  })

  it('reports genes already in the scope and failures', async () => {
    bulkAssign.mockResolvedValue({ total_created: 1, total_skipped: 1, total_errors: 1 } as never)
    const w = await resolved()
    await w.find('[data-testid=add]').trigger('click')
    await flushPromises()
    expect(addToast).toHaveBeenCalledWith('1 gene added, 1 already in scope, 1 failed', 'warning')
  })

  it('explains a refused list in words, not raw validation JSON', async () => {
    resolve.mockRejectedValue({
      response: {
        data: { detail: [{ loc: ['body', 'symbols'], msg: 'List should have at most 1000 items' }] }
      }
    })
    const w = mountDialog()
    await w.find('textarea').setValue('A')
    await w.find('[data-testid=resolve]').trigger('click')
    await flushPromises()
    expect(addToast).toHaveBeenCalledWith(
      'Could not resolve the list. Symbols: List should have at most 1000 items.',
      'error'
    )
  })

  it('keeps the dialog open and tells the user when resolving or adding fails', async () => {
    resolve.mockRejectedValue(new Error('down'))
    const w = mountDialog()
    await w.find('textarea').setValue('A')
    await w.find('[data-testid=resolve]').trigger('click')
    await flushPromises()
    expect(addToast).toHaveBeenCalledWith('Could not resolve the list. Try again.', 'error')

    bulkAssign.mockRejectedValue(new Error('x'))
    const w2 = await resolved()
    await w2.find('[data-testid=add]').trigger('click')
    await flushPromises()
    expect(addToast).toHaveBeenCalledWith('0 genes added, 2 failed', 'error')
    expect(w2.emitted('added')).toBeUndefined()
  })

  it('goes back to the list to edit it, and cancels', async () => {
    const w = await resolved()
    await w
      .findAll('button')
      .find(b => b.text() === 'Edit list')!
      .trigger('click')
    expect(w.find('textarea').exists()).toBe(true)
    await w
      .findAll('button')
      .find(b => b.text() === 'Cancel')!
      .trigger('click')
    expect(w.emitted('update:modelValue')![0]).toEqual([false])
  })

  it('starts empty when reopened', async () => {
    const w = await resolved()
    await w.setProps({ modelValue: false })
    await w.setProps({ modelValue: true })
    expect(w.find('textarea').element.value).toBe('')
  })

  it('moves focus to the summary after resolving', async () => {
    const w = await resolved()
    expect(document.activeElement).toBe(w.find('[data-testid=summary]').element)
    w.unmount()
  })
})
