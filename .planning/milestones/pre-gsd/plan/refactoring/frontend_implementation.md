# Frontend Implementation - ClinGen SOP v11

**Parent Plan**: `IMPLEMENTATION_PLAN.md`
**Phase**: Phase 3 (Weeks 10-14)
**Owner**: Frontend Developers

---

## Overview

This document specifies all frontend changes for ClinGen SOP v11 implementation, including hand-coded evidence forms, validation composables, gene summary views, and complete component hierarchy.

---

## Architecture Layers

```
┌──────────────────────────────────────────────────────────┐
│                    Views (Pages)                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │ Curation   │  │ Gene       │  │ Evidence   │         │
│  │ Editor     │  │ Summary    │  │ Entry      │         │
│  │ View.vue   │  │ View.vue   │  │ View.vue   │         │
│  └────────────┘  └────────────┘  └────────────┘         │
└──────────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────┐
│              Components (Reusable)                        │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │ ClinGen    │  │ Scope      │  │ Validated  │         │
│  │ Form       │  │ Summary    │  │ Input      │         │
│  │ Components │  │ Card.vue   │  │ .vue       │         │
│  └────────────┘  └────────────┘  └────────────┘         │
└──────────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────┐
│              Composables (Logic)                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │ use        │  │ use        │  │ use        │         │
│  │ Validation │  │ Evidence   │  │ Scoring    │         │
│  └────────────┘  └────────────┘  └────────────┘         │
└──────────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────┐
│              Stores (Pinia)                               │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │ evidence   │  │ gene       │  │ validation │         │
│  │ Store      │  │ Summary    │  │ Store      │         │
│  │            │  │ Store      │  │            │         │
│  └────────────┘  └────────────┘  └────────────┘         │
└──────────────────────────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────┐
│                API Client Layer                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │ evidence   │  │ gene       │  │ validation │         │
│  │ API.ts     │  │ Summary    │  │ API.ts     │         │
│  │            │  │ API.ts     │  │            │         │
│  └────────────┘  └────────────┘  └────────────┘         │
└──────────────────────────────────────────────────────────┘
```

---

## Pinia Stores

### 1. Evidence Store

**File**: `frontend/src/stores/evidence.ts`

```typescript
/**
 * Evidence store for managing evidence items
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { EvidenceItem, EvidenceItemCreate, EvidenceItemUpdate } from '@/types/evidence'
import * as evidenceAPI from '@/api/evidence'
import { logService } from '@/services/logService'

export const useEvidenceStore = defineStore('evidence', () => {
  // State
  const evidence = ref<Map<string, EvidenceItem>>(new Map())
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const getEvidenceByCuration = computed(() => {
    return (curationId: string) => {
      return Array.from(evidence.value.values())
        .filter(item => item.curation_id === curationId)
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    }
  })

  const getEvidenceByCategory = computed(() => {
    return (curationId: string, category: string) => {
      return getEvidenceByCuration.value(curationId)
        .filter(item => item.evidence_category === category)
    }
  })

  const geneticEvidenceCount = computed(() => {
    return (curationId: string) => {
      return getEvidenceByCuration.value(curationId)
        .filter(item => item.evidence_type === 'genetic').length
    }
  })

  const experimentalEvidenceCount = computed(() => {
    return (curationId: string) => {
      return getEvidenceByCuration.value(curationId)
        .filter(item => item.evidence_type === 'experimental').length
    }
  })

  // Actions
  async function fetchEvidenceForCuration(curationId: string): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const items = await evidenceAPI.getEvidenceItems(curationId)
      items.forEach(item => evidence.value.set(item.id, item))
      logService.info('Evidence items fetched', { curationId, count: items.length })
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch evidence'
      logService.error('Failed to fetch evidence', { curationId, error: e })
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createEvidence(
    curationId: string,
    data: EvidenceItemCreate
  ): Promise<EvidenceItem> {
    loading.value = true
    error.value = null

    try {
      const created = await evidenceAPI.createEvidenceItem(curationId, data)
      evidence.value.set(created.id, created)
      logService.info('Evidence item created', { curationId, itemId: created.id })
      return created
    } catch (e: any) {
      error.value = e.message || 'Failed to create evidence'
      logService.error('Failed to create evidence', { curationId, error: e })
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateEvidence(
    curationId: string,
    itemId: string,
    data: EvidenceItemUpdate
  ): Promise<EvidenceItem> {
    loading.value = true
    error.value = null

    try {
      const updated = await evidenceAPI.updateEvidenceItem(curationId, itemId, data)
      evidence.value.set(updated.id, updated)
      logService.info('Evidence item updated', { curationId, itemId })
      return updated
    } catch (e: any) {
      error.value = e.message || 'Failed to update evidence'
      logService.error('Failed to update evidence', { curationId, itemId, error: e })
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteEvidence(curationId: string, itemId: string): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await evidenceAPI.deleteEvidenceItem(curationId, itemId)
      evidence.value.delete(itemId)
      logService.info('Evidence item deleted', { curationId, itemId })
    } catch (e: any) {
      error.value = e.message || 'Failed to delete evidence'
      logService.error('Failed to delete evidence', { curationId, itemId, error: e })
      throw e
    } finally {
      loading.value = false
    }
  }

  function clearEvidence(): void {
    evidence.value.clear()
    error.value = null
  }

  return {
    // State
    evidence,
    loading,
    error,

    // Getters
    getEvidenceByCuration,
    getEvidenceByCategory,
    geneticEvidenceCount,
    experimentalEvidenceCount,

    // Actions
    fetchEvidenceForCuration,
    createEvidence,
    updateEvidence,
    deleteEvidence,
    clearEvidence,
  }
})
```

