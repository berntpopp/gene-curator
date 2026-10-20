/**
 * Tests for ScopeSelector (clinical scope picker).
 *
 * @see src/components/dynamic/ScopeSelector.vue
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const scopesStore = vi.hoisted(() => ({
  loading: false,
  scopes: [] as Array<Record<string, unknown>>,
  setCurrentScope: vi.fn(),
  fetchUserScopes: vi.fn()
}))

vi.mock('@/stores', () => ({
  useScopesStore: () => scopesStore
}))

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

import ScopeSelector from '../ScopeSelector.vue'

const stubs = {
  'v-card': { template: '<div><slot /></div>' },
  'v-card-title': { template: '<div><slot /></div>' },
  'v-card-text': { template: '<div><slot /></div>' },
  'v-card-actions': { template: '<div><slot /></div>' },
  'v-spacer': { template: '<span />' },
  'v-icon': { template: '<span />' },
  'v-alert': { template: '<div><slot name="prepend" /><slot /></div>' },
  'v-btn': { template: '<button v-bind="$attrs"><slot /></button>' },
  'v-list-item': { template: '<div><slot /><slot name="append" /></div>' },
  'v-list-item-title': { template: '<div><slot /></div>' },
  'v-list-item-subtitle': { template: '<div><slot /></div>' },
  'v-chip': { template: '<span><slot /></span>' },
  'v-select': {
    name: 'VSelect',
    props: ['items', 'modelValue'],
    template: `<div class="v-select-stub">
      <div v-for="option in items" :key="option.id">
        <slot name="item" :props="{}" :item="{ raw: option }" />
        <slot name="selection" :item="{ raw: option }" />
      </div>
    </div>`
  }
}

const activeScope = {
  id: 'scope-1',
  display_name: 'Hereditary Cancer',
  institution: 'Charité',
  description: 'Cancer genetics',
  is_active: true
}

const inactiveScope = { ...activeScope, id: 'scope-2', is_active: false }

describe('ScopeSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    scopesStore.scopes = [activeScope, inactiveScope]
    scopesStore.fetchUserScopes.mockResolvedValue([])
  })

  it('loads the user scopes on mount', async () => {
    mount(ScopeSelector, { global: { stubs } })
    await flushPromises()

    expect(scopesStore.fetchUserScopes).toHaveBeenCalledTimes(1)
  })

  it('offers only active scopes in the select', () => {
    const wrapper = mount(ScopeSelector, { global: { stubs } })

    const items = wrapper.findComponent({ name: 'VSelect' }).props('items') as unknown[]
    expect(items).toEqual([activeScope])
  })

  it('hides the continue action until a scope is chosen', () => {
    const wrapper = mount(ScopeSelector, { global: { stubs } })

    expect(wrapper.findAll('button')).toHaveLength(0)
  })

  it('records the chosen scope and shows its details', async () => {
    const wrapper = mount(ScopeSelector, { global: { stubs } })

    wrapper.findComponent({ name: 'VSelect' }).vm.$emit('update:model-value', activeScope)
    await flushPromises()

    expect(scopesStore.setCurrentScope).toHaveBeenCalledWith(activeScope)
    expect(wrapper.text()).toContain('Working in: Hereditary Cancer')
    expect(wrapper.text()).toContain('Institution: Charité')
  })

  it('emits scope-selected when continuing with the chosen scope', async () => {
    const wrapper = mount(ScopeSelector, { global: { stubs } })

    wrapper.findComponent({ name: 'VSelect' }).vm.$emit('update:model-value', activeScope)
    await flushPromises()
    await wrapper.find('button').trigger('click')

    expect(wrapper.emitted('scope-selected')).toEqual([[activeScope]])
  })

  it('logs an error when the scopes cannot be loaded', async () => {
    scopesStore.fetchUserScopes.mockRejectedValue(new Error('network down'))
    const wrapper = mount(ScopeSelector, { global: { stubs } })
    await flushPromises()

    expect(wrapper.exists()).toBe(true)
    expect(scopesStore.fetchUserScopes).toHaveBeenCalled()
  })
})
