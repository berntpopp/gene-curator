/**
 * Tests for useFormTabs (tabbed layout state of DynamicForm).
 *
 * @see src/components/dynamic/composables/useFormTabs.ts
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { computed, ref, type ComputedRef, type Ref } from 'vue'
import { useFormTabs } from '../composables/useFormTabs'
import type { FormValidationResult, JsonSchemaDocument, TabConfig } from '../types'

vi.mock('@/composables/useLogger', () => ({
  useLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() })
}))

function tab(id: string, overrides: Partial<TabConfig> = {}): TabConfig {
  return {
    id,
    name: `Tab ${id}`,
    sections: [{ name: 'Section', fields: [`${id}_field`] }],
    ...overrides
  }
}

function tabSchema(tabs: TabConfig[], type = 'tabs'): JsonSchemaDocument {
  return { ui_configuration: { layout: { type, tabs } } }
}

interface Harness {
  tabs: ReturnType<typeof useFormTabs>
  schema: Ref<JsonSchemaDocument>
  result: Ref<FormValidationResult | undefined>
  backendErrors: Ref<Record<string, string[]>>
  activeTab: Ref<string | null>
  missing: Ref<string[]>
}

function setup(schema: JsonSchemaDocument = {}): Harness {
  const schemaRef = ref<JsonSchemaDocument>(schema)
  const result = ref<FormValidationResult | undefined>(undefined)
  const backendErrors = ref<Record<string, string[]>>({})
  const activeTab = ref<string | null>(null)
  const missing = ref<string[]>([])
  const tabs = useFormTabs({
    missingPaths: computed(() => missing.value),
    jsonSchema: computed(() => schemaRef.value) as ComputedRef<JsonSchemaDocument>,
    validationResult: computed(() => result.value) as ComputedRef<FormValidationResult | undefined>,
    backendErrors,
    activeTab
  })
  return { tabs, schema: schemaRef, result, backendErrors, activeTab, missing }
}

describe('useFormTabs', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('layout detection', () => {
    it('uses flat rendering when there is no layout', () => {
      const { tabs } = setup({})

      expect(tabs.hasTabs.value).toBe(false)
      expect(tabs.validTabs.value).toEqual([])
    })

    it('uses flat rendering for a non-tabs layout', () => {
      const { tabs } = setup(tabSchema([tab('a'), tab('b')], 'flat'))

      expect(tabs.hasTabs.value).toBe(false)
    })

    it('uses flat rendering when the tabs list is empty', () => {
      const { tabs } = setup(tabSchema([]))

      expect(tabs.hasTabs.value).toBe(false)
    })

    it('renders tabs when at least two valid tabs exist', () => {
      const { tabs } = setup(tabSchema([tab('a'), tab('b')]))

      expect(tabs.hasTabs.value).toBe(true)
      expect(tabs.validTabs.value.map(t => t.id)).toEqual(['a', 'b'])
    })

    it('drops tabs without id, name or sections', () => {
      const { tabs } = setup(
        tabSchema([
          tab('a'),
          { id: '', name: 'No id', sections: [{ name: 'S', fields: [] }] },
          { id: 'noname', name: '', sections: [{ name: 'S', fields: [] }] },
          tab('nosections', { sections: [] }),
          tab('c')
        ])
      )

      expect(tabs.validTabs.value.map(t => t.id)).toEqual(['a', 'c'])
    })

    it('falls back to flat rendering when only one valid tab remains', () => {
      const { tabs } = setup(tabSchema([tab('a'), tab('b', { sections: [] })]))

      expect(tabs.validTabs.value).toEqual([])
    })
  })

  describe('scores and error state', () => {
    it('maps score badges through the _score suffix and special cases', () => {
      const { tabs, result } = setup(
        tabSchema([
          tab('genetic', { show_score_badge: true }),
          tab('experimental', { show_score_badge: true }),
          tab('clinical', { show_score_badge: true }),
          tab('plain', { show_score_badge: false })
        ])
      )
      result.value = {
        score_calculations: {
          genetic_evidence_score: 7,
          experimental_evidence_score: 2.5,
          clinical_score: 0
        }
      }

      expect(tabs.tabScores.value).toEqual({ genetic: 7, experimental: 2.5, clinical: 0 })
    })

    it('reports no scores without score calculations', () => {
      const { tabs } = setup(tabSchema([tab('genetic', { show_score_badge: true }), tab('b')]))

      expect(tabs.tabScores.value).toEqual({})
    })

    it('reports null for a badge tab without a matching score', () => {
      const { tabs, result } = setup(
        tabSchema([tab('unknown', { show_score_badge: true }), tab('b')])
      )
      result.value = { score_calculations: { other: 1 } }

      expect(tabs.tabScores.value).toEqual({ unknown: null })
    })

    it('colours scores by value', () => {
      const { tabs } = setup()

      expect(tabs.getScoreColor(null)).toBe('grey')
      expect(tabs.getScoreColor(undefined)).toBe('grey')
      expect(tabs.getScoreColor(8)).toBe('success')
      expect(tabs.getScoreColor(3)).toBe('warning')
      expect(tabs.getScoreColor(1)).toBe('info')
    })

    it('flags tabs whose fields have backend errors', () => {
      const { tabs, backendErrors } = setup(tabSchema([tab('a'), tab('b')]))
      backendErrors.value = { a_field: ['Required'] }

      expect(tabs.tabValidationErrors.value).toEqual({ a: true, b: false })
    })

    it('flags tabs holding an empty required field, nested too (MUI-16)', () => {
      const { tabs, missing } = setup(tabSchema([tab('a'), tab('b'), tab('c')]))
      missing.value = ['b_field', 'c_field.inner']

      expect(tabs.tabValidationErrors.value).toEqual({ a: false, b: true, c: true })
      expect(tabs.findFirstInvalidTab()).toBe('b')
    })
  })

  describe('navigation', () => {
    it('moves to the next and previous tab', () => {
      const { tabs, activeTab } = setup(tabSchema([tab('a'), tab('b'), tab('c')]))
      activeTab.value = 'a'

      tabs.nextTab()
      expect(activeTab.value).toBe('b')

      tabs.prevTab()
      expect(activeTab.value).toBe('a')
    })

    it('stays on the first and last tab at the ends', () => {
      const { tabs, activeTab } = setup(tabSchema([tab('a'), tab('b')]))

      activeTab.value = 'a'
      tabs.prevTab()
      expect(activeTab.value).toBe('a')

      activeTab.value = 'b'
      tabs.nextTab()
      expect(activeTab.value).toBe('b')
    })

    it('finds the first tab that has an error', () => {
      const { tabs, backendErrors } = setup(tabSchema([tab('a'), tab('b'), tab('c')]))

      expect(tabs.findFirstInvalidTab()).toBeNull()

      backendErrors.value = { c_field: ['Bad'], b_field: ['Bad'] }
      expect(tabs.findFirstInvalidTab()).toBe('b')
    })
  })
})