---

### 2. Gene Summary Store

**File**: `frontend/src/stores/geneSummary.ts`

```typescript
/**
 * Gene summary store for cross-scope aggregation
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { GeneSummaryPublic, GeneSummaryFull } from '@/types/geneSummary'
import * as geneSummaryAPI from '@/api/geneSummary'
import { logService } from '@/services/logService'

export const useGeneSummaryStore = defineStore('geneSummary', () => {
  // State
  const publicSummaries = ref<Map<string, GeneSummaryPublic>>(new Map())
  const fullSummaries = ref<Map<string, GeneSummaryFull>>(new Map())
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Actions
  async function fetchPublicSummary(geneId: string): Promise<GeneSummaryPublic | null> {
    loading.value = true
    error.value = null

    try {
      const summary = await geneSummaryAPI.getPublicSummary(geneId)
      if (summary) {
        publicSummaries.value.set(geneId, summary)
      }
      logService.info('Public gene summary fetched', { geneId })
      return summary
    } catch (e: any) {
      if (e.response?.status === 404) {
        logService.info('No public curations for gene', { geneId })
        return null
      }
      error.value = e.message || 'Failed to fetch gene summary'
      logService.error('Failed to fetch public summary', { geneId, error: e })
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchFullSummary(geneId: string): Promise<GeneSummaryFull> {
    loading.value = true
    error.value = null

    try {
      const summary = await geneSummaryAPI.getFullSummary(geneId)
      fullSummaries.value.set(geneId, summary)
      logService.info('Full gene summary fetched', { geneId })
      return summary
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch full summary'
      logService.error('Failed to fetch full summary', { geneId, error: e })
      throw e
    } finally {
      loading.value = false
    }
  }

  async function recomputeSummary(geneId: string): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await geneSummaryAPI.recomputeSummary(geneId)
      // Invalidate cached summaries
      publicSummaries.value.delete(geneId)
      fullSummaries.value.delete(geneId)
      logService.info('Gene summary recomputed', { geneId })
    } catch (e: any) {
      error.value = e.message || 'Failed to recompute summary'
      logService.error('Failed to recompute summary', { geneId, error: e })
      throw e
    } finally {
      loading.value = false
    }
  }

  function clearSummaries(): void {
    publicSummaries.value.clear()
    fullSummaries.value.clear()
    error.value = null
  }

  return {
    // State
    publicSummaries,
    fullSummaries,
    loading,
    error,

    // Actions
    fetchPublicSummary,
    fetchFullSummary,
    recomputeSummary,
    clearSummaries,
  }
})
```

---

### 3. Validation Store

**File**: `frontend/src/stores/validation.ts`

```typescript
/**
 * Validation store for external validator integration
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ValidationResult } from '@/types/validation'
import * as validationAPI from '@/api/validation'
import { logService } from '@/services/logService'

export const useValidationStore = defineStore('validation', () => {
  // State
  const cache = ref<Map<string, ValidationResult>>(new Map())
  const loading = ref<Map<string, boolean>>(new Map())
  const error = ref<string | null>(null)

  // Helpers
  function getCacheKey(validator: string, value: string): string {
    return `${validator}:${value.toLowerCase().trim()}`
  }

  // Actions
  async function validateHGNC(geneSymbol: string, skipCache = false): Promise<ValidationResult> {
    const cacheKey = getCacheKey('hgnc', geneSymbol)

    // Check cache
    if (!skipCache && cache.value.has(cacheKey)) {
      logService.info('Validation cache hit', { validator: 'hgnc', value: geneSymbol })
      return cache.value.get(cacheKey)!
    }

    loading.value.set(cacheKey, true)
    error.value = null

    try {
      const result = await validationAPI.validateHGNC(geneSymbol, skipCache)
      cache.value.set(cacheKey, result)
      logService.info('HGNC validation complete', {
        geneSymbol,
        isValid: result.is_valid,
      })
      return result
    } catch (e: any) {
      error.value = e.message || 'Validation failed'
      logService.error('HGNC validation failed', { geneSymbol, error: e })
      throw e
    } finally {
      loading.value.delete(cacheKey)
    }
  }

  async function validatePubMed(pmid: string, skipCache = false): Promise<ValidationResult> {
    const cacheKey = getCacheKey('pubmed', pmid)

    if (!skipCache && cache.value.has(cacheKey)) {
      logService.info('Validation cache hit', { validator: 'pubmed', value: pmid })
      return cache.value.get(cacheKey)!
    }

    loading.value.set(cacheKey, true)
    error.value = null

    try {
      const result = await validationAPI.validatePubMed(pmid, skipCache)
      cache.value.set(cacheKey, result)
      logService.info('PubMed validation complete', {
        pmid,
        isValid: result.is_valid,
      })
      return result
    } catch (e: any) {
      error.value = e.message || 'Validation failed'
      logService.error('PubMed validation failed', { pmid, error: e })
      throw e
    } finally {
      loading.value.delete(cacheKey)
    }
  }

  async function validateHPO(hpoTerm: string, skipCache = false): Promise<ValidationResult> {
    const cacheKey = getCacheKey('hpo', hpoTerm)

    if (!skipCache && cache.value.has(cacheKey)) {
      logService.info('Validation cache hit', { validator: 'hpo', value: hpoTerm })
      return cache.value.get(cacheKey)!
    }

    loading.value.set(cacheKey, true)
    error.value = null

    try {
      const result = await validationAPI.validateHPO(hpoTerm, skipCache)
      cache.value.set(cacheKey, result)
      logService.info('HPO validation complete', {
        hpoTerm,
        isValid: result.is_valid,
      })
      return result
    } catch (e: any) {
      error.value = e.message || 'Validation failed'
      logService.error('HPO validation failed', { hpoTerm, error: e })
      throw e
    } finally {
      loading.value.delete(cacheKey)
    }
  }

  async function validateBatch(
    validator: string,
    values: string[]
  ): Promise<Record<string, ValidationResult>> {
    error.value = null

    try {
      const results = await validationAPI.validateBatch(validator, values)
      // Cache all results
      Object.entries(results).forEach(([value, result]) => {
        const cacheKey = getCacheKey(validator, value)
        cache.value.set(cacheKey, result)
      })
      logService.info('Batch validation complete', { validator, count: values.length })
      return results
    } catch (e: any) {
      error.value = e.message || 'Batch validation failed'
      logService.error('Batch validation failed', { validator, error: e })
      throw e
    }
  }

  function isValidating(validator: string, value: string): boolean {
    const cacheKey = getCacheKey(validator, value)
    return loading.value.get(cacheKey) || false
  }

  function clearCache(): void {
    cache.value.clear()
    loading.value.clear()
    error.value = null
  }

  return {
    // State
    cache,
    loading,
    error,

    // Actions
    validateHGNC,
    validatePubMed,
    validateHPO,
    validateBatch,
    isValidating,
    clearCache,
  }
})
```

