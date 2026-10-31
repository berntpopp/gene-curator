/** Workflow-stage builder, import diff and merged field types (#282) */
import { describe, it, expect, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import WorkflowStagesEditor from '../WorkflowStagesEditor.vue'
import ColumnsEditor from '../ColumnsEditor.vue'
import FieldDialog from '../FieldDialog.vue'
import { addStage, nextOf, removeStage, setNext, shapeOf, stageNames } from '../workflowModel'
import { schemaChanges } from '../importDiff'
import { FIELD_TYPES, pickerType, typeTitle, type FieldDef } from '../fieldModel'
import { call, vmOf } from '@/views/__tests__/vm'

afterEach(() => {
  document.body.innerHTML = ''
})

const list = () => ({
  states: [{ name: 'draft', permissions: ['curator'] }, { name: 'submitted' }],
  transitions: { draft: ['submitted'], submitted: [] } as Record<string, string[]>,
  initial_state: 'draft'
})
const map = () => ({
  entry: { allowed_transitions: ['precuration'] },
  precuration: { allowed_transitions: ['review'] },
  review: { allowed_transitions: ['precuration'], reviewers_required: 1 }
})

describe('workflowModel', () => {
  it('reads and edits both stored shapes, keeping unknown keys', () => {
    expect([shapeOf(list()), shapeOf(map()), shapeOf(null), shapeOf({ states: 1 })]).toEqual([
      'list',
      'map',
      null,
      null
    ])
    const wf = list() as Record<string, unknown>
    addStage(wf, 'approved')
    addStage(wf, 'draft') // already there
    setNext(wf, 'submitted', ['approved'])
    expect(stageNames(wf)).toEqual(['draft', 'submitted', 'approved'])
    removeStage(wf, 'draft')
    expect(wf).toEqual({
      states: [{ name: 'submitted' }, { name: 'approved' }],
      transitions: { submitted: ['approved'], approved: [] }
    })
    const m = map() as Record<string, unknown>
    addStage(m, 'active')
    setNext(m, 'review', ['precuration', 'active'])
    removeStage(m, 'precuration')
    expect(m).toEqual({
      entry: { allowed_transitions: [] },
      review: { allowed_transitions: ['active'], reviewers_required: 1 },
      active: { allowed_transitions: [] }
    })
    expect(nextOf(m, 'nowhere')).toEqual([])
  })
})

describe('WorkflowStagesEditor', () => {
  const mountEditor = (modelValue: unknown, extra = {}) =>
    mount(WorkflowStagesEditor, {
      props: { modelValue, hasScoring: true, ...extra },
      attachTo: document.body
    })
  const last = (w: ReturnType<typeof mountEditor>) =>
    w.emitted('update:modelValue')!.at(-1)![0] as Record<string, unknown>

  it('edits a stage map: description, reviewers, add and remove', async () => {
    const w = mountEditor(map(), {
      diagnostics: [
        { field: 'workflow_states', message: 'Missing required stage: x', severity: 'error' },
        {
          field: 'workflow_states.review.reviewers_required',
          message: 'reviewers 1-5',
          severity: 'error'
        }
      ]
    })
    expect(w.text()).toContain('Missing required stage: x')
    expect(w.find('[data-testid="stage-review"]').text()).toContain('reviewers 1-5')
    const vm = vmOf(w)
    await call(vm, 'setKey', 'review', 'reviewers_required', '2', true)
    expect((last(w).review as Record<string, unknown>).reviewers_required).toBe(2)
    await call(vm, 'setKey', 'entry', 'description', 'Start')
    expect((last(w).entry as Record<string, unknown>).description).toBe('Start')
    await call(vm, 'setKey', 'review', 'reviewers_required', '')
    expect('reviewers_required' in (last(w).review as object)).toBe(false)
    await call(vm, 'setKey', 'nowhere', 'description', 'x')
    vm.newName = 'active'
    await call(vm, 'add')
    expect(last(w).active).toEqual({ allowed_transitions: [] })
    vm.newName = '   '
    await call(vm, 'add') // blank name: nothing
    await w.find('[aria-label="Remove stage entry"]').trigger('click')
    expect('entry' in last(w)).toBe(false)
    const open = (label: string) => w.findAll('button').find(b => b.text() === label)!
    await open('Open form').trigger('click')
    await open('Open scoring').trigger('click')
    expect(w.emitted('open')).toEqual([['fields'], ['scoring']])
    expect(w.find('[aria-label="Description of review"]').exists()).toBe(true)
    expect(w.find('[aria-label="Next stages of review"]').exists()).toBe(true)
    vm.newName = '  review  ' // trimmed like addStage: taken
    expect(vm.canAdd).toBe(false)
  })

  it('sets the initial state of a list and starts a missing workflow', async () => {
    const w = mountEditor(list())
    await flushPromises()
    const select = w.findAllComponents({ name: 'VSelect' })[0]!
    select.vm.$emit('update:modelValue', 'submitted')
    expect(last(w).initial_state).toBe('submitted')
    select.vm.$emit('update:modelValue', null)
    expect('initial_state' in last(w)).toBe(false)
    const next = w.findAllComponents({ name: 'VSelect' })[1]!
    next.vm.$emit('update:modelValue', [])
    expect((last(w).transitions as Record<string, unknown>).draft).toEqual([])

    const empty = mountEditor(null)
    expect(empty.text()).toContain('Advanced JSON')
    await empty
      .findAll('button')
      .find(b => b.text() === 'Create workflow')!
      .trigger('click')
    expect(last(empty).initial_state).toBe('draft')
  })
})

describe('schemaChanges', () => {
  it('names added, removed and changed fields and other changed blocks', () => {
    const current = {
      field_definitions: { a: { type: 'text', order: 1 }, b: { type: 'text', order: 2 } },
      scoring_configuration: null,
      workflow_states: { x: { allowed_transitions: [] } }
    }
    const incoming = {
      field_definitions: { a: { type: 'number' }, c: { type: 'text' } },
      scoring_configuration: { engine: 'point_model' },
      workflow_states: { x: { allowed_transitions: [] } }
    }
    expect(schemaChanges(current, incoming)).toEqual([
      'Fields added: c',
      'Fields removed: b',
      'Fields changed: a',
      'Scoring changed'
    ])
    const reordered = { field_definitions: { b: { type: 'text' }, a: { type: 'text' } } }
    expect(schemaChanges(current, reordered)).toEqual(['Fields reordered', 'Workflow changed'])
  })

  it('ignores key order and the column order the import stamps', () => {
    const stored = {
      field_definitions: {
        t: { type: 'evidence_table', columns: { p: { type: 'text', order: 1 } } }
      }
    }
    const file = {
      field_definitions: { t: { columns: { p: { type: 'text' } }, type: 'evidence_table' } }
    }
    expect(schemaChanges(stored, file)).toEqual([])
  })
})

describe('merged field types', () => {
  it('shows string as Text and enum as Single choice without rewriting them', async () => {
    expect(FIELD_TYPES.map(t => t.value)).not.toContain('string')
    expect(FIELD_TYPES.map(t => t.value)).not.toContain('enum')
    expect([pickerType('string'), pickerType('enum'), pickerType('url')]).toEqual([
      'text',
      'select',
      'url'
    ])
    expect([typeTitle('string'), typeTitle('enum'), typeTitle('odd'), typeTitle(null)]).toEqual([
      'Text',
      'Single choice',
      'odd',
      'no type'
    ])
    const field: FieldDef = { id: 'f', type: 'string', label: 'F' }
    const w = mount(FieldDialog, { props: { field, otherIds: [] }, attachTo: document.body })
    await flushPromises()
    const type = w.findAllComponents({ name: 'VSelect' }).find(s => s.props('label') === 'Type')!
    expect(type.props('modelValue')).toBe('text')
    await call(vmOf(w), 'save')
    expect((w.emitted('save')![0]![0] as FieldDef).type).toBe('string')
    type.vm.$emit('update:modelValue', 'object')
    await flushPromises()
    expect(w.findComponent(ColumnsEditor).props('title')).toBe('Fields in this group')
  })
})

describe('groups in the field editor', () => {
  it('edits a group of fields and a group inside it', async () => {
    const field: FieldDef = {
      id: 'g',
      type: 'object',
      properties: { inner: { type: 'object', properties: { x: { type: 'text' } } } }
    }
    const w = mount(FieldDialog, { props: { field, otherIds: [] }, attachTo: document.body })
    await flushPromises()
    const editors = w.findAllComponents(ColumnsEditor)
    expect(editors).toHaveLength(2)
    expect(editors[1]!.props('title')).toBe('Fields in inner')
    editors[1]!.vm.$emit('update:modelValue', { y: { type: 'number', order: 1 } })
    await call(vmOf(editors[0]!), 'add')
    await call(vmOf(w), 'save')
    expect((w.emitted('save')![0]![0] as FieldDef).properties).toEqual({
      inner: { type: 'object', properties: { y: { type: 'number', order: 1 } }, order: 1 },
      field_2: { type: 'text', label: '', order: 2 }
    })
    expect(vmOf(editors[0]!).keyRule).toBeTypeOf('function')
    const rule = (vmOf(editors[0]!).keyRule as (i: number) => (v: string) => unknown)(0)
    expect([rule(''), rule('field_2')]).toEqual([
      'Field id is required',
      'Field ids must be unique'
    ])
  })
})
