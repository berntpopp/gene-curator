import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PublishDialog from '../PublishDialog.vue'
import { useSchemasStore } from '@/stores/schemas'

const { showError, showSuccess } = vi.hoisted(() => ({ showError: vi.fn(), showSuccess: vi.fn() }))
vi.mock('@/composables/useNotifications', () => ({ showError, showSuccess }))

const impact = {
  pairs: [
    { id: 'p1', name: 'KGDB', version: '1.0' },
    { id: 'p2', name: 'Spare', version: '2.0' }
  ],
  scopes: [{ id: 's', name: 'kidney', display_name: 'Kidney', default_workflow_pair_id: 'p1' }],
  latest: { id: 'v1', version: 1 }
}

let store: ReturnType<typeof useSchemasStore>

const mountDialog = async (open = true) => {
  const wrapper = mount(PublishDialog, {
    props: { modelValue: open, schemaId: 'sc', schemaName: 'KGDB curation' },
    attachTo: document.body
  })
  await flushPromises()
  return wrapper
}

const publishButton = () =>
  [...document.body.querySelectorAll('button')].find(b =>
    b.textContent?.includes('Publish version')
  )!

beforeEach(() => {
  vi.clearAllMocks()
  setActivePinia(createPinia())
  store = useSchemasStore()
  vi.spyOn(store, 'validateSchema').mockResolvedValue({
    is_valid: true,
    errors: [],
    warnings: ["UI configuration missing 'sections'"]
  } as never)
  vi.spyOn(store, 'fetchPublishImpact').mockResolvedValue(impact as never)
})
afterEach(() => {
  document.body.innerHTML = ''
})

describe('PublishDialog', () => {
  it('shows the validator report and the pairs and scopes it reaches before publishing', async () => {
    await mountDialog()
    const text = document.body.textContent ?? ''
    expect(text).toContain('Publishes the saved schema as version 2')
    expect(text).toContain('No errors.')
    expect(text).toContain("Warning: UI configuration missing 'sections'")
    expect(text).toContain('KGDB v1.0')
    expect(text).toContain('Default in: Kidney')
    expect(text).toContain('Not a scope default')
    expect(store.validateSchema).toHaveBeenCalledWith('sc')
  })

  it('does not load while closed and says when no pair uses the schema', async () => {
    const wrapper = await mountDialog(false)
    expect(store.validateSchema).not.toHaveBeenCalled()
    vi.mocked(store.fetchPublishImpact).mockResolvedValue({ pairs: [], scopes: [], latest: null })
    await wrapper.setProps({ modelValue: true })
    await flushPromises()
    expect(document.body.textContent).toContain('No workflow pair uses this schema')
    expect(document.body.textContent).toContain('as version 1')
  })

  it('blocks publishing while the validator reports errors', async () => {
    vi.mocked(store.validateSchema).mockResolvedValue({
      is_valid: false,
      errors: ['Missing required field: workflow_states'],
      warnings: []
    } as never)
    await mountDialog()
    expect(document.body.textContent).toContain('Missing required field: workflow_states')
    expect(publishButton().disabled).toBe(true)
  })

  it('publishes and closes', async () => {
    const publish = vi
      .spyOn(store, 'publishVersion')
      .mockResolvedValue({ id: 'v2', version: 2 } as never)
    const wrapper = await mountDialog()
    publishButton().click()
    await flushPromises()
    expect(publish).toHaveBeenCalledWith('sc')
    expect(showSuccess).toHaveBeenCalledWith('Published version 2')
    expect(wrapper.emitted('published')?.[0]).toEqual([{ id: 'v2', version: 2 }])
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })

  it('lists the refusal reasons of a 422 (failed scoring tests) and stays open', async () => {
    vi.spyOn(store, 'publishVersion').mockRejectedValue({
      response: {
        status: 422,
        data: { detail: { message: 'x', errors: ['tests[0]: total 3 != 4'] } }
      }
    })
    const wrapper = await mountDialog()
    publishButton().click()
    await flushPromises()
    expect(document.body.textContent).toContain('tests[0]: total 3 != 4')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
    expect(showError).not.toHaveBeenCalled()
  })

  it('reports other failures', async () => {
    vi.spyOn(store, 'publishVersion').mockRejectedValue({
      response: { data: { detail: 'Not enough permissions' } }
    })
    await mountDialog()
    publishButton().click()
    await flushPromises()
    expect(showError).toHaveBeenCalledWith('Not enough permissions')
  })

  it('closes when the schema cannot be checked', async () => {
    vi.mocked(store.validateSchema).mockRejectedValue(new Error('down'))
    const wrapper = await mountDialog()
    expect(showError).toHaveBeenCalledWith('down')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([false])
  })
})