---

## Composables

### 1. useValidation

**File**: `frontend/src/composables/useValidation.ts`

```typescript
/**
 * Composable for field validation with external validators
 */

import { ref, watch } from 'vue'
import { useValidationStore } from '@/stores/validation'
import { debounce } from 'lodash-es'
import type { ValidationResult } from '@/types/validation'

export function useValidation(validator: 'hgnc' | 'pubmed' | 'hpo') {
  const validationStore = useValidationStore()

  const value = ref('')
  const result = ref<ValidationResult | null>(null)
  const isValidating = ref(false)
  const error = ref<string | null>(null)

  // Debounced validation
  const validateDebounced = debounce(async (val: string) => {
    if (!val || val.length < 2) {
      result.value = null
      return
    }

    isValidating.value = true
    error.value = null

    try {
      let validationResult: ValidationResult

      if (validator === 'hgnc') {
        validationResult = await validationStore.validateHGNC(val)
      } else if (validator === 'pubmed') {
        validationResult = await validationStore.validatePubMed(val)
      } else {
        validationResult = await validationStore.validateHPO(val)
      }

      result.value = validationResult
    } catch (e: any) {
      error.value = e.message || 'Validation failed'
    } finally {
      isValidating.value = false
    }
  }, 500)

  // Watch value changes
  watch(value, (newVal) => {
    validateDebounced(newVal)
  })

  // Manual validation
  async function validate(val?: string): Promise<ValidationResult | null> {
    const valueToValidate = val || value.value

    if (!valueToValidate) {
      result.value = null
      return null
    }

    isValidating.value = true
    error.value = null

    try {
      let validationResult: ValidationResult

      if (validator === 'hgnc') {
        validationResult = await validationStore.validateHGNC(valueToValidate)
      } else if (validator === 'pubmed') {
        validationResult = await validationStore.validatePubMed(valueToValidate)
      } else {
        validationResult = await validationStore.validateHPO(valueToValidate)
      }

      result.value = validationResult
      return validationResult
    } catch (e: any) {
      error.value = e.message || 'Validation failed'
      return null
    } finally {
      isValidating.value = false
    }
  }

  function reset(): void {
    value.value = ''
    result.value = null
    error.value = null
    isValidating.value = false
  }

  return {
    value,
    result,
    isValidating,
    error,
    validate,
    reset,
  }
}
```

---

### 2. useEvidence

**File**: `frontend/src/composables/useEvidence.ts`

```typescript
/**
 * Composable for evidence management
 */

import { computed, ref } from 'vue'
import { useEvidenceStore } from '@/stores/evidence'
import type { EvidenceItemCreate, EvidenceItemUpdate } from '@/types/evidence'

export function useEvidence(curationId: string) {
  const evidenceStore = useEvidenceStore()

  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const evidenceItems = computed(() => {
    return evidenceStore.getEvidenceByCuration(curationId)
  })

  const geneticEvidence = computed(() => {
    return evidenceItems.value.filter(item => item.evidence_type === 'genetic')
  })

  const experimentalEvidence = computed(() => {
    return evidenceItems.value.filter(item => item.evidence_type === 'experimental')
  })

  const totalScore = computed(() => {
    return evidenceItems.value.reduce((sum, item) => {
      return sum + (item.computed_score || 0)
    }, 0)
  })

  // Actions
  async function fetchEvidence(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.fetchEvidenceForCuration(curationId)
    } catch (e: any) {
      error.value = e.message || 'Failed to fetch evidence'
    } finally {
      loading.value = false
    }
  }

  async function addEvidence(data: EvidenceItemCreate): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.createEvidence(curationId, data)
    } catch (e: any) {
      error.value = e.message || 'Failed to add evidence'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateEvidence(itemId: string, data: EvidenceItemUpdate): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.updateEvidence(curationId, itemId, data)
    } catch (e: any) {
      error.value = e.message || 'Failed to update evidence'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function removeEvidence(itemId: string): Promise<void> {
    loading.value = true
    error.value = null

    try {
      await evidenceStore.deleteEvidence(curationId, itemId)
    } catch (e: any) {
      error.value = e.message || 'Failed to delete evidence'
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    loading,
    error,

    // Computed
    evidenceItems,
    geneticEvidence,
    experimentalEvidence,
    totalScore,

    // Actions
    fetchEvidence,
    addEvidence,
    updateEvidence,
    removeEvidence,
  }
}
```

