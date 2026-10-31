/** MUI-09: override points without a rationale are ignored by scoring, so the form says so. */
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import DynamicNestedField from '../DynamicNestedField.vue'
import { WORKSPACE_FRAME, createWorkspaceFrame } from '@/components/workspace/useWorkspaceFrame'

const schema = {
  type: 'object',
  properties: {
    override_points: { type: 'number', label: 'Override points' },
    override_rationale: { type: 'string', label: 'Override rationale' }
  }
}

function mountAssessment(modelValue: Record<string, unknown>) {
  const frame = createWorkspaceFrame()
  const w = mount(DynamicNestedField, {
    props: {
      fieldName: 'segregation_assessment',
      fieldSchema: schema,
      label: 'Segregation assessment',
      modelValue,
      depth: 0,
      errorMessages: []
    },
    global: { provide: { [WORKSPACE_FRAME as symbol]: frame } }
  })
  return { w, frame }
}

describe('segregation override rationale', () => {
  it('shows an inline error and blocks submit when points have no rationale', () => {
    const { w, frame } = mountAssessment({ override_points: 2, override_rationale: ' ' })
    expect(w.text()).toContain('Add a rationale for the override')
    expect(frame.blockers.value.join()).toContain('add a rationale for the override')
  })

  it('is quiet without an override, or with a rationale', async () => {
    const { w, frame } = mountAssessment({ override_points: null })
    expect(w.text()).not.toContain('Add a rationale')
    await w.setProps({ modelValue: { override_points: 0, override_rationale: 'expert' } })
    expect(w.text()).not.toContain('Add a rationale')
    expect(frame.blockers.value).toEqual([])
  })
})
