import { describe, it, expect, vi, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DiseaseCorrection from '../DiseaseCorrection.vue'
import { useCurationsStore } from '@/stores/curations'
import { useScopesStore } from '@/stores/scopes'
import { curationsAPI } from '@/api/curations'

vi.mock('@/api/curations', () => ({
  curationsAPI: { correctDisease: vi.fn(), getCuration: vi.fn() }
}))

const VDialog = { props: ['modelValue'], template: '<div v-if="modelValue"><slot /></div>' }

function mountAs(role: string, save = vi.fn().mockResolvedValue(true), evidence = {}) {
  const curations = useCurationsStore()
  curations.currentCuration = { id: 'c1', lock_version: 4, evidence_data: evidence } as never
  useScopesStore().currentUserRole = role as never
  return mount(DiseaseCorrection, {
    props: { save },
    global: { stubs: { VDialog } },
    attachTo: document.body
  })
}

async function fill(w: ReturnType<typeof mountAs>, reason: string) {
  await w.get('[data-testid="disease-correction-open"]').trigger('click')
  await flushPromises()
  const [name, mondo] = w.findAll('input[type="text"], input:not([type])')
  await name!.setValue('HNF1B disorder')
  await mondo!.setValue('MONDO:0000001')
  w.findAllComponents({ name: 'VSelect' })[0]!.vm.$emit('update:modelValue', 'AD')
  await w.get('textarea').setValue(reason)
  await w.get('[data-testid="disease-correction-save"]').trigger('click')
  await flushPromises()
}

describe('DiseaseCorrection (#453)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(curationsAPI.correctDisease).mockReset()
    vi.mocked(curationsAPI.getCuration).mockResolvedValue({ id: 'c1', lock_version: 5 } as never)
  })

  it('is offered to scope admins only', () => {
    expect(mountAs('curator').find('[data-testid="disease-correction-open"]').exists()).toBe(false)
    expect(mountAs('admin').find('[data-testid="disease-correction-open"]').exists()).toBe(true)
  })

  it('sends the correction with its reason and lock_version, then reloads', async () => {
    vi.mocked(curationsAPI.correctDisease).mockResolvedValue({} as never)
    const w = mountAs('admin')
    await fill(w, 'legacy import lost it')
    expect(curationsAPI.correctDisease).toHaveBeenCalledWith('c1', {
      disease_name: 'HNF1B disorder',
      mondo_id: 'MONDO:0000001',
      mode_of_inheritance: 'AD',
      relationship_type: null, // the record names none: left as it is
      reason: 'legacy import lost it',
      lock_version: 4
    })
    expect(curationsAPI.getCuration).toHaveBeenCalledWith('c1')
    expect(w.emitted('corrected')).toHaveLength(1)
  })

  it('needs a reason, and shows a refusal', async () => {
    const w = mountAs('admin')
    await fill(w, ' ')
    expect(curationsAPI.correctDisease).not.toHaveBeenCalled()
    vi.mocked(curationsAPI.correctDisease).mockRejectedValue({
      response: { data: { detail: 'Only a draft or sent-back curation can be corrected' } }
    })
    await w.get('textarea').setValue('a reason')
    await w.get('[data-testid="disease-correction-save"]').trigger('click')
    await flushPromises()
    expect(w.text()).toContain('Only a draft or sent-back curation')
    expect(w.emitted('corrected')).toBeUndefined()
  })

  it('saves unsaved edits first and corrects at the saved version; a failed save opens nothing', async () => {
    vi.mocked(curationsAPI.correctDisease).mockResolvedValue({} as never)
    const failing = vi.fn().mockResolvedValue(false)
    const w = mountAs('admin', failing)
    await w.get('[data-testid="disease-correction-open"]').trigger('click')
    await flushPromises()
    expect(failing).toHaveBeenCalled()
    expect(w.find('textarea').exists()).toBe(false)

    const curations = useCurationsStore()
    const saving = vi.fn(async () => {
      curations.currentCuration = { ...curations.currentCuration!, lock_version: 6 }
      return true
    })
    await fill(mountAs('admin', saving), 'after the save')
    expect(saving).toHaveBeenCalledOnce()
    expect(vi.mocked(curationsAPI.correctDisease).mock.calls[0]![1].lock_version).toBe(6)
  })

  it("keeps the record's relationship type unless changed", async () => {
    vi.mocked(curationsAPI.correctDisease).mockResolvedValue({} as never)
    const evidence = { entity_definition: { relationship_type: 'susceptibility' } }
    await fill(mountAs('admin', undefined, evidence), 'keep it')
    expect(vi.mocked(curationsAPI.correctDisease).mock.calls[0]![1].relationship_type).toBe(
      'susceptibility'
    )
  })
})