---

### 3. useScoring

**File**: `frontend/src/composables/useScoring.ts`

```typescript
/**
 * Composable for ClinGen scoring calculations
 */

import { computed, type ComputedRef } from 'vue'
import type { EvidenceItem } from '@/types/evidence'

interface ScoringBreakdown {
  genetic_total: number
  experimental_total: number
  total_score: number
  classification: string
  case_level_score: number
  segregation_score: number
  case_control_score: number
  expression_score: number
  function_score: number
  models_score: number
  rescue_score: number
}

export function useScoring(evidenceItems: ComputedRef<EvidenceItem[]>) {
  const breakdown = computed<ScoringBreakdown>(() => {
    const genetic = evidenceItems.value.filter(e => e.evidence_type === 'genetic')
    const experimental = evidenceItems.value.filter(e => e.evidence_type === 'experimental')

    // Genetic scores by category
    const case_level_score = genetic
      .filter(e => e.evidence_category === 'case_level')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const segregation_score = genetic
      .filter(e => e.evidence_category === 'segregation')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const case_control_score = genetic
      .filter(e => e.evidence_category === 'case_control')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const genetic_total = Math.min(
      case_level_score + segregation_score + case_control_score,
      12.0
    )

    // Experimental scores by category
    const expression_score = experimental
      .filter(e => e.evidence_category === 'expression')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const function_score = experimental
      .filter(e => e.evidence_category === 'protein_function')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const models_score = experimental
      .filter(e => e.evidence_category === 'models')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const rescue_score = experimental
      .filter(e => e.evidence_category === 'rescue')
      .reduce((sum, e) => sum + (e.computed_score || 0), 0)

    const experimental_total = Math.min(
      expression_score + function_score + models_score + rescue_score,
      6.0
    )

    const total_score = genetic_total + experimental_total

    // Classification
    let classification = 'No Known Disease Relationship'
    if (total_score >= 12) classification = 'Definitive'
    else if (total_score >= 7) classification = 'Strong'
    else if (total_score >= 2) classification = 'Moderate'
    else if (total_score >= 0.1) classification = 'Limited'

    return {
      genetic_total,
      experimental_total,
      total_score,
      classification,
      case_level_score: Math.min(case_level_score, 12),
      segregation_score: Math.min(segregation_score, 7),
      case_control_score: Math.min(case_control_score, 6),
      expression_score: Math.min(expression_score, 2),
      function_score: Math.min(function_score, 2),
      models_score: Math.min(models_score, 4),
      rescue_score: Math.min(rescue_score, 2),
    }
  })

  const classificationColor = computed(() => {
    const cls = breakdown.value.classification
    if (cls === 'Definitive') return 'success'
    if (cls === 'Strong') return 'info'
    if (cls === 'Moderate') return 'warning'
    if (cls === 'Limited') return 'grey'
    return 'error'
  })

  return {
    breakdown,
    classificationColor,
  }
}
```

---

## Components

### 1. ValidatedInput.vue

**File**: `frontend/src/components/ValidatedInput.vue`

```vue
<template>
  <v-text-field
    v-model="internalValue"
    :label="label"
    :hint="hint"
    :loading="isValidating"
    :error-messages="errorMessages"
    :success-messages="successMessages"
    :prepend-inner-icon="statusIcon"
    :color="statusColor"
    @blur="handleBlur"
  >
    <template #append-inner>
      <v-tooltip v-if="result && result.data" location="top">
        <template #activator="{ props }">
          <v-icon v-bind="props" size="small">mdi-information</v-icon>
        </template>
        <div class="text-caption">
          <div v-if="validator === 'hgnc'">
            <strong>{{ result.data.approved_symbol }}</strong>
            <div>{{ result.data.hgnc_id }}</div>
            <div v-if="result.data.locus_type">Type: {{ result.data.locus_type }}</div>
          </div>
          <div v-else-if="validator === 'pubmed'">
            <strong>{{ result.data.title }}</strong>
            <div>{{ result.data.journal }} ({{ result.data.pub_date }})</div>
          </div>
          <div v-else-if="validator === 'hpo'">
            <strong>{{ result.data.term_name }}</strong>
            <div class="text-caption">{{ result.data.definition }}</div>
          </div>
        </div>
      </v-tooltip>
    </template>

    <template v-if="result && result.suggestions" #append>
      <v-menu>
        <template #activator="{ props }">
          <v-btn
            v-bind="props"
            variant="text"
            size="small"
            color="warning"
          >
            Suggestions
          </v-btn>
        </template>
        <v-list>
          <v-list-item
            v-for="suggestion in result.suggestions.did_you_mean"
            :key="suggestion"
            @click="internalValue = suggestion"
          >
            <v-list-item-title>{{ suggestion }}</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </template>
  </v-text-field>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useValidation } from '@/composables/useValidation'

interface Props {
  modelValue: string
  validator: 'hgnc' | 'pubmed' | 'hpo'
  label: string
  hint?: string
  required?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  hint: '',
  required: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void
}>()

const {
  value: internalValue,
  result,
  isValidating,
  error,
  validate,
} = useValidation(props.validator)

// Sync with v-model
internalValue.value = props.modelValue

// Emit changes
const handleBlur = () => {
  emit('update:modelValue', internalValue.value)
}

// Status
const statusIcon = computed(() => {
  if (isValidating.value) return 'mdi-loading mdi-spin'
  if (result.value?.is_valid) return 'mdi-check-circle'
  if (result.value && !result.value.is_valid) return 'mdi-alert-circle'
  return ''
})

const statusColor = computed(() => {
  if (result.value?.is_valid) return 'success'
  if (result.value && !result.value.is_valid) return 'error'
  return ''
})

const errorMessages = computed(() => {
  if (error.value) return [error.value]
  if (result.value && !result.value.is_valid && result.value.error_message) {
    return [result.value.error_message]
  }
  return []
})

const successMessages = computed(() => {
  if (result.value?.is_valid && result.value.data) {
    if (props.validator === 'hgnc') {
      return [`✓ Approved symbol: ${result.value.data.approved_symbol}`]
    } else if (props.validator === 'pubmed') {
      return [`✓ Valid PMID`]
    } else if (props.validator === 'hpo') {
      return [`✓ ${result.value.data.term_name}`]
    }
  }
  return []
})
</script>
```

