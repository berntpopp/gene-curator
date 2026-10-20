/**
 * useFormTabs Composable
 *
 * Tabbed layout logic for DynamicForm: validates the tab configuration, maps
 * tab scores and per-tab error state, and handles tab navigation.
 *
 * @module components/dynamic/composables/useFormTabs
 */

import { computed, type ComputedRef, type Ref } from 'vue'
import { useLogger } from '@/composables/useLogger'
import type { FormValidationResult, JsonSchemaDocument, TabConfig } from '../types'

/**
 * Extract all field paths from a tab's sections
 */
export function getTabFieldPaths(tab: { sections?: Array<{ fields?: string[] }> }): string[] {
  const paths: string[] = []
  tab.sections?.forEach(section => {
    section.fields?.forEach(fieldPath => {
      paths.push(fieldPath)
    })
  })
  return paths
}

export interface UseFormTabsOptions {
  jsonSchema: ComputedRef<JsonSchemaDocument>
  validationResult: ComputedRef<FormValidationResult | undefined>
  /** Backend errors keyed by dot-notation field path */
  backendErrors: Ref<Record<string, string[]>>
  activeTab: Ref<string | null>
}

/**
 * Tab-related state and actions for a schema-driven form.
 * Falls back to flat rendering (hasTabs false) when the layout is unusable.
 */
export function useFormTabs({
  jsonSchema,
  validationResult,
  backendErrors,
  activeTab
}: UseFormTabsOptions) {
  const logger = useLogger()

  const hasTabs = computed(() => {
    const layout = jsonSchema.value?.ui_configuration?.layout

    if (!layout) {
      logger.debug('No ui_configuration.layout - using flat rendering')
      return false
    }

    if (layout.type !== 'tabs') {
      logger.debug('Layout type not tabs - using flat rendering', { type: layout.type })
      return false
    }

    if (!Array.isArray(layout.tabs) || layout.tabs.length === 0) {
      logger.warn('Invalid tabs configuration - using flat rendering', { layout })
      return false
    }

    return true
  })

  const validTabs = computed<TabConfig[]>(() => {
    if (!hasTabs.value) return []

    const tabs = (jsonSchema.value.ui_configuration?.layout?.tabs ?? []).filter(tab => {
      // Validate tab structure
      if (!tab.id || !tab.name) {
        logger.warn('Tab missing required fields', { tab })
        return false
      }

      if (!Array.isArray(tab.sections) || tab.sections.length === 0) {
        logger.warn('Tab has no sections', { tabId: tab.id })
        return false
      }

      return true
    })

    // If fewer than 2 valid tabs, fallback to flat rendering
    if (tabs.length < 2) {
      logger.warn('Fewer than 2 valid tabs - using flat rendering', { validCount: tabs.length })
      return []
    }

    return tabs
  })

  /**
   * Map tab ID to score calculation field
   * Convention: tab.id maps to score_calculations[tab.id + '_score']
   * Special cases: genetic -> genetic_evidence_score, experimental -> experimental_evidence_score
   */
  function calculateTabScore(tab: TabConfig): number | null {
    const scoreCalcs = validationResult.value?.score_calculations
    if (!scoreCalcs) return null

    // Check for direct mapping with _score suffix
    const scoreKey = `${tab.id}_score`
    if (scoreCalcs[scoreKey] !== undefined) {
      return scoreCalcs[scoreKey]
    }

    // Check for special cases
    const specialMappings: Record<string, string> = {
      genetic: 'genetic_evidence_score',
      experimental: 'experimental_evidence_score',
      clinical: 'clinical_evidence_score'
    }

    const specialKey = specialMappings[tab.id]
    if (specialKey && scoreCalcs[specialKey] !== undefined) {
      return scoreCalcs[specialKey]
    }

    return null
  }

  /**
   * Calculate score for each tab with show_score_badge enabled
   * Maps tab IDs to their corresponding score from validationResult
   */
  const tabScores = computed<Record<string, number | null>>(() => {
    if (!validationResult.value?.score_calculations) return {}

    const scores: Record<string, number | null> = {}
    validTabs.value.forEach(tab => {
      if (tab.show_score_badge) {
        scores[tab.id] = calculateTabScore(tab)
      }
    })

    return scores
  })

  /**
   * Track which tabs have validation errors
   */
  const tabValidationErrors = computed<Record<string, boolean>>(() => {
    const errors: Record<string, boolean> = {}

    validTabs.value.forEach(tab => {
      // Get all field paths in this tab
      const fieldsInTab = getTabFieldPaths(tab)
      const hasErrors = fieldsInTab.some(
        fieldPath => (backendErrors.value[fieldPath]?.length ?? 0) > 0
      )
      errors[tab.id] = hasErrors
    })

    return errors
  })

  /**
   * Determine color for score badge based on value
   * @returns Vuetify color name
   */
  function getScoreColor(score: number | null | undefined): string {
    if (score === null || score === undefined) return 'grey'
    if (score >= 7) return 'success'
    if (score >= 2) return 'warning'
    return 'info'
  }

  /**
   * Navigate to next tab (for mobile swipe gesture)
   */
  function nextTab() {
    const currentIndex = validTabs.value.findIndex(t => t.id === activeTab.value)
    if (currentIndex < validTabs.value.length - 1) {
      activeTab.value = validTabs.value[currentIndex + 1]!.id
    }
  }

  /**
   * Navigate to previous tab (for mobile swipe gesture)
   */
  function prevTab() {
    const currentIndex = validTabs.value.findIndex(t => t.id === activeTab.value)
    if (currentIndex > 0) {
      activeTab.value = validTabs.value[currentIndex - 1]!.id
    }
  }

  /**
   * Find first tab containing validation errors
   */
  const findFirstInvalidTab = (): string | null => {
    for (const tab of validTabs.value) {
      if (tabValidationErrors.value[tab.id]) {
        return tab.id
      }
    }
    return null
  }

  return {
    hasTabs,
    validTabs,
    tabScores,
    tabValidationErrors,
    getScoreColor,
    nextTab,
    prevTab,
    findFirstInvalidTab
  }
}
