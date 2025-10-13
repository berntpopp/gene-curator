# Frontend Refactor Plan - Vue 3 + Vite Migration with ClinGen Components

This directory contains the frontend modernization plan for migrating from Vue CLI to Vite while implementing ClinGen-specific UI components and workflows.

## Work Stream Overview

**Objective**: Modernize the frontend architecture while preserving the configuration-driven workflow system and adding specialized ClinGen evidence entry components.

**Key Transformations**:
- **Build System**: Vue CLI → Vite for faster development and builds
- **State Management**: Ad-hoc stores → Pinia for centralized state
- **ClinGen UI**: Specialized components for evidence entry and scoring display
- **Type Safety**: Enhanced TypeScript integration with API contracts
- **Performance**: Modern bundling and code splitting

## Directory Structure

```
frontend/
├── README.md                    # This overview
├── migration_strategy.md        # Vue CLI to Vite migration plan
├── clingen_components.md        # ClinGen-specific component design
├── state_management.md          # Pinia store architecture
├── configuration_system.md      # Preserving workflow configuration system
├── routing_auth.md             # Route guards and authentication
├── testing_strategy.md         # Frontend testing with Vitest
└── implementation/
    ├── project_structure.md    # New Vite project organization
    ├── dependencies.md         # Updated package.json dependencies
    ├── build_config.md         # Vite configuration
    └── deployment.md           # Static hosting and CI/CD updates
```

## Key Features

### 1. Modern Development Stack
- **Vite**: Lightning-fast development server and optimized builds
- **Vue 3**: Composition API, better TypeScript support, improved performance
- **Pinia**: Type-safe state management with DevTools integration
- **TypeScript**: Enhanced type safety with API client generation

### 2. ClinGen-Specific Components
- **Evidence Entry Forms**: Structured forms for each evidence type
- **Real-time Scoring**: Live score calculation as evidence is entered
- **Summary Preview**: Auto-generated evidence summary display
- **Workflow Management**: Multi-stage review process visualization

### 3. Enhanced User Experience
- **Progressive Web App**: Offline capability and installation
- **Responsive Design**: Mobile-first approach with Vuetify 3
- **Accessibility**: WCAG 2.1 compliance for scientific accessibility
- **Performance**: Code splitting and lazy loading

## Current Architecture Analysis

### Components to Preserve
- **Configuration System**: `src/config/workflows/` structure
- **Dynamic Form Rendering**: Component-based form generation
- **Data Display Table**: Flexible table component for various data
- **User Authentication**: Firebase Auth integration (initially)
- **CSV Import/Export**: Data management functionality

### Components to Transform
- **Store Pattern**: Replace with Pinia stores
- **Build System**: Migrate to Vite configuration
- **Component Structure**: Modernize with Composition API
- **Route Guards**: Update for new authentication system
- **State Reactivity**: Improve with Pinia reactivity

### Components to Add
- **ClinGen Evidence Forms**: Specialized evidence entry components
- **Scoring Dashboard**: Real-time evidence score visualization
- **Summary Generator**: Template-based summary creation interface
- **Workflow Tracker**: Professional curation process management
- **External Evidence**: Integration forms for PanelApp, etc.

## Migration Phases

### Phase 1: Foundation Migration
1. **Vite Setup**: Create new Vite configuration
2. **Package Migration**: Update dependencies to Vue 3 + Vite compatible versions
3. **Basic Component Migration**: Convert existing components to Composition API
4. **Routing Update**: Migrate Vue Router to v4

### Phase 2: State Management
1. **Pinia Integration**: Replace Firebase direct access with Pinia stores
2. **API Client**: Create typed API client for FastAPI backend
3. **Store Migration**: Convert existing store patterns to Pinia
4. **Reactivity Enhancement**: Improve component reactivity

### Phase 3: ClinGen Components
1. **Evidence Entry Forms**: Build specialized ClinGen evidence components
2. **Scoring Integration**: Real-time score calculation and display
3. **Summary Generation**: Evidence summary creation interface
4. **Workflow Management**: Professional review process components

### Phase 4: Enhancement & Optimization
1. **Performance Optimization**: Code splitting and lazy loading
2. **PWA Features**: Service worker and offline capability
3. **Testing**: Comprehensive test suite with Vitest
4. **Accessibility**: WCAG compliance and screen reader support

## ClinGen Component Architecture

### Evidence Entry Components
```vue
<!-- ClinGenEvidenceEntry.vue -->
<template>
  <v-tabs v-model="activeTab">
    <v-tab value="case-level">Case-Level Evidence</v-tab>
    <v-tab value="segregation">Segregation Data</v-tab>
    <v-tab value="case-control">Case-Control Studies</v-tab>
    <v-tab value="experimental">Experimental Evidence</v-tab>
  </v-tabs>
  
  <v-window v-model="activeTab">
    <v-window-item value="case-level">
      <CaseLevelEvidenceForm 
        v-model="evidence.genetic_evidence.case_level_data"
        @update="updateScores"
      />
    </v-window-item>
    <!-- Other tabs... -->
  </v-window>
  
  <!-- Real-time scoring display -->
  <ClinGenScoreCard 
    :genetic-score="scores.genetic"
    :experimental-score="scores.experimental"
    :verdict="verdict"
  />
</template>
```