---

### 2. ClinGenGeneticEvidenceForm.vue (Hand-Coded)

**File**: `frontend/src/components/clingen/ClinGenGeneticEvidenceForm.vue`

```vue
<template>
  <v-card>
    <v-card-title>
      <span class="text-h6">Add Genetic Evidence</span>
    </v-card-title>

    <v-card-text>
      <v-form ref="formRef" @submit.prevent="handleSubmit">
        <!-- Evidence Category -->
        <v-select
          v-model="form.evidence_category"
          :items="evidenceCategories"
          label="Evidence Category *"
          :rules="[rules.required]"
          @update:model-value="resetConditionalFields"
        />

        <!-- Inheritance Pattern (always shown) -->
        <v-select
          v-model="form.inheritance_pattern"
          :items="inheritancePatterns"
          label="Inheritance Pattern *"
          :rules="[rules.required]"
        />

        <!-- Case-Level Fields -->
        <template v-if="form.evidence_category === 'case_level'">
          <v-select
            v-model="form.variant_type"
            :items="variantTypes"
            label="Variant Type *"
            :rules="[rules.required]"
          />

          <v-text-field
            v-model.number="form.proband_count"
            type="number"
            label="Proband Count *"
            :rules="[rules.required, rules.min(1)]"
            hint="Number of probands with this variant"
          />

          <v-checkbox
            v-model="form.de_novo"
            label="De Novo Variant"
            hint="Variant confirmed as de novo"
          />

          <v-checkbox
            v-model="form.functional_alteration"
            label="Functional Alteration Demonstrated"
            hint="Functional studies confirm pathogenic effect"
          />
        </template>

        <!-- Segregation Fields -->
        <template v-if="form.evidence_category === 'segregation'">
          <v-text-field
            v-model.number="form.family_count"
            type="number"
            label="Family Count"
            :rules="[rules.min(1)]"
            hint="Number of families with segregation data"
          />

          <v-text-field
            v-model.number="form.lod_score"
            type="number"
            step="0.1"
            label="LOD Score"
            hint="Logarithm of odds score (if calculated)"
          />

          <v-alert v-if="form.family_count && !form.lod_score" type="info" density="compact">
            LOD score will be calculated automatically based on family count and inheritance
          </v-alert>
        </template>

        <!-- Case-Control Fields -->
        <template v-if="form.evidence_category === 'case_control'">
          <v-text-field
            v-model.number="form.case_count"
            type="number"
            label="Case Count *"
            :rules="[rules.required, rules.min(1)]"
          />

          <v-text-field
            v-model.number="form.control_count"
            type="number"
            label="Control Count *"
            :rules="[rules.required, rules.min(1)]"
          />

          <v-text-field
            v-model.number="form.p_value"
            type="number"
            step="0.0001"
            label="P-Value"
            hint="Statistical significance"
          />
        </template>

        <!-- PMIDs (always shown) -->
        <v-combobox
          v-model="form.pmids"
          label="PubMed IDs (PMIDs) *"
          multiple
          chips
          closable-chips
          :rules="[rules.required, rules.minLength(1)]"
          hint="Enter PMIDs and press Enter. Format: 12345678"
        >
          <template #chip="{ item, props }">
            <v-chip v-bind="props" color="primary">
              {{ item.value }}
            </v-chip>
          </template>
        </v-combobox>

        <!-- Validate PMIDs Button -->
        <v-btn
          v-if="form.pmids.length > 0"
          variant="outlined"
          size="small"
          :loading="validatingPmids"
          @click="validateAllPmids"
        >
          Validate PMIDs
        </v-btn>

        <v-alert
          v-if="pmidValidationErrors.length > 0"
          type="warning"
          density="compact"
          class="mt-2"
        >
          Invalid PMIDs: {{ pmidValidationErrors.join(', ') }}
        </v-alert>

        <!-- Notes -->
        <v-textarea
          v-model="form.notes"
          label="Notes"
          rows="3"
          hint="Additional details about this evidence"
        />

        <!-- Computed Score Preview -->
        <v-card v-if="computedScore !== null" variant="tonal" color="info" class="mt-4">
          <v-card-text>
            <div class="text-subtitle-2">Estimated Score</div>
            <div class="text-h4">{{ computedScore.toFixed(2) }} points</div>
            <div class="text-caption">Final score calculated by backend</div>
          </v-card-text>
        </v-card>
      </v-form>
    </v-card-text>

    <v-card-actions>
      <v-spacer />
      <v-btn @click="handleCancel">Cancel</v-btn>
      <v-btn
        color="primary"
        :loading="loading"
        :disabled="!formValid"
        @click="handleSubmit"
      >
        Add Evidence
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useValidationStore } from '@/stores/validation'
import type { EvidenceItemCreate } from '@/types/evidence'

interface Props {
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
})

const emit = defineEmits<{
  (e: 'submit', data: EvidenceItemCreate): void
  (e: 'cancel'): void
}>()

const validationStore = useValidationStore()

// Form ref
const formRef = ref()
const formValid = ref(false)

// Form data
const form = ref({
  evidence_category: '',
  inheritance_pattern: '',
  variant_type: '',
  proband_count: null as number | null,
  de_novo: false,
  functional_alteration: false,
  family_count: null as number | null,
  lod_score: null as number | null,
  case_count: null as number | null,
  control_count: null as number | null,
  p_value: null as number | null,
  pmids: [] as string[],
  notes: '',
})

// Options
const evidenceCategories = [
  { title: 'Case-Level Evidence', value: 'case_level' },
  { title: 'Segregation Evidence', value: 'segregation' },
  { title: 'Case-Control Evidence', value: 'case_control' },
]

const variantTypes = [
  { title: 'Predicted Null (LOF)', value: 'predicted_null' },
  { title: 'Missense', value: 'missense' },
  { title: 'Other Variant Type', value: 'other_variant_type' },
]

const inheritancePatterns = [
  { title: 'Autosomal Dominant', value: 'autosomal_dominant' },
  { title: 'Autosomal Recessive', value: 'autosomal_recessive' },
  { title: 'X-Linked', value: 'x_linked' },
]

// Validation rules
const rules = {
  required: (v: any) => !!v || 'This field is required',
  min: (min: number) => (v: any) => v >= min || `Must be at least ${min}`,
  minLength: (min: number) => (v: any) => v.length >= min || `Must have at least ${min} items`,
}

// PMID validation
const validatingPmids = ref(false)
const pmidValidationErrors = ref<string[]>([])

async function validateAllPmids() {
  validatingPmids.value = true
  pmidValidationErrors.value = []

  try {
    const results = await validationStore.validateBatch('pubmed', form.value.pmids)

    Object.entries(results).forEach(([pmid, result]) => {
      if (!result.is_valid) {
        pmidValidationErrors.value.push(pmid)
      }
    })
  } finally {
    validatingPmids.value = false
  }
}

// Computed score (client-side estimate)
const computedScore = computed(() => {
  const category = form.value.evidence_category
  const variantType = form.value.variant_type
  const probandCount = form.value.proband_count || 0
  const deNovo = form.value.de_novo
  const functional = form.value.functional_alteration

  if (category === 'case_level' && probandCount > 0) {
    let base = 0
    if (variantType === 'predicted_null') base = 1.5
    else if (variantType === 'missense') base = 0.1
    else base = 0.5

    let score = base * probandCount

    if (deNovo) {
      if (variantType === 'predicted_null') score += 0.5 * probandCount
      else if (variantType === 'missense') score += 0.4 * probandCount
    }

    if (functional) {
      score += 0.4 * probandCount
    }

    return Math.min(score, 12)
  }

  return null
})

// Reset conditional fields when category changes
function resetConditionalFields() {
  form.value.variant_type = ''
  form.value.proband_count = null
  form.value.de_novo = false
  form.value.functional_alteration = false
  form.value.family_count = null
  form.value.lod_score = null
  form.value.case_count = null
  form.value.control_count = null
  form.value.p_value = null
}

// Handlers
async function handleSubmit() {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  const evidenceData: Record<string, any> = {
    evidence_category: form.value.evidence_category,
    inheritance_pattern: form.value.inheritance_pattern,
    pmids: form.value.pmids,
    notes: form.value.notes,
  }

  // Add category-specific fields
  if (form.value.evidence_category === 'case_level') {
    evidenceData.variant_type = form.value.variant_type
    evidenceData.proband_count = form.value.proband_count
    evidenceData.de_novo = form.value.de_novo
    evidenceData.functional_alteration = form.value.functional_alteration
  } else if (form.value.evidence_category === 'segregation') {
    if (form.value.family_count) evidenceData.family_count = form.value.family_count
    if (form.value.lod_score) evidenceData.lod_score = form.value.lod_score
  } else if (form.value.evidence_category === 'case_control') {
    evidenceData.case_count = form.value.case_count
    evidenceData.control_count = form.value.control_count
    if (form.value.p_value) evidenceData.p_value = form.value.p_value
  }

  const payload: EvidenceItemCreate = {
    evidence_category: form.value.evidence_category,
    evidence_type: 'genetic',
    evidence_data: evidenceData,
  }

  emit('submit', payload)
}

function handleCancel() {
  emit('cancel')
}
</script>
```

