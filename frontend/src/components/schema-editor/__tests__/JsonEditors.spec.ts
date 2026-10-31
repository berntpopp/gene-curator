import { describe, it, expect } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import JsonBlockEditor from '../JsonBlockEditor.vue'
import AdvancedJson from '../AdvancedJson.vue'

const mountBlock = (modelValue: unknown, nullable = false) =>
  mount(JsonBlockEditor, { props: { modelValue, label: 'Block', nullable } })

describe('JsonBlockEditor', () => {
  it('emits parsed objects and the parse error for each edit', async () => {
    const wrapper = mountBlock({ a: 1 })
    const textarea = wrapper.find('textarea')
    expect((textarea.element as HTMLTextAreaElement).value).toContain('"a": 1')
    await textarea.setValue('{"b": 2}')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([{ b: 2 }])
    expect(wrapper.emitted('error')?.at(-1)).toEqual([''])
    await textarea.setValue('{bad')
    expect(wrapper.emitted('error')?.at(-1)?.[0]).not.toBe('')
    expect(wrapper.text()).toContain(String(wrapper.emitted('error')?.at(-1)?.[0]))
    await textarea.setValue('[1]')
    expect(wrapper.emitted('error')?.at(-1)).toEqual(['Must be a JSON object ({ ... })'])
    await textarea.setValue('')
    expect(wrapper.emitted('error')?.at(-1)?.[0]).toContain('Required')
    expect(wrapper.emitted('update:modelValue')).toHaveLength(1)
  })

  it('treats empty text as null when nullable', async () => {
    const wrapper = mountBlock(null, true)
    expect((wrapper.find('textarea').element as HTMLTextAreaElement).value).toBe('')
    await wrapper.find('textarea').setValue('  ')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([null])
  })

  it('shows a value changed elsewhere, replacing invalid text, but keeps equal text', async () => {
    const wrapper = mountBlock({ a: 1 })
    const textarea = wrapper.find('textarea')
    await textarea.setValue('{"a":1}')
    await wrapper.setProps({ modelValue: { a: 1 } })
    expect((textarea.element as HTMLTextAreaElement).value).toBe('{"a":1}')
    await textarea.setValue('{oops')
    await wrapper.setProps({ modelValue: { a: 2 } })
    expect((textarea.element as HTMLTextAreaElement).value).toContain('"a": 2')
    expect(wrapper.emitted('error')?.at(-1)).toEqual([''])
  })
})

describe('AdvancedJson', () => {
  it('has one editor per block and reports updates and errors by block', async () => {
    const wrapper = mount(AdvancedJson, {
      props: {
        modelValue: {
          field_definitions: {},
          ui_configuration: { sections: [] },
          validation_rules: {},
          scoring_configuration: null,
          workflow_states: {}
        },
        errors: { ui_configuration: 'bad' }
      }
    })
    await flushPromises()
    const editors = wrapper.findAllComponents(JsonBlockEditor)
    expect(editors).toHaveLength(5)
    expect(wrapper.text()).toContain('Workflow states')
    // The editor already has a Scoring tab; its JSON block is named apart (MUI-23)
    expect(wrapper.findAll('.v-tab').map(t => t.text())).toContain('Scoring configuration')
    editors[1]!.vm.$emit('update:modelValue', { x: 1 })
    editors[3]!.vm.$emit('error', 'nope')
    expect(wrapper.emitted('update')?.[0]).toEqual(['ui_configuration', { x: 1 }])
    expect(wrapper.emitted('error')?.[0]).toEqual(['scoring_configuration', 'nope'])
    expect(editors[3]!.props('nullable')).toBe(true)
    expect(editors[0]!.props('nullable')).toBe(false)
  })
})
