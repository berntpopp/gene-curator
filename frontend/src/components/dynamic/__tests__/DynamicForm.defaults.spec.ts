import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import DynamicForm from '../DynamicForm.vue'

const store = vi.hoisted(() => ({
  loading: false,
  error: null,
  getJsonSchema: vi.fn(() => null),
  getValidationResult: vi.fn(() => null),
  generateJsonSchema: vi.fn(),
  validateEvidence: vi.fn(),
  validateField: vi.fn(),
  clearValidationResult: vi.fn()
}))
vi.mock('@/stores', () => ({ useValidationStore: () => store }))
vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

const fields = {
  answered: { type: 'boolean', required: true, default: false },
  unspecified: { type: 'boolean', required: true },
  count: { type: 'number', default: 0 },
  note: { type: 'text', default: '' },
  nullable: { type: 'text', default: null },
  inherited: { type: 'boolean', readonly: true, default: false },
  nested: { type: 'object', properties: { answer: { type: 'boolean', default: false } } },
  rows: { type: 'array', items: { properties: { score: { type: 'number', default: 3 } } } }
}
const definition = { field_definitions: fields }
const expected = { answered: false, count: 0, note: '', nullable: null, nested: { answer: false } }
function mountForm(props: Record<string, unknown> = {}) {
  return mount(DynamicForm, {
    props: { schemaId: 'defaults', definition, ...props },
    global: {
      stubs: {
        DynamicField: {
          name: 'DynamicField',
          props: ['fieldName', 'modelValue'],
          template: '<span />'
        }
      }
    }
  })
}
const model = (wrapper: ReturnType<typeof mountForm>) =>
  wrapper.emitted('update:modelValue')?.at(-1)?.[0]
const save = async (wrapper: ReturnType<typeof mountForm>) => {
  await wrapper
    .findAll('button')
    .find(b => b.text().includes('Save draft'))!
    .trigger('click')
  return wrapper.emitted('save-draft')?.at(-1)?.[0]
}

beforeEach(() => vi.clearAllMocks())

describe('declared defaults in editable evidence', () => {
  it.each(['curation', 'precuration'])(
    'includes untouched defaults in %s save payloads',
    async kind => {
      const input = {}
      const config =
        kind === 'curation'
          ? definition
          : {
              field_definitions: {
                sections: [
                  { fields: Object.entries(fields).map(([id, field]) => ({ id, ...field })) }
                ]
              }
            }
      const wrapper = mountForm({ definition: config, initialData: input })
      await flushPromises()
      expect(model(wrapper)).toEqual(expected)
      expect(await save(wrapper)).toEqual(expected)
      expect(input).toEqual({})
      wrapper.unmount()
    }
  )

  it('preserves supplied false, zero, empty, null and loaded rows without mutating input', async () => {
    const input = {
      answered: false,
      count: 0,
      note: '',
      nullable: null,
      nested: null,
      rows: [{ score: null }, {}]
    }
    const wrapper = mountForm({
      initialData: input,
      definition: {
        field_definitions: {
          ...fields,
          answered: { ...fields.answered, default: true },
          count: { ...fields.count, default: 5 },
          note: { ...fields.note, default: 'assigned' },
          nullable: { ...fields.nullable, default: 'assigned' }
        }
      }
    })
    await flushPromises()
    // an unpinned definition is a draft: validated as rendered (#282)
    expect(store.validateEvidence).toHaveBeenCalledWith(
      input,
      'defaults',
      'form',
      undefined,
      wrapper.props('definition')
    )
    expect(model(wrapper)).toBeUndefined()
    expect(input.nested).toBeNull()
    expect(input.rows).toEqual([{ score: null }, {}])
    wrapper.unmount()
  })

  it('adopts late server evidence even after defaults were emitted', async () => {
    const wrapper = mountForm()
    await flushPromises()
    await wrapper.setProps({
      initialData: { answered: true, nested: { answer: true }, note: 'saved' }
    })
    expect(await save(wrapper)).toEqual({
      ...expected,
      answered: true,
      nested: { answer: true },
      note: 'saved'
    })
    wrapper.unmount()
  })

  it('keeps deliberate edits when late server evidence arrives', async () => {
    const wrapper = mountForm()
    await flushPromises()
    wrapper
      .findAllComponents({ name: 'DynamicField' })
      .find(f => f.props('fieldName') === 'note')!
      .vm.$emit('update:model-value', 'typed')
    await wrapper.setProps({ initialData: { note: 'saved' } })
    expect(await save(wrapper)).toEqual({ ...expected, note: 'typed' })
    wrapper.unmount()
  })

  it('initializes a late schema without replacing an edit already made', async () => {
    const wrapper = mountForm({ definition: { field_definitions: { note: fields.note } } })
    await flushPromises()
    wrapper.findComponent({ name: 'DynamicField' }).vm.$emit('update:model-value', 'typed')
    await wrapper.setProps({ definition })
    expect(await save(wrapper)).toEqual({ ...expected, note: 'typed' })
    wrapper.unmount()
  })

  it('initializes when the schema arrives and when a readonly form becomes editable', async () => {
    const wrapper = mountForm({ definition: { field_definitions: {} }, readonly: true })
    await wrapper.setProps({ definition })
    expect(model(wrapper)).toBeUndefined()
    await wrapper.setProps({ readonly: false })
    expect(model(wrapper)).toEqual(expected)
    wrapper.unmount()
  })

  it('does not add defaults in readonly mode or retain them over later readonly evidence', async () => {
    const wrapper = mountForm({ readonly: true, initialData: { note: 'review' } })
    await flushPromises()
    expect(model(wrapper)).toBeUndefined()
    await wrapper.setProps({ initialData: { note: 'new review' } })
    expect(model(wrapper)).toEqual({ note: 'new review' })
    await wrapper.setProps({ readonly: false })
    expect(model(wrapper)).toEqual({ ...expected, note: 'new review' })
    wrapper
      .findAllComponents({ name: 'DynamicField' })
      .find(f => f.props('fieldName') === 'note')!
      .vm.$emit('update:model-value', 'edited')
    await wrapper.setProps({ readonly: true, initialData: { note: 'server review' } })
    expect(model(wrapper)).toEqual({ note: 'server review' })
    wrapper.unmount()
  })
})