---

### 3. GeneSummaryView.vue

**File**: `frontend/src/views/GeneSummaryView.vue`

```vue
<template>
  <v-container>
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <v-icon left>mdi-dna</v-icon>
            Gene Summary: {{ geneSymbol }}
          </v-card-title>

          <v-card-text>
            <!-- Loading -->
            <v-progress-linear v-if="loading" indeterminate />

            <!-- Error -->
            <v-alert v-else-if="error" type="error">
              {{ error }}
            </v-alert>

            <!-- No data -->
            <v-alert v-else-if="!summary" type="info">
              No curations found for this gene
            </v-alert>

            <!-- Summary -->
            <div v-else>
              <!-- Overview -->
              <v-row>
                <v-col cols="12" md="4">
                  <v-card variant="tonal">
                    <v-card-text>
                      <div class="text-caption">Scopes Curating</div>
                      <div class="text-h4">{{ summary.public_scopes_count }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>

                <v-col cols="12" md="4">
                  <v-card variant="tonal" :color="consensusColor">
                    <v-card-text>
                      <div class="text-caption">Consensus Classification</div>
                      <div class="text-h6">{{ summary.consensus_classification || 'N/A' }}</div>
                    </v-card-text>
                  </v-card>
                </v-col>

                <v-col cols="12" md="4">
                  <v-card variant="tonal" :color="summary.has_conflicts ? 'warning' : 'success'">
                    <v-card-text>
                      <div class="text-caption">Agreement</div>
                      <div class="text-h6">
                        {{ summary.has_conflicts ? 'Conflicting' : 'Consensus' }}
                      </div>
                    </v-card-text>
                  </v-card>
                </v-col>
              </v-row>

              <!-- Conflicts Alert -->
              <v-alert
                v-if="summary.has_conflicts"
                type="warning"
                variant="tonal"
                class="mt-4"
              >
                <v-alert-title>Conflicting Classifications</v-alert-title>
                Multiple scopes have assigned different classifications to this gene.
                Review individual scope curations below.
              </v-alert>

              <!-- Classification Distribution -->
              <v-card class="mt-4">
                <v-card-title>Classification Distribution</v-card-title>
                <v-card-text>
                  <v-chip-group>
                    <v-chip
                      v-for="(count, classification) in summary.classification_summary"
                      :key="classification"
                      :color="getClassificationColor(classification as string)"
                      label
                    >
                      {{ classification }}: {{ count }}
                    </v-chip>
                  </v-chip-group>
                </v-card-text>
              </v-card>

              <!-- Per-Scope Summaries -->
              <v-row class="mt-4">
                <v-col
                  v-for="scope in summary.scope_summaries"
                  :key="scope.scope_id"
                  cols="12"
                  md="6"
                >
                  <scope-summary-card :scope-summary="scope" />
                </v-col>
              </v-row>

              <!-- Last Updated -->
              <div class="text-caption text-grey mt-4">
                Last updated: {{ formatDate(summary.last_updated) }}
              </div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useGeneSummaryStore } from '@/stores/geneSummary'
import ScopeSummaryCard from '@/components/ScopeSummaryCard.vue'
import { formatDate } from '@/utils/dates'

const route = useRoute()
const geneSummaryStore = useGeneSummaryStore()

const geneId = route.params.geneId as string
const geneSymbol = ref('')
const loading = ref(false)
const error = ref<string | null>(null)

const summary = computed(() => {
  return geneSummaryStore.publicSummaries.get(geneId) || null
})

const consensusColor = computed(() => {
  const cls = summary.value?.consensus_classification
  if (cls === 'definitive') return 'success'
  if (cls === 'strong') return 'info'
  if (cls === 'moderate') return 'warning'
  return 'grey'
})

function getClassificationColor(classification: string): string {
  if (classification === 'definitive') return 'success'
  if (classification === 'strong') return 'info'
  if (classification === 'moderate') return 'warning'
  if (classification === 'limited') return 'grey'
  return 'error'
}

onMounted(async () => {
  loading.value = true
  try {
    await geneSummaryStore.fetchPublicSummary(geneId)
    // TODO: Fetch gene symbol from genes store
    geneSymbol.value = 'BRCA1' // Placeholder
  } catch (e: any) {
    error.value = e.message || 'Failed to load gene summary'
  } finally {
    loading.value = false
  }
})
</script>
```

