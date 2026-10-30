import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ScoreTrace from '../ScoreTrace.vue'
import { storedScores } from '@/views/curation/curationScores'
const trace = {
  raw_total: 6,
  total_cap: 5,
  total: 5,
  class: 'custom',
  sections: [
    {
      key: 'custom_section',
      raw: 7,
      cap: 6,
      score: 6,
      categories: [
        {
          key: 'shared_models_and_rescue',
          raw: 9,
          cap: 7,
          score: 7,
          types: [
            { path: 'models.organism', items: 2, score: 6 },
            { path: 'rescue.human', items: 1, score: 3 }
          ]
        },
        { key: 'exact_cap', raw: 2, cap: 2, score: 2, types: [] }
      ]
    }
  ]
}
const render = (t: unknown) =>
  mount(ScoreTrace, {
    props: { scores: storedScores({ total_score: 5, trace: t }), classification: 'Custom verdict' }
  })
describe('ScoreTrace', () => {
  it('renders custom paths, item counts and each backend cap without recomputing', () => {
    const w = render(trace)
    expect(w.text()).toContain('Custom verdict')
    expect(w.text()).toContain('Custom section')
    expect(w.text()).toContain('Shared models and rescue')
    expect(w.text()).toContain('Models › organism')
    const rows = w.findAll('tr').map(r => r.findAll('th,td').map(c => c.text()))
    expect(rows).toContainEqual(['Models › organism', '2', '6.00', '—', '—'])
    expect(rows).toContainEqual(['Shared models and rescue', '—', '9.00', '7.00', '7 · capped'])
    expect(rows).toContainEqual(['Exact cap', '—', '2.00', '2.00', '2'])
    expect(rows).toContainEqual(['Total', '—', '6.00', '5.00', '5 · capped'])
    expect(w.text()).toContain('Classification rule details were not stored')
  })
  it('displays the selected replication band and its description', () => {
    const w = render({
      ...trace,
      classification_rule: {
        class: 'definitive',
        min: 12,
        requires: 'replicated_over_time',
        description: 'Replicated evidence'
      }
    })
    expect(w.text()).toContain('Minimum 12 points')
    expect(w.text()).toContain('Requires Replicated over time')
    expect(w.text()).toContain('Replicated evidence')
  })
  it('says which band a section minimum skipped and lists each capped group', () => {
    const w = render({
      ...trace,
      classification_rule: {
        class: 'limited',
        min: 0.1,
        skipped: [{ class: 'moderate', section: 'genetic', min: 4, score: 2 }]
      },
      capped_groups: [{ path: 'genetic.probands', value: 'c.100A>G', raw: 6, capped: 2 }]
    })
    expect(w.text()).toContain('Skipped Moderate: needs Genetic ≥ 4 points, has 2.00')
    expect(w.get('[data-testid="capped-groups"]').text()).toContain(
      'Genetic › probands · c.100A>G: 6.00 → 2.00 points'
    )
  })
  it('displays the returned override condition without assigning a new verdict', () => {
    const w = render({
      ...trace,
      classification_rule: {
        class: 'disputed',
        when: 'contradictory_evidence',
        field: 'impact',
        in: ['disputed']
      }
    })
    expect(w.text()).toContain('Override: Contradictory evidence · Impact: disputed')
    expect(w.find('.cls-mark').text()).toBe('Custom verdict')
  })
  it('handles old partial traces and null caps as unknown', () => {
    const w = render({ sections: [{ key: 'old', categories: [{ key: 'legacy', types: [{}] }] }] })
    expect(w.text()).toContain('Unavailable')
    expect(w.text()).not.toContain('capped')
  })
})