### Score Display Components
```vue
<!-- ClinGenScoreCard.vue -->
<template>
  <v-card class="clingen-score-card">
    <v-card-title>ClinGen Evidence Scores</v-card-title>
    
    <v-row class="ma-2">
      <v-col cols="6">
        <v-progress-circular
          :model-value="(geneticScore / 12) * 100"
          :color="getScoreColor(geneticScore, 12)"
          size="80"
          width="8"
        >
          <span class="text-h6">{{ geneticScore }}/12</span>
        </v-progress-circular>
        <p class="text-center mt-2">Genetic Evidence</p>
      </v-col>
      
      <v-col cols="6">
        <v-progress-circular
          :model-value="(experimentalScore / 6) * 100"
          :color="getScoreColor(experimentalScore, 6)"
          size="80"
          width="8"
        >
          <span class="text-h6">{{ experimentalScore }}/6</span>
        </v-progress-circular>
        <p class="text-center mt-2">Experimental Evidence</p>
      </v-col>
    </v-row>
    
    <v-alert 
      :type="getVerdictType(verdict)"
      :color="getVerdictColor(verdict)"
      class="ma-4"
    >
      <div class="d-flex align-center">
        <v-icon :icon="getVerdictIcon(verdict)" class="mr-2"></v-icon>
        <div>
          <div class="text-h6">{{ verdict }}</div>
          <div class="text-body-2">Total Score: {{ totalScore }}/18</div>
        </div>
      </div>
    </v-alert>
  </v-card>
</template>
```

## State Management with Pinia

### Curation Store
```typescript
// stores/curation.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Curation, CurationCreate, CurationResponse } from '@/types/api'
import { apiClient } from '@/api/client'

export const useCurationStore = defineStore('curation', () => {
  // State
  const curations = ref<CurationResponse[]>([])
  const currentCuration = ref<CurationResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const curationsByVerdict = computed(() => {
    return curations.value.reduce((acc, curation) => {
      const verdict = curation.verdict
      if (!acc[verdict]) acc[verdict] = []
      acc[verdict].push(curation)
      return acc
    }, {} as Record<string, CurationResponse[]>)
  })

  // Actions
  async function fetchCurations() {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiClient.get<CurationResponse[]>('/curations/')
      curations.value = response.data
    } catch (err) {
      error.value = 'Failed to fetch curations'
      console.error(err)
    } finally {
      loading.value = false
    }
  }

  async function createCuration(curationData: CurationCreate) {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiClient.post<CurationResponse>('/curations/', curationData)
      curations.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = 'Failed to create curation'
      console.error(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateCuration(id: string, curationData: Partial<CurationCreate>) {
    loading.value = true
    error.value = null
    
    try {
      const response = await apiClient.put<CurationResponse>(`/curations/${id}`, curationData)
      const index = curations.value.findIndex(c => c.id === id)
      if (index !== -1) {
        curations.value[index] = response.data
      }
      return response.data
    } catch (err) {
      error.value = 'Failed to update curation'
      console.error(err)
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    curations,
    currentCuration,
    loading,
    error,
    
    // Computed
    curationsByVerdict,
    
    // Actions
    fetchCurations,
    createCuration,
    updateCuration
  }
})
```

## Configuration System Preservation

The current configuration-driven workflow system will be preserved and enhanced:

### Enhanced Configuration Structure
```typescript
// types/configuration.ts
interface ClinGenFieldConfig extends FieldConfig {
  clingen_category?: 'genetic' | 'experimental' | 'metadata'
  evidence_type?: string
  scoring_weight?: number
  validation_rules?: ClinGenValidationRule[]
}

interface ClinGenValidationRule {
  type: 'required_pmid' | 'valid_hpo_terms' | 'score_range'
  message: string
  validator: (value: any) => boolean
}

// Enhanced workflow configuration
interface ClinGenWorkflowConfig extends WorkflowConfig {
  clingen_compliance: {
    sop_version: string
    required_evidence_categories: string[]
    scoring_matrix: ScoringMatrixConfig
    summary_template: string
  }
  evidence_forms: {
    case_level: ClinGenFieldConfig[]
    segregation: ClinGenFieldConfig[]
    experimental: ClinGenFieldConfig[]
  }
}
```

## Integration Points

- **Database Work Stream**: Uses PostgreSQL schema for data persistence
- **API Work Stream**: Consumes FastAPI endpoints with full type safety
- **Original Firebase**: Maintains compatibility during migration period

## Work Stream Status

- [x] Requirements analysis and component inventory
- [ ] Migration strategy documentation
- [ ] ClinGen component specifications
- [ ] Pinia store architecture design
- [ ] Configuration system enhancement plan
- [ ] Testing strategy development

## Success Criteria

- **Migration Completeness**: All current functionality preserved
- **ClinGen Integration**: Seamless evidence entry and scoring workflow
- **Performance**: 50% faster development builds, 30% smaller production bundles
- **Type Safety**: Full TypeScript coverage with API contract validation
- **User Experience**: Improved accessibility and mobile responsiveness
- **Developer Experience**: Hot module replacement and enhanced debugging

## Next Steps

1. Document detailed migration strategy from Vue CLI to Vite
2. Design ClinGen-specific component architecture
3. Plan Pinia store structure and data flow
4. Enhance configuration system for ClinGen compliance
5. Create comprehensive testing strategy
6. Plan deployment and CI/CD updates