---

## API Client Layer

**File**: `frontend/src/api/evidence.ts`

```typescript
import api from './client'
import type { EvidenceItem, EvidenceItemCreate, EvidenceItemUpdate } from '@/types/evidence'

export async function getEvidenceItems(curationId: string): Promise<EvidenceItem[]> {
  const response = await api.get(`/curations/${curationId}/evidence`)
  return response.data
}

export async function createEvidenceItem(
  curationId: string,
  data: EvidenceItemCreate
): Promise<EvidenceItem> {
  const response = await api.post(`/curations/${curationId}/evidence`, data)
  return response.data
}

export async function updateEvidenceItem(
  curationId: string,
  itemId: string,
  data: EvidenceItemUpdate
): Promise<EvidenceItem> {
  const response = await api.put(`/curations/${curationId}/evidence/${itemId}`, data)
  return response.data
}

export async function deleteEvidenceItem(
  curationId: string,
  itemId: string
): Promise<void> {
  await api.delete(`/curations/${curationId}/evidence/${itemId}`)
}
```

**File**: `frontend/src/api/geneSummary.ts`

```typescript
import api from './client'
import type { GeneSummaryPublic, GeneSummaryFull } from '@/types/geneSummary'

export async function getPublicSummary(geneId: string): Promise<GeneSummaryPublic | null> {
  try {
    const response = await api.get(`/genes/${geneId}/summary`)
    return response.data
  } catch (error: any) {
    if (error.response?.status === 404) {
      return null
    }
    throw error
  }
}

export async function getFullSummary(geneId: string): Promise<GeneSummaryFull> {
  const response = await api.get(`/genes/${geneId}/summary/full`)
  return response.data
}

export async function recomputeSummary(geneId: string): Promise<void> {
  await api.post(`/genes/${geneId}/summary/recompute`)
}
```

