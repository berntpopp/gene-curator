import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ApproveChecklistDialog from '../ApproveChecklistDialog.vue'
import RequestChangesDialog from '../RequestChangesDialog.vue'

const dialogStub = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }
const opts = (props: Record<string, unknown>) => ({
  props: props as never,
  global: { stubs: { VDialog: dialogStub } }
})

const approveProps = {
  modelValue: true,
  geneSymbol: 'PKD1',
  scopeName: 'Kidney genetics',
  classification: 'Definitive',
  total: 16.5,
  curator: 'Alice Smith',
  blockers: [] as { key: string; label: string }[],
  busy: false,
  error: null as string | null
}

describe('ApproveChecklistDialog', () => {
  it('names what is approved and shows classification, score and curator', () => {
    const w = mount(ApproveChecklistDialog, opts(approveProps))
    expect(w.text()).toContain('Approve PKD1 for Kidney genetics?')
    expect(w.text()).toContain('16.5')
    expect(w.text()).toContain('Alice Smith')
    expect(w.text()).toContain('Definitive')
  })

  it('stays disabled until every checklist item is ticked, counting what is left', async () => {
    const w = mount(ApproveChecklistDialog, opts(approveProps))
    const btn = () => w.find('[data-testid=approve-confirm]')
    expect(w.findAll('input[type=checkbox]')).toHaveLength(4)
    expect(btn().attributes('disabled')).toBeDefined()
    expect(w.find('[data-testid=checks-left]').text()).toBe('4 checks left')
    for (const cb of w.findAll('input[type=checkbox]')) await cb.setValue(true)
    expect(btn().attributes('disabled')).toBeUndefined()
    expect(w.find('[data-testid=checks-left]').text()).toBe('')
  })

  it('has no replication check below Definitive', () => {
    const w = mount(ApproveChecklistDialog, opts({ ...approveProps, classification: 'Strong' }))
    expect(w.findAll('input[type=checkbox]')).toHaveLength(3)
  })

  it('blocks approval and lists items still unreviewed or queried', async () => {
    const w = mount(
      ApproveChecklistDialog,
      opts({ ...approveProps, blockers: [{ key: 'g.a[1]', label: 'G › A [1]' }] })
    )
    for (const cb of w.findAll('input[type=checkbox]')) await cb.setValue(true)
    expect(w.find('[data-testid=blockers]').text()).toContain('G › A [1]')
    expect(w.find('[data-testid=approve-confirm]').attributes('disabled')).toBeDefined()
  })

  it('emits approve with the note, and cancel', async () => {
    const w = mount(ApproveChecklistDialog, opts({ ...approveProps, classification: 'Strong' }))
    for (const cb of w.findAll('input[type=checkbox]')) await cb.setValue(true)
    await w.find('textarea').setValue('Looks good')
    await w.find('[data-testid=approve-confirm]').trigger('click')
    expect(w.emitted('approve')![0]).toEqual(['Looks good'])
    await w.find('[data-testid=approve-cancel]').trigger('click')
    expect(w.emitted('update:modelValue')![0]).toEqual([false])
  })

  it('shows an API error inside the dialog', () => {
    const w = mount(ApproveChecklistDialog, opts({ ...approveProps, error: 'Not allowed' }))
    expect(w.text()).toContain('Not allowed')
  })
})

describe('RequestChangesDialog', () => {
  const props = {
    modelValue: true,
    geneSymbol: 'PKD1',
    todos: '- G: Explain',
    busy: false,
    error: null
  }

  it('prefills the feedback with the open queries as a to-do list', () => {
    const w = mount(RequestChangesDialog, opts(props))
    expect((w.find('textarea').element as HTMLTextAreaElement).value).toBe('- G: Explain')
  })

  it('requires feedback and emits it', async () => {
    const w = mount(RequestChangesDialog, opts({ ...props, todos: '' }))
    expect(w.find('[data-testid=changes-confirm]').attributes('disabled')).toBeDefined()
    await w.find('textarea').setValue('Please fix')
    await w.find('[data-testid=changes-confirm]').trigger('click')
    expect(w.emitted('reject')![0]).toEqual(['Please fix'])
  })

  it('limits the feedback to the API maximum and shows a counter', async () => {
    const w = mount(RequestChangesDialog, opts(props))
    expect(w.find('textarea').attributes('maxlength')).toBe('2000')
    expect(w.text()).toContain('/ 2000')
  })

  it('refills when reopened with new queries and cancels', async () => {
    const w = mount(RequestChangesDialog, opts({ ...props, modelValue: false }))
    await w.setProps({ todos: '- X: y', modelValue: true })
    expect((w.find('textarea').element as HTMLTextAreaElement).value).toBe('- X: y')
    await w.find('[data-testid=changes-cancel]').trigger('click')
    expect(w.emitted('update:modelValue')![0]).toEqual([false])
  })
})