**File**: `frontend/src/api/validation.ts`

```typescript
import api from './client'
import type { ValidationResult } from '@/types/validation'

export async function validateHGNC(
  geneSymbol: string,
  skipCache = false
): Promise<ValidationResult> {
  const response = await api.post('/validation/hgnc', null, {
    params: { gene_symbol: geneSymbol, skip_cache: skipCache },
  })
  return response.data
}

export async function validatePubMed(
  pmid: string,
  skipCache = false
): Promise<ValidationResult> {
  const response = await api.post('/validation/pubmed', null, {
    params: { pmid, skip_cache: skipCache },
  })
  return response.data
}

export async function validateHPO(
  hpoTerm: string,
  skipCache = false
): Promise<ValidationResult> {
  const response = await api.post('/validation/hpo', null, {
    params: { hpo_term: hpoTerm, skip_cache: skipCache },
  })
  return response.data
}

export async function validateBatch(
  validator: string,
  values: string[]
): Promise<Record<string, ValidationResult>> {
  const response = await api.post('/validation/validate', {
    validator_name: validator,
    values,
  })
  return response.data
}
```

---

## TypeScript Types

**File**: `frontend/src/types/evidence.ts`

```typescript
export interface EvidenceItem {
  id: string
  curation_id: string
  evidence_category: string
  evidence_type: 'genetic' | 'experimental'
  evidence_data: Record<string, any>
  computed_score: number | null
  validation_status: 'pending' | 'valid' | 'invalid' | 'migrated'
  created_at: string
  updated_at: string
  created_by: string
}

export interface EvidenceItemCreate {
  evidence_category: string
  evidence_type: 'genetic' | 'experimental'
  evidence_data: Record<string, any>
}

export interface EvidenceItemUpdate {
  evidence_data?: Record<string, any>
  validation_status?: string
}
```

**File**: `frontend/src/types/geneSummary.ts`

```typescript
export interface ScopeSummary {
  scope_id: string
  scope_name: string
  is_public: boolean
  classification: string | null
  genetic_score: number
  experimental_score: number
  total_score: number
  last_updated: string
  curator_count: number
  evidence_count: number
}

export interface GeneSummaryPublic {
  gene_id: string
  public_scopes_count: number
  classification_summary: Record<string, number>
  consensus_classification: string | null
  has_conflicts: boolean
  scope_summaries: ScopeSummary[]
  last_updated: string
}

export interface GeneSummaryFull extends GeneSummaryPublic {
  total_scopes_curated: number
  private_scopes_count: number
  consensus_confidence: number | null
}
```

**File**: `frontend/src/types/validation.ts`

```typescript
export interface ValidationResult {
  is_valid: boolean
  status: 'valid' | 'invalid' | 'not_found' | 'error'
  data?: Record<string, any>
  suggestions?: {
    did_you_mean: string[]
  }
  error_message?: string
}
```

---

## Routing

**File**: `frontend/src/router/index.ts` (ADD)

```typescript
{
  path: '/genes/:geneId/summary',
  name: 'GeneSummary',
  component: () => import('@/views/GeneSummaryView.vue'),
  meta: { requiresAuth: false } // Public view
},
{
  path: '/curations/:curationId/evidence',
  name: 'EvidenceEntry',
  component: () => import('@/views/EvidenceEntryView.vue'),
  meta: { requiresAuth: true }
},
```

---

## Testing Checklist

### Component Tests
- [ ] ValidatedInput.vue (validation states, suggestions)
- [ ] ClinGenGeneticEvidenceForm.vue (conditional fields, validation)
- [ ] ScopeSummaryCard.vue (display, colors)
- [ ] GeneSummaryView.vue (loading, error, data display)

### Composable Tests
- [ ] useValidation (debouncing, caching, error handling)
- [ ] useEvidence (CRUD operations, filtering)
- [ ] useScoring (score calculations match backend)

### Store Tests
- [ ] evidenceStore (CRUD, filtering by category)
- [ ] geneSummaryStore (public vs full, caching)
- [ ] validationStore (caching, batch validation)

### Integration Tests
- [ ] Create evidence item → updates store → triggers re-score
- [ ] Validate HGNC → caches result → reuses cache
- [ ] View gene summary → fetches from API → displays correctly

---

## UI/UX Guidelines

### Colors (Vuetify 3)
- **Definitive**: `success` (green)
- **Strong**: `info` (blue)
- **Moderate**: `warning` (orange)
- **Limited**: `grey`
- **No Known**: `error` (red)
- **Conflicts**: `warning` (orange alert)

### Icons (MDI)
- Gene: `mdi-dna`
- Evidence: `mdi-file-document`
- Validation: `mdi-check-circle` / `mdi-alert-circle`
- Loading: `mdi-loading mdi-spin`
- Info: `mdi-information`

### Spacing
- Form fields: 16px margin-bottom
- Section dividers: 24px margin-top
- Cards: 16px padding

---

## Next Steps

1. **Review** this document with frontend team
2. **Implement** stores (evidence, geneSummary, validation)
3. **Implement** composables (useValidation, useEvidence, useScoring)
4. **Implement** ValidatedInput component
5. **Implement** hand-coded ClinGen forms
6. **Implement** GeneSummaryView
7. **Write** component tests
8. **Integration** testing with backend API

---

**Document Status**: ✅ Ready for Implementation
**Estimated Effort**: 4-5 weeks (Phase 3)
**Dependencies**: API implementation (Phase 2) must be complete
