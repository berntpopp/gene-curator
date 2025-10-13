# Gene Curator - Frontend Development Guide

## Overview

Gene Curator's frontend is built with Vue 3, Vite, and Pinia, featuring a comprehensive scope-based, multi-stage workflow system for gene-disease curation. This guide covers the component architecture for clinical specialty organization, 4-eyes principle quality assurance, multi-curation management, state management, and development patterns for the schema-agnostic platform.

## Technology Stack

### Core Technologies
- **Vue 3.4.21**: Composition API with `<script setup>` syntax
- **Vite 5.2.8**: Fast development server and build tool
- **Pinia 2.1.7**: State management with Composition API
- **Vuetify 3.9.3**: Material Design component library
- **TypeScript**: Type safety and enhanced developer experience
- **Vue Router**: Client-side routing with authentication guards

### Build and Development
- **ESLint + Prettier**: Code formatting and linting
- **Vite HMR**: Hot module replacement for fast development
- **Component Testing**: Vitest for unit and component tests
- **Bundle Analysis**: Built-in bundle analyzer for optimization

## Project Structure

```
frontend/src/
├── components/
│   ├── scope/                # Scope-based organization components
│   │   ├── ScopeSelector.vue
│   │   ├── ScopeManagement.vue
│   │   ├── GeneScopeAssignment.vue
│   │   └── ScopePermissions.vue
│   ├── workflow/             # Multi-stage workflow components
│   │   ├── WorkflowNavigation.vue
│   │   ├── StageIndicator.vue
│   │   ├── WorkflowProgress.vue
│   │   └── StageTransition.vue
│   ├── precuration/          # Precuration stage components
│   │   ├── PrecurationForm.vue
│   │   ├── PrecurationsList.vue
│   │   ├── PrecurationSelector.vue
│   │   └── MultiplePrecurations.vue
│   ├── curation/             # Curation stage components
│   │   ├── CurationForm.vue
│   │   ├── EvidenceEntryForm.vue
│   │   ├── DynamicScoringCard.vue
│   │   ├── MultipleCurations.vue
│   │   └── PrecurationReference.vue
│   ├── review/               # 4-Eyes principle review components
│   │   ├── ReviewAssignment.vue
│   │   ├── ReviewInterface.vue
│   │   ├── ReviewActions.vue
│   │   ├── ReviewHistory.vue
│   │   └── FourEyesValidator.vue
│   ├── active/               # Active status management components
│   │   ├── ActiveCurationCard.vue
│   │   ├── ArchiveManagement.vue
│   │   ├── StatusTransition.vue
│   │   └── CurationComparison.vue
│   ├── drafts/               # Draft management components
│   │   ├── DraftSaver.vue
│   │   ├── AutoSaveIndicator.vue
│   │   ├── ResumeWorkflow.vue
│   │   └── VersionHistory.vue
│   ├── dynamic/              # Schema-driven components
│   │   ├── DynamicForm.vue
│   │   ├── SchemaRenderer.vue
│   │   ├── FieldValidator.vue
│   │   └── MethodologySelector.vue
│   └── common/               # Reusable components
│       ├── AppBar.vue
│       ├── ScopeNavigation.vue
│       ├── InfoField.vue
│       ├── ConfirmationDialog.vue
│       └── MessageSnackbar.vue
├── stores/                   # Pinia state management
│   ├── auth.js
│   ├── scopes.js             # Scope management
│   ├── genes.js
│   ├── geneScopeAssignments.js
│   ├── precurations.js       # Multiple precurations per gene-scope
│   ├── curations.js          # Multiple curations per gene-scope
│   ├── reviews.js            # 4-eyes principle reviews
│   ├── activeCurations.js    # Active status management
│   ├── schemas.js            # Schema and workflow pairs
│   ├── scoring.js            # Dynamic scoring engines
│   ├── drafts.js             # Draft persistence
│   └── users.js
├── views/                    # Page-level components
│   ├── Dashboard.vue         # Scope-based dashboard
│   ├── ScopeManagement.vue   # Scope administration
│   ├── GenesTable.vue
│   ├── GeneScopeAssignments.vue
│   ├── PrecurationsTable.vue # Scope-filtered precurations
│   ├── CurationsTable.vue    # Scope-filtered curations
│   ├── ReviewDashboard.vue   # 4-eyes principle review queue
│   ├── ActiveCurations.vue   # Active curation management
│   ├── WorkflowDetail.vue    # Multi-stage workflow view
│   └── UserManagement.vue
├── api/                      # API client layer
│   ├── client.js
│   ├── auth.js
│   ├── scopes.js
│   ├── genes.js
│   ├── geneScopeAssignments.js
│   ├── precurations.js
│   ├── curations.js
│   ├── reviews.js
│   ├── activeCurations.js
│   ├── schemas.js
│   └── scoring.js
├── router/                   # Vue Router configuration
│   ├── index.js
│   └── scopeGuards.js        # Scope-based route guards
├── composables/              # Reusable composition functions
│   ├── useNotifications.js
│   ├── useScopePermissions.js
│   ├── useWorkflowNavigation.js
│   ├── useMultiCuration.js
│   ├── useFourEyesPrinciple.js
│   ├── useDraftManagement.js
│   ├── useAutoSave.js
│   └── useDynamicScoring.js
└── types/                    # TypeScript type definitions
    ├── index.ts
    ├── scopes.ts
    ├── workflow.ts
    ├── multi-curation.ts
    └── review.ts
```

## Component Architecture

### Scope-Based Organization Components

#### 1. ScopeSelector.vue
Handles clinical specialty selection and scope-based navigation.

**Key Features**:
- Clinical specialty selection (kidney-genetics, cardio-genetics, etc.)
- Scope-based permission validation
- User's assigned scope filtering
- Institution-based scope organization
- Default scope preferences

**Usage Example**:
```vue
<template>
  <ScopeSelector 
    v-model="selectedScope"
    :user-scopes="userAssignedScopes"
    :show-all="isAdmin"
    @scope-changed="handleScopeChange"
  />
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import ScopeSelector from '@/components/scope/ScopeSelector.vue'

const authStore = useAuthStore()
const scopesStore = useScopesStore()

const selectedScope = ref(null)
const isAdmin = computed(() => authStore.isAdmin)
const userAssignedScopes = computed(() => authStore.user?.assigned_scopes || [])

const handleScopeChange = (scope) => {
  console.log('Scope changed:', scope)
  // Filter data by scope
  scopesStore.setActiveScope(scope)
  // Update URL or navigate
  router.push({ query: { scope: scope.name } })
}
</script>
```

**Scope Validation Rules**:
```javascript
// Scope access validation
const scopeAccessRules = [
  scope => !!scope || 'Clinical specialty scope is required',
  scope => userAssignedScopes.value.includes(scope.id) || isAdmin.value || 'Access denied to this clinical specialty'
]

// Institution scope validation
const institutionScopeRules = [
  scope => !scope.institution || authStore.user.institution === scope.institution || 'Institution access required'
]
```

#### 2. WorkflowNavigation.vue
Multi-stage workflow navigation with progress tracking and stage transitions.

**Key Features**:
- 5-stage workflow visualization (Entry → Precuration → Curation → Review → Active)
- Stage completion indicators with 4-eyes principle status
- Scope-based workflow filtering
- Permission-based stage access control
- Multi-curation support with active/archived indicators

**Workflow Navigation Structure**:
```vue
<template>
  <v-stepper v-model="currentStage" class="workflow-navigation">
    <v-stepper-header>
      <v-stepper-item 
        :value="1" 
        :complete="isStageComplete('entry')"
        :color="getStageColor('entry')"
      >
        Gene Entry
      </v-stepper-item>
      
      <v-divider />
      
      <v-stepper-item 
        :value="2" 
        :complete="isStageComplete('precuration')"
        :color="getStageColor('precuration')"
      >
        Precuration ({{ precurationCount }})
      </v-stepper-item>
      
      <v-divider />
      
      <v-stepper-item 
        :value="3" 
        :complete="isStageComplete('curation')"
        :color="getStageColor('curation')"
      >
        Curation ({{ curationCount }})
      </v-stepper-item>
      
      <v-divider />
      
      <v-stepper-item 
        :value="4" 
        :complete="isStageComplete('review')"
        :color="getStageColor('review')"
      >
        Review (4-Eyes)
      </v-stepper-item>
      
      <v-divider />
      
      <v-stepper-item 
        :value="5" 
        :complete="isStageComplete('active')"
        :color="getStageColor('active')"
      >
        Active Status
      </v-stepper-item>
    </v-stepper-header>

    <v-stepper-window v-model="currentStage">
      <v-stepper-window-item :value="1">
        <GeneScopeAssignment 
          v-model="geneScopeData"
          :selected-scope="selectedScope"
          @assigned="handleGeneAssignment"
        />
      </v-stepper-window-item>
      
      <v-stepper-window-item :value="2">
        <MultiplePrecurations 
          :gene-scope="geneScopeData"
          :existing-precurations="precurations"
          @precuration-completed="handlePrecurationCompleted"
        />
      </v-stepper-window-item>
      
      <v-stepper-window-item :value="3">
        <MultipleCurations 
          :gene-scope="geneScopeData"
          :available-precurations="completedPrecurations"
          :existing-curations="curations"
          @curation-submitted="handleCurationSubmitted"
        />
      </v-stepper-window-item>
      
      <v-stepper-window-item :value="4">
        <ReviewInterface 
          :pending-reviews="pendingReviews"
          :four-eyes-compliance="true"
          @review-completed="handleReviewCompleted"
        />
      </v-stepper-window-item>
      
      <v-stepper-window-item :value="5">
        <ActiveCurationManagement 
          :gene-scope="geneScopeData"
          :approved-curations="approvedCurations"
          :current-active="currentActive"
          @status-changed="handleStatusChange"
        />
      </v-stepper-window-item>
    </v-stepper-window>
  </v-stepper>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useWorkflowNavigation } from '@/composables/useWorkflowNavigation'
import { useMultiCuration } from '@/composables/useMultiCuration'

const {
  currentStage,
  isStageComplete,
  getStageColor,
  canAccessStage
} = useWorkflowNavigation()

const {
  precurations,
  curations,
  pendingReviews,
  approvedCurations,
  currentActive,
  precurationCount,
  curationCount
} = useMultiCuration()

const selectedScope = ref(null)
const geneScopeData = ref(null)

const completedPrecurations = computed(() => 
  precurations.value.filter(p => p.status === 'completed')
)

// Handle stage transitions
const handleGeneAssignment = (assignment) => {
  geneScopeData.value = assignment
  currentStage.value = 2
}

const handlePrecurationCompleted = () => {
  if (canAccessStage('curation')) {
    currentStage.value = 3
  }
}

const handleCurationSubmitted = () => {
  if (canAccessStage('review')) {
    currentStage.value = 4
  }
}

const handleReviewCompleted = () => {
  if (canAccessStage('active')) {
    currentStage.value = 5
  }
}
</script>
```

#### 3. ReviewInterface.vue
4-Eyes principle review interface with independent assessment capabilities.

**Key Features**:
- Independent reviewer assignment (different from curation creator)
- Comprehensive curation review with evidence assessment
- Approve/reject/request-revision actions
- Scope-based reviewer pool management
- Review time tracking and performance metrics

**Implementation**:
```vue
<template>
  <v-card>
    <v-card-title>
      <v-icon start color="primary">mdi-account-multiple-check</v-icon>
      4-Eyes Principle Review
    </v-card-title>
    
    <v-card-text>
      <!-- Reviewer Assignment -->
      <div class="mb-4">
        <div class="d-flex justify-space-between align-center mb-2">
          <span class="text-subtitle-1">Assigned Reviewer</span>
          <v-chip 
            :color="reviewerStatus.color" 
            size="small"
            variant="tonal"
          >
            {{ reviewerStatus.text }}
          </v-chip>
        </div>
        <div class="d-flex align-center">
          <v-avatar size="32" class="mr-2">
            <v-icon>mdi-account</v-icon>
          </v-avatar>
          <div>
            <div class="font-weight-medium">{{ review.reviewer?.name }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ review.reviewer?.email }}
            </div>
          </div>
        </div>
      </div>

      <!-- Review Status -->
      <div class="mb-4">
        <div class="d-flex justify-space-between align-center mb-2">
          <span class="text-subtitle-1">Review Status</span>
          <span class="text-h6" :class="getStatusColor(review.status)">
            {{ formatStatus(review.status) }}
          </span>
        </div>
        <v-progress-linear 
          :model-value="getReviewProgress(review.status)"
          :color="getStatusColor(review.status)"
          height="8"
          rounded
        />
      </div>

      <!-- Review Actions -->
      <div class="mb-4" v-if="canReview">
        <div class="text-subtitle-1 mb-2">Review Actions</div>
        <div class="d-flex gap-2">
          <v-btn 
            color="success" 
            variant="tonal"
            @click="showApproveDialog = true"
          >
            <v-icon start>mdi-check</v-icon>
            Approve
          </v-btn>
          <v-btn 
            color="warning" 
            variant="tonal"
            @click="showRevisionDialog = true"
          >
            <v-icon start>mdi-pencil</v-icon>
            Request Revision
          </v-btn>
          <v-btn 
            color="error" 
            variant="tonal"
            @click="showRejectDialog = true"
          >
            <v-icon start>mdi-close</v-icon>
            Reject
          </v-btn>
        </div>
      </div>

      <!-- 4-Eyes Validation -->
      <v-expansion-panels class="mt-4">
        <v-expansion-panel>
          <v-expansion-panel-title>Independence Validation</v-expansion-panel-title>
          <v-expansion-panel-text>
            <FourEyesValidator 
              :curation="curation" 
              :reviewer="review.reviewer"
              :validation-result="independenceValidation"
            />
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </v-card-text>
  </v-card>

  <!-- Review Action Dialogs -->
  <ApprovalDialog 
    v-model="showApproveDialog"
    :review="review"
    @approved="handleApproval"
  />
  
  <RevisionDialog 
    v-model="showRevisionDialog"
    :review="review"
    @revision-requested="handleRevisionRequest"
  />
  
  <RejectionDialog 
    v-model="showRejectDialog"
    :review="review"
    @rejected="handleRejection"
  />
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useReviewsStore } from '@/stores/reviews'
import { useFourEyesPrinciple } from '@/composables/useFourEyesPrinciple'

const authStore = useAuthStore()
const reviewsStore = useReviewsStore()

const props = defineProps({
  review: { type: Object, required: true },
  curation: { type: Object, required: true }
})

const emit = defineEmits(['review-completed'])

const showApproveDialog = ref(false)
const showRevisionDialog = ref(false)
const showRejectDialog = ref(false)

// 4-Eyes principle validation
const {
  validateIndependence,
  canReview,
  independenceValidation
} = useFourEyesPrinciple(props.curation, authStore.user)

const reviewerStatus = computed(() => {
  if (!props.review.reviewer) {
    return { text: 'Unassigned', color: 'grey' }
  }
  
  if (props.review.reviewer.id === props.curation.created_by) {
    return { text: 'Invalid (Same Creator)', color: 'error' }
  }
  
  return { text: 'Valid Reviewer', color: 'success' }
})

const getStatusColor = (status) => {
  const colors = {
    'pending': 'warning',
    'approved': 'success',
    'rejected': 'error',
    'needs_revision': 'info'
  }
  return colors[status] || 'grey'
}

const getReviewProgress = (status) => {
  const progress = {
    'pending': 25,
    'needs_revision': 50,
    'approved': 100,
    'rejected': 100
  }
  return progress[status] || 0
}

const formatStatus = (status) => {
  return status.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// Review action handlers
const handleApproval = async (approvalData) => {
  try {
    await reviewsStore.approveReview(props.review.id, approvalData)
    emit('review-completed', { action: 'approved', data: approvalData })
    showApproveDialog.value = false
  } catch (error) {
    console.error('Failed to approve review:', error)
  }
}

const handleRevisionRequest = async (revisionData) => {
  try {
    await reviewsStore.requestRevision(props.review.id, revisionData)
    emit('review-completed', { action: 'revision_requested', data: revisionData })
    showRevisionDialog.value = false
  } catch (error) {
    console.error('Failed to request revision:', error)
  }
}

const handleRejection = async (rejectionData) => {
  try {
    await reviewsStore.rejectReview(props.review.id, rejectionData)
    emit('review-completed', { action: 'rejected', data: rejectionData })
    showRejectDialog.value = false
  } catch (error) {
    console.error('Failed to reject review:', error)
  }
}
</script>
```

### Multi-Curation Components

#### MultiplePrecurations.vue
Manages multiple precurations per gene-scope combination with comparison capabilities.

```vue
<template>
  <div class="multiple-precurations">
    <div class="d-flex justify-space-between align-center mb-4">
      <h3>Precurations for {{ geneScope.gene.approved_symbol }} ({{ geneScope.scope.display_name }})</h3>
      <v-btn 
        color="primary" 
        @click="showCreateForm = true"
        :disabled="!canCreatePrecuration"
      >
        <v-icon start>mdi-plus</v-icon>
        New Precuration
      </v-btn>
    </div>

    <!-- Existing Precurations -->
    <v-row>
      <v-col 
        v-for="precuration in existingPrecurations" 
        :key="precuration.id"
        cols="12" 
        md="6" 
        lg="4"
      >
        <PrecurationCard 
          :precuration="precuration"
          :gene-scope="geneScope"
          @edit="editPrecuration"
          @complete="completePrecuration"
          @compare="addToComparison"
        />
      </v-col>
    </v-row>

    <!-- Comparison View -->
    <v-expand-transition>
      <PrecurationComparison 
        v-if="comparisonPrecurations.length > 1"
        :precurations="comparisonPrecurations"
        @clear="clearComparison"
      />
    </v-expand-transition>

    <!-- Create/Edit Form -->
    <v-dialog v-model="showCreateForm" max-width="800">
      <PrecurationForm 
        :precuration="editingPrecuration"
        :gene-scope="geneScope"
        @submit="handlePrecurationSubmit"
        @cancel="showCreateForm = false"
        @auto-save="handleAutoSave"
      />
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { usePrecurationsStore } from '@/stores/precurations'
import { useAuthStore } from '@/stores/auth'

const precurationsStore = usePrecurationsStore()
const authStore = useAuthStore()

const props = defineProps({
  geneScope: { type: Object, required: true },
  existingPrecurations: { type: Array, default: () => [] }
})

const emit = defineEmits(['precuration-completed'])

const showCreateForm = ref(false)
const editingPrecuration = ref(null)
const comparisonPrecurations = ref([])

const canCreatePrecuration = computed(() => {
  return authStore.canCreateInScope(props.geneScope.scope.id)
})

const editPrecuration = (precuration) => {
  editingPrecuration.value = precuration
  showCreateForm.value = true
}

const completePrecuration = async (precuration) => {
  try {
    await precurationsStore.completePrecuration(precuration.id)
    emit('precuration-completed', precuration)
  } catch (error) {
    console.error('Failed to complete precuration:', error)
  }
}

const handlePrecurationSubmit = async (formData) => {
  try {
    if (editingPrecuration.value) {
      await precurationsStore.updatePrecuration(editingPrecuration.value.id, formData)
    } else {
      await precurationsStore.createPrecuration({
        ...formData,
        gene_id: props.geneScope.gene.id,
        scope_id: props.geneScope.scope.id
      })
    }
    showCreateForm.value = false
    editingPrecuration.value = null
  } catch (error) {
    console.error('Failed to save precuration:', error)
  }
}

const handleAutoSave = async (formData) => {
  // Auto-save draft functionality
  await precurationsStore.autoSaveDraft(formData)
}

const addToComparison = (precuration) => {
  if (!comparisonPrecurations.value.includes(precuration)) {
    comparisonPrecurations.value.push(precuration)
  }
}

const clearComparison = () => {
  comparisonPrecurations.value = []
}
</script>
```

#### MultipleCurations.vue
Manages multiple curations per gene-scope with precuration dependencies.

```vue
<template>
  <div class="multiple-curations">
    <div class="d-flex justify-space-between align-center mb-4">
      <h3>Curations for {{ geneScope.gene.approved_symbol }} ({{ geneScope.scope.display_name }})</h3>
      <v-btn 
        color="primary" 
        @click="showCreateForm = true"
        :disabled="!canCreateCuration"
      >
        <v-icon start>mdi-plus</v-icon>
        New Curation
      </v-btn>
    </div>

    <!-- Precuration Selection -->
    <v-alert 
      v-if="!selectedPrecuration && availablePrecurations.length === 0"
      type="warning"
      class="mb-4"
    >
      No completed precurations available. Complete a precuration first.
    </v-alert>

    <v-select 
      v-if="availablePrecurations.length > 0"
      v-model="selectedPrecuration"
      :items="availablePrecurations"
      item-title="display_label"
      item-value="id"
      label="Select Precuration Reference"
      class="mb-4"
    />

    <!-- Existing Curations -->
    <v-row>
      <v-col 
        v-for="curation in existingCurations" 
        :key="curation.id"
        cols="12" 
        md="6" 
        lg="4"
      >
        <CurationCard 
          :curation="curation"
          :gene-scope="geneScope"
          :is-active="isActiveCuration(curation)"
          @edit="editCuration"
          @submit-for-review="submitForReview"
          @compare="addToComparison"
        />
      </v-col>
    </v-row>

    <!-- Active Curation Indicator -->
    <v-card 
      v-if="activeCuration"
      color="success"
      variant="tonal"
      class="mt-4"
    >
      <v-card-text>
        <div class="d-flex align-center">
          <v-icon start>mdi-star</v-icon>
          <div>
            <div class="font-weight-medium">Active Curation</div>
            <div class="text-caption">
              {{ activeCuration.computed_verdict }} - 
              Activated {{ formatDate(activeCuration.activated_at) }}
            </div>
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- Curation Form -->
    <v-dialog v-model="showCreateForm" max-width="1200">
      <CurationForm 
        :curation="editingCuration"
        :gene-scope="geneScope"
        :precuration-reference="selectedPrecuration"
        @submit="handleCurationSubmit"
        @cancel="showCreateForm = false"
        @auto-save="handleAutoSave"
      />
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useCurationsStore } from '@/stores/curations'
import { useActiveCurationsStore } from '@/stores/activeCurations'
import { useAuthStore } from '@/stores/auth'

const curationsStore = useCurationsStore()
const activeCurationsStore = useActiveCurationsStore()
const authStore = useAuthStore()

const props = defineProps({
  geneScope: { type: Object, required: true },
  availablePrecurations: { type: Array, default: () => [] },
  existingCurations: { type: Array, default: () => [] }
})

const emit = defineEmits(['curation-submitted'])

const showCreateForm = ref(false)
const editingCuration = ref(null)
const selectedPrecuration = ref(null)

const activeCuration = computed(() => {
  return activeCurationsStore.getActiveForGeneScope(
    props.geneScope.gene.id,
    props.geneScope.scope.id
  )
})

const canCreateCuration = computed(() => {
  return authStore.canCreateInScope(props.geneScope.scope.id) && 
         props.availablePrecurations.length > 0
})

const isActiveCuration = (curation) => {
  return activeCuration.value?.curation_id === curation.id
}

const editCuration = (curation) => {
  editingCuration.value = curation
  selectedPrecuration.value = curation.precuration_id
  showCreateForm.value = true
}

const submitForReview = async (curation) => {
  try {
    await curationsStore.submitForReview(curation.id)
    emit('curation-submitted', curation)
  } catch (error) {
    console.error('Failed to submit for review:', error)
  }
}

const handleCurationSubmit = async (formData) => {
  try {
    const curationData = {
      ...formData,
      gene_id: props.geneScope.gene.id,
      scope_id: props.geneScope.scope.id,
      precuration_id: selectedPrecuration.value
    }
    
    if (editingCuration.value) {
      await curationsStore.updateCuration(editingCuration.value.id, curationData)
    } else {
      await curationsStore.createCuration(curationData)
    }
    
    showCreateForm.value = false
    editingCuration.value = null
  } catch (error) {
    console.error('Failed to save curation:', error)
  }
}

const handleAutoSave = async (formData) => {
  await curationsStore.autoSaveDraft(formData)
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString()
}
</script>
```

### Reusable Components

#### InfoField.vue
Displays structured information with optional help tooltips and external links.

```vue
<template>
  <div class="info-field">
    <div class="text-caption text-medium-emphasis">
      {{ label }}
      <v-tooltip v-if="help" location="top">
        <template v-slot:activator="{ props }">
          <v-icon v-bind="props" size="small" class="ml-1">
            mdi-help-circle-outline
          </v-icon>
        </template>
        <span>{{ help }}</span>
      </v-tooltip>
    </div>
    
    <div class="text-body-1" :class="valueClass">
      <slot>
        <a v-if="link" :href="link" target="_blank" class="text-decoration-none">
          {{ displayValue }}
          <v-icon size="small" class="ml-1">mdi-open-in-new</v-icon>
        </a>
        <span v-else>{{ displayValue }}</span>
      </slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number, Boolean, Object], default: null },
  help: { type: String, default: null },
  link: { type: String, default: null },
  format: { type: String, default: 'text' },
  emptyText: { type: String, default: 'Not specified' }
})

const displayValue = computed(() => {
  if (props.value === null || props.value === undefined || props.value === '') {
    return props.emptyText
  }
  
  switch (props.format) {
    case 'date':
      return new Date(props.value).toLocaleDateString()
    case 'datetime':
      return new Date(props.value).toLocaleString()
    case 'boolean':
      return props.value ? 'Yes' : 'No'
    case 'array':
      return Array.isArray(props.value) ? props.value.join(', ') : props.value
    default:
      return props.value
  }
})

const valueClass = computed(() => {
  if (props.value === null || props.value === undefined || props.value === '') {
    return 'text-medium-emphasis font-italic'
  }
  return 'font-weight-medium'
})
</script>
```

## State Management (Pinia)

### Scope-Based Store Architecture

Each major entity has its own Pinia store following a consistent pattern, enhanced with scope-based filtering and multi-stage workflow support:

#### scopes.js Store
```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as scopesApi from '@/api/scopes'

export const useScopesStore = defineStore('scopes', () => {
  // State
  const scopes = ref([])
  const activeScope = ref(null)
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const getUserScopes = computed(() => {
    return (userId) => scopes.value.filter(scope => 
      scope.assigned_curators.some(curator => curator.id === userId)
    )
  })

  const getScopeById = computed(() => {
    return (id) => scopes.value.find(s => s.id === id)
  })

  const activeScopeId = computed(() => activeScope.value?.id)

  // Actions
  const fetchScopes = async (params = {}) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await scopesApi.getScopes(params)
      scopes.value = response.data.scopes
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const setActiveScope = (scope) => {
    activeScope.value = scope
    // Trigger scope-based data filtering across other stores
    localStorage.setItem('activeScope', JSON.stringify(scope))
  }

  const assignCuratorToScope = async (scopeId, userId) => {
    try {
      await scopesApi.assignCurator(scopeId, userId)
      // Update local state
      const scope = scopes.value.find(s => s.id === scopeId)
      if (scope) {
        await fetchScope(scopeId) // Refresh scope data
      }
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  const createScope = async (scopeData) => {
    loading.value = true
    try {
      const response = await scopesApi.createScope(scopeData)
      scopes.value.push(response.data)
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    scopes,
    activeScope,
    loading,
    error,
    
    // Getters
    getUserScopes,
    getScopeById,
    activeScopeId,
    
    // Actions
    fetchScopes,
    setActiveScope,
    assignCuratorToScope,
    createScope
  }
})
```

#### curations.js Store (Enhanced for Multi-Stage Workflow)
```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as curationsApi from '@/api/curations'
import { useScopesStore } from './scopes'

export const useCurationsStore = defineStore('curations', () => {
  // State
  const curations = ref([])
  const currentCuration = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const draftSaveTimer = ref(null)

  // Scope integration
  const scopesStore = useScopesStore()

  // Getters
  const getCurationById = computed(() => {
    return (id) => curations.value.find(c => c.id === id)
  })

  const getCurationsByScope = computed(() => {
    return (scopeId) => curations.value.filter(c => c.scope_id === scopeId)
  })

  const getCurationsByGeneScope = computed(() => {
    return (geneId, scopeId) => curations.value.filter(c => 
      c.gene_id === geneId && c.scope_id === scopeId
    )
  })

  const curationsByStatus = computed(() => {
    return curations.value.reduce((acc, curation) => {
      const status = curation.status
      if (!acc[status]) acc[status] = []
      acc[status].push(curation)
      return acc
    }, {})
  })

  const pendingReviewCurations = computed(() => {
    return curations.value.filter(c => c.status === 'pending_review')
  })

  const draftCurations = computed(() => {
    return curations.value.filter(c => c.is_draft === true)
  })

  const curationsByVerdict = computed(() => {
    return curations.value.reduce((acc, curation) => {
      const verdict = curation.computed_verdict
      if (!acc[verdict]) acc[verdict] = []
      acc[verdict].push(curation)
      return acc
    }, {})
  })

  // Actions
  const fetchCurations = async (params = {}) => {
    loading.value = true
    error.value = null
    
    // Add active scope filter if not specified
    const queryParams = { ...params }
    if (!queryParams.scope_id && scopesStore.activeScopeId) {
      queryParams.scope_id = scopesStore.activeScopeId
    }
    
    try {
      const response = await curationsApi.getCurations(queryParams)
      curations.value = response.data.curations
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const fetchCuration = async (id) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await curationsApi.getCuration(id)
      currentCuration.value = response.data
      
      // Update in list if exists
      const index = curations.value.findIndex(c => c.id === id)
      if (index !== -1) {
        curations.value[index] = response.data
      }
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const createCuration = async (curationData) => {
    loading.value = true
    error.value = null
    
    // Ensure scope_id is included
    const dataWithScope = {
      ...curationData,
      scope_id: curationData.scope_id || scopesStore.activeScopeId
    }
    
    try {
      const response = await curationsApi.createCuration(dataWithScope)
      curations.value.push(response.data)
      currentCuration.value = response.data
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const updateCuration = async (id, curationData) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await curationsApi.updateCuration(id, curationData)
      
      // Update in list
      const index = curations.value.findIndex(c => c.id === id)
      if (index !== -1) {
        curations.value[index] = response.data
      }
      
      // Update current if it's the same curation
      if (currentCuration.value?.id === id) {
        currentCuration.value = response.data
      }
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // Multi-stage workflow actions
  const submitForReview = async (curationId, reviewData = {}) => {
    loading.value = true
    try {
      const response = await curationsApi.submitForReview(curationId, reviewData)
      
      // Update in list
      const index = curations.value.findIndex(c => c.id === curationId)
      if (index !== -1) {
        curations.value[index] = { ...curations.value[index], ...response.data }
      }
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  // Auto-save functionality
  const autoSaveDraft = async (curationData) => {
    if (draftSaveTimer.value) {
      clearTimeout(draftSaveTimer.value)
    }
    
    draftSaveTimer.value = setTimeout(async () => {
      try {
        const saveData = {
          ...curationData,
          is_draft: true,
          auto_save: true
        }
        
        if (currentCuration.value) {
          await curationsApi.updateCuration(currentCuration.value.id, saveData)
        }
      } catch (error) {
        console.warn('Auto-save failed:', error)
      }
    }, 2000) // Auto-save after 2 seconds of inactivity
  }

  // Schema-aware score calculation
  const previewScores = async (evidenceData, workflowPairId) => {
    try {
      const response = await curationsApi.previewScores({
        workflow_pair_id: workflowPairId,
        evidence_data: evidenceData
      })
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  const generateSummary = async (curationId) => {
    try {
      const response = await curationsApi.generateSummary(curationId)
      return response.data.summary_text
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  const approveCuration = async (id, comment) => {
    try {
      const response = await curationsApi.approveCuration(id, { comment })
      
      // Update in list
      const index = curations.value.findIndex(c => c.id === id)
      if (index !== -1) {
        curations.value[index] = { ...curations.value[index], ...response.data }
      }
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  const publishCuration = async (id) => {
    try {
      const response = await curationsApi.publishCuration(id)
      
      // Update in list
      const index = curations.value.findIndex(c => c.id === id)
      if (index !== -1) {
        curations.value[index] = { ...curations.value[index], ...response.data }
      }
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  // Helper function
  const sumPoints = (evidenceArray) => {
    return evidenceArray.reduce((sum, item) => sum + (parseFloat(item.points) || 0), 0)
  }

  return {
    // State
    curations,
    currentCuration,
    loading,
    error,
    
    // Getters
    getCurationById,
    getCurationsByScope,
    getCurationsByGeneScope,
    curationsByStatus,
    curationsByVerdict,
    pendingReviewCurations,
    draftCurations,
    
    // Actions
    fetchCurations,
    fetchCuration,
    createCuration,
    updateCuration,
    submitForReview,
    autoSaveDraft,
    previewScores,
    generateSummary,
    publishCuration
  }
})
```

#### reviews.js Store (4-Eyes Principle)
```javascript
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as reviewsApi from '@/api/reviews'
import { useAuthStore } from './auth'

export const useReviewsStore = defineStore('reviews', () => {
  // State
  const reviews = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Getters
  const getReviewById = computed(() => {
    return (id) => reviews.value.find(r => r.id === id)
  })

  const pendingReviews = computed(() => {
    return reviews.value.filter(r => r.status === 'pending')
  })

  const myPendingReviews = computed(() => {
    const authStore = useAuthStore()
    return reviews.value.filter(r => 
      r.status === 'pending' && r.reviewer_id === authStore.user?.id
    )
  })

  const completedReviews = computed(() => {
    return reviews.value.filter(r => ['approved', 'rejected', 'needs_revision'].includes(r.status))
  })

  // Actions
  const fetchReviews = async (params = {}) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await reviewsApi.getReviews(params)
      reviews.value = response.data.reviews
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const approveReview = async (reviewId, approvalData) => {
    loading.value = true
    try {
      const response = await reviewsApi.approveReview(reviewId, approvalData)
      
      // Update in list
      const index = reviews.value.findIndex(r => r.id === reviewId)
      if (index !== -1) {
        reviews.value[index] = { ...reviews.value[index], ...response.data }
      }
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const rejectReview = async (reviewId, rejectionData) => {
    loading.value = true
    try {
      const response = await reviewsApi.rejectReview(reviewId, rejectionData)
      
      // Update in list
      const index = reviews.value.findIndex(r => r.id === reviewId)
      if (index !== -1) {
        reviews.value[index] = { ...reviews.value[index], ...response.data }
      }
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const requestRevision = async (reviewId, revisionData) => {
    loading.value = true
    try {
      const response = await reviewsApi.requestRevision(reviewId, revisionData)
      
      // Update in list
      const index = reviews.value.findIndex(r => r.id === reviewId)
      if (index !== -1) {
        reviews.value[index] = { ...reviews.value[index], ...response.data }
      }
      
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    // State
    reviews,
    loading,
    error,
    
    // Getters
    getReviewById,
    pendingReviews,
    myPendingReviews,
    completedReviews,
    
    // Actions
    fetchReviews,
    approveReview,
    rejectReview,
    requestRevision
  }
})
```

#### scoring.js Store (Enhanced for Multi-Methodology)
```javascript
import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as scoringApi from '@/api/scoring'

export const useScoringStore = defineStore('scoring', () => {
  // State
  const availableEngines = ref([])
  const loading = ref(false)
  const error = ref(null)

  // Actions
  const fetchEngines = async () => {
    loading.value = true
    try {
      const response = await scoringApi.getEngines()
      availableEngines.value = response.data.engines
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const calculateScores = async (request) => {
    loading.value = true
    try {
      const response = await scoringApi.calculateScores(request)
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  const validateEvidence = async (request) => {
    try {
      const response = await scoringApi.validateEvidence(request)
      return response.data
    } catch (err) {
      error.value = err.message
      throw err
    }
  }

  return {
    availableEngines,
    loading,
    error,
    fetchEngines,
    calculateScores,
    validateEvidence
  }
})
```

### Scope-Based Store Usage in Components

```vue
<script setup>
import { onMounted, ref, computed } from 'vue'
import { useCurationsStore } from '@/stores/curations'
import { useScopesStore } from '@/stores/scopes'
import { useReviewsStore } from '@/stores/reviews'
import { useSchemaStore } from '@/stores/schemas'
import { useAuthStore } from '@/stores/auth'
import { useNotifications } from '@/composables/useNotifications'
import { useWorkflowNavigation } from '@/composables/useWorkflowNavigation'
import { useMultiCuration } from '@/composables/useMultiCuration'

const curationsStore = useCurationsStore()
const scopesStore = useScopesStore()
const reviewsStore = useReviewsStore()
const schemaStore = useSchemaStore()
const authStore = useAuthStore()
const { showSuccess, showError } = useNotifications()
const { currentStage, navigateToStage } = useWorkflowNavigation()
const { 
  getMultipleCurations, 
  getActiveCuration, 
  canCreateCuration 
} = useMultiCuration()

const selectedScope = ref(null)
const selectedGeneScope = ref(null)
const selectedWorkflowPair = ref(null)
const evidenceData = ref({})
const currentScores = ref(null)
const draftSaveIndicator = ref(false)

const searchFilters = ref({
  scope_id: null,
  gene_id: null,
  workflow_pair_id: null,
  status: null,
  computed_verdict: null,
  is_draft: null
})

// Reactive data from stores with scope filtering
const userScopes = computed(() => scopesStore.getUserScopes(authStore.user?.id))
const activeScope = computed(() => scopesStore.activeScope)
const scopedCurations = computed(() => 
  activeScope.value ? curationsStore.getCurationsByScope(activeScope.value.id) : []
)
const workflowPairs = computed(() => schemaStore.workflowPairs)
const pendingReviews = computed(() => reviewsStore.myPendingReviews)
const loading = computed(() => 
  curationsStore.loading || scopesStore.loading || reviewsStore.loading
)

// Load initial data with scope awareness
onMounted(async () => {
  try {
    // Load user scopes first
    await scopesStore.fetchScopes()
    
    // Set active scope from localStorage or default to first assigned scope
    const savedScope = localStorage.getItem('activeScope')
    if (savedScope) {
      selectedScope.value = JSON.parse(savedScope)
      scopesStore.setActiveScope(selectedScope.value)
    } else if (userScopes.value.length > 0) {
      selectedScope.value = userScopes.value[0]
      scopesStore.setActiveScope(selectedScope.value)
    }
    
    // Load scope-filtered data
    await Promise.all([
      curationsStore.fetchCurations({ scope_id: activeScope.value?.id }),
      schemaStore.fetchWorkflowPairs(),
      reviewsStore.fetchReviews({ reviewer_id: authStore.user.id })
    ])
    
    // Load user default workflow pair for selected scope
    const defaults = await schemaStore.getUserDefaultSchema()
    if (defaults.default_workflow_pair) {
      selectedWorkflowPair.value = defaults.default_workflow_pair
    }
  } catch (error) {
    showError('Failed to load application data')
  }
})

// Scope change handler
const handleScopeChange = async (scope) => {
  selectedScope.value = scope
  scopesStore.setActiveScope(scope)
  
  // Refresh data for new scope
  await Promise.all([
    curationsStore.fetchCurations({ scope_id: scope.id }),
    reviewsStore.fetchReviews({ scope_id: scope.id })
  ])
}

// Real-time scoring with auto-save
const updateScores = async () => {
  if (!selectedWorkflowPair.value || !Object.keys(evidenceData.value).length) {
    return
  }
  
  try {
    const result = await curationsStore.previewScores(
      evidenceData.value,
      selectedWorkflowPair.value.id
    )
    currentScores.value = result
    
    // Trigger auto-save
    await curationsStore.autoSaveDraft({
      workflow_pair_id: selectedWorkflowPair.value.id,
      evidence_data: evidenceData.value,
      computed_scores: result.scores
    })
    
    draftSaveIndicator.value = true
    setTimeout(() => { draftSaveIndicator.value = false }, 2000)
  } catch (error) {
    console.warn('Score calculation failed:', error)
  }
}

// Create curation with scope and precuration dependency
const createCuration = async (formData) => {
  if (!selectedScope.value) {
    showError('Please select a clinical specialty scope')
    return
  }
  
  if (!formData.precuration_id) {
    showError('Please select a precuration reference')
    return
  }
  
  if (!selectedWorkflowPair.value) {
    showError('Please select a curation methodology')
    return
  }
  
  try {
    const curationData = {
      gene_id: formData.gene_id,
      scope_id: selectedScope.value.id,
      precuration_id: formData.precuration_id,
      workflow_pair_id: selectedWorkflowPair.value.id,
      evidence_data: formData.evidence_data || {},
      is_draft: true
    }
    
    const newCuration = await curationsStore.createCuration(curationData)
    showSuccess(`Curation created in ${selectedScope.value.display_name} scope`)
    
    // Navigate to curation stage if using workflow navigation
    navigateToStage('curation')
    
    return newCuration
  } catch (error) {
    showError(error.message || 'Failed to create curation')
    throw error
  }
}

// Submit curation for 4-eyes review
const submitForReview = async (curationId, reviewerAssignment = {}) => {
  try {
    await curationsStore.submitForReview(curationId, reviewerAssignment)
    showSuccess('Curation submitted for 4-eyes principle review')
    
    // Navigate to review stage
    navigateToStage('review')
  } catch (error) {
    showError(error.message || 'Failed to submit for review')
    throw error
  }
}

// Search within active scope
const searchCurations = async () => {
  try {
    const filters = {
      ...searchFilters.value,
      scope_id: activeScope.value?.id // Always filter by active scope
    }
    await curationsStore.fetchCurations(filters)
  } catch (error) {
    showError('Search failed')
  }
}

// Handle review actions (4-eyes principle)
const handleReviewAction = async (reviewId, action, data) => {
  try {
    switch (action) {
      case 'approve':
        await reviewsStore.approveReview(reviewId, data)
        showSuccess('Curation approved')
        break
      case 'reject':
        await reviewsStore.rejectReview(reviewId, data)
        showSuccess('Curation rejected')
        break
      case 'request_revision':
        await reviewsStore.requestRevision(reviewId, data)
        showSuccess('Revision requested')
        break
    }
    
    // Refresh reviews list
    await reviewsStore.fetchReviews({ reviewer_id: authStore.user.id })
  } catch (error) {
    showError(`Failed to ${action} review`)
  }
}
</script>
```

## User Interface Patterns

## Scope-Based and Multi-Stage Composables

### useScopePermissions.js
```javascript
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'

export function useScopePermissions() {
  const authStore = useAuthStore()
  const scopesStore = useScopesStore()

  const canAccessScope = computed(() => {
    return (scopeId) => {
      if (authStore.isAdmin) return true
      
      const userScopes = authStore.user?.assigned_scopes || []
      return userScopes.includes(scopeId)
    }
  })

  const canCreateInScope = computed(() => {
    return (scopeId) => {
      if (!authStore.isCurator && !authStore.isAdmin) return false
      return canAccessScope.value(scopeId)
    }
  })

  const canReviewInScope = computed(() => {
    return (scopeId, creatorId) => {
      if (!authStore.isCurator && !authStore.isAdmin) return false
      if (creatorId === authStore.user?.id) return false // 4-eyes principle
      return canAccessScope.value(scopeId)
    }
  })

  const getAssignedScopes = computed(() => {
    if (authStore.isAdmin) {
      return scopesStore.scopes
    }
    
    const userScopeIds = authStore.user?.assigned_scopes || []
    return scopesStore.scopes.filter(scope => userScopeIds.includes(scope.id))
  })

  const hasInstitutionAccess = computed(() => {
    return (scopeInstitution) => {
      if (authStore.isAdmin) return true
      if (!scopeInstitution) return true // Public scopes
      return authStore.user?.institution === scopeInstitution
    }
  })

  return {
    canAccessScope,
    canCreateInScope,
    canReviewInScope,
    getAssignedScopes,
    hasInstitutionAccess
  }
}
```

### useWorkflowNavigation.js
```javascript
import { ref, computed } from 'vue'
import { useScopePermissions } from './useScopePermissions'

export function useWorkflowNavigation() {
  const { canAccessScope, canCreateInScope, canReviewInScope } = useScopePermissions()
  
  const currentStage = ref(1) // 1: Entry, 2: Precuration, 3: Curation, 4: Review, 5: Active
  const completedStages = ref(new Set())

  const stageNames = {
    1: 'entry',
    2: 'precuration', 
    3: 'curation',
    4: 'review',
    5: 'active'
  }

  const isStageComplete = computed(() => {
    return (stage) => {
      const stageName = typeof stage === 'string' ? stage : stageNames[stage]
      return completedStages.value.has(stageName)
    }
  })

  const canAccessStage = computed(() => {
    return (stage) => {
      const stageNumber = typeof stage === 'string' ? 
        Object.keys(stageNames).find(key => stageNames[key] === stage) : stage
      
      // Sequential access - can only access current or completed stages
      return stageNumber <= currentStage.value || isStageComplete.value(stage)
    }
  })

  const getStageColor = computed(() => {
    return (stage) => {
      const stageName = typeof stage === 'string' ? stage : stageNames[stage]
      
      if (isStageComplete.value(stageName)) return 'success'
      if (currentStage.value === stage || stageNames[currentStage.value] === stage) return 'primary'
      return 'grey'
    }
  })

  const navigateToStage = (stage) => {
    const stageNumber = typeof stage === 'string' ? 
      Object.keys(stageNames).find(key => stageNames[key] === stage) : stage
    
    if (canAccessStage.value(stageNumber)) {
      currentStage.value = parseInt(stageNumber)
    }
  }

  const completeStage = (stage) => {
    const stageName = typeof stage === 'string' ? stage : stageNames[stage]
    completedStages.value.add(stageName)
    
    // Auto-advance to next stage if available
    const nextStage = currentStage.value + 1
    if (nextStage <= 5) {
      currentStage.value = nextStage
    }
  }

  const getStageProgress = computed(() => {
    return (completedStages.value.size / 5) * 100
  })

  return {
    currentStage,
    completedStages,
    stageNames,
    isStageComplete,
    canAccessStage,
    getStageColor,
    getStageProgress,
    navigateToStage,
    completeStage
  }
}
```

### useMultiCuration.js
```javascript
import { ref, computed } from 'vue'
import { useCurationsStore } from '@/stores/curations'
import { usePrecurationsStore } from '@/stores/precurations'
import { useActiveCurationsStore } from '@/stores/activeCurations'
import { useScopePermissions } from './useScopePermissions'

export function useMultiCuration(geneId, scopeId) {
  const curationsStore = useCurationsStore()
  const precurationsStore = usePrecurationsStore()
  const activeCurationsStore = useActiveCurationsStore()
  const { canCreateInScope, canReviewInScope } = useScopePermissions()

  const selectedGeneId = ref(geneId)
  const selectedScopeId = ref(scopeId)

  // Multiple precurations for gene-scope
  const precurations = computed(() => {
    if (!selectedGeneId.value || !selectedScopeId.value) return []
    return precurationsStore.getPrecurationsByGeneScope(selectedGeneId.value, selectedScopeId.value)
  })

  const completedPrecurations = computed(() => {
    return precurations.value.filter(p => p.status === 'completed')
  })

  const precurationCount = computed(() => precurations.value.length)

  // Multiple curations for gene-scope
  const curations = computed(() => {
    if (!selectedGeneId.value || !selectedScopeId.value) return []
    return curationsStore.getCurationsByGeneScope(selectedGeneId.value, selectedScopeId.value)
  })

  const draftCurations = computed(() => {
    return curations.value.filter(c => c.is_draft === true)
  })

  const submittedCurations = computed(() => {
    return curations.value.filter(c => c.status === 'pending_review')
  })

  const approvedCurations = computed(() => {
    return curations.value.filter(c => c.status === 'approved')
  })

  const curationCount = computed(() => curations.value.length)

  // Active curation (one per gene-scope)
  const activeCuration = computed(() => {
    if (!selectedGeneId.value || !selectedScopeId.value) return null
    return activeCurationsStore.getActiveForGeneScope(selectedGeneId.value, selectedScopeId.value)
  })

  // Permissions
  const canCreatePrecuration = computed(() => {
    return canCreateInScope.value(selectedScopeId.value)
  })

  const canCreateCuration = computed(() => {
    return canCreateInScope.value(selectedScopeId.value) && completedPrecurations.value.length > 0
  })

  const canReview = computed(() => {
    return (curation) => {
      return canReviewInScope.value(selectedScopeId.value, curation.created_by)
    }
  })

  // Actions
  const setGeneScope = (geneId, scopeId) => {
    selectedGeneId.value = geneId
    selectedScopeId.value = scopeId
  }

  const getMultiplePrecurations = () => precurations.value
  const getMultipleCurations = () => curations.value
  const getActiveCuration = () => activeCuration.value

  return {
    // State
    selectedGeneId,
    selectedScopeId,
    
    // Precurations
    precurations,
    completedPrecurations,
    precurationCount,
    
    // Curations
    curations,
    draftCurations,
    submittedCurations,
    approvedCurations,
    curationCount,
    
    // Active Status
    activeCuration,
    
    // Permissions
    canCreatePrecuration,
    canCreateCuration,
    canReview,
    
    // Actions
    setGeneScope,
    getMultiplePrecurations,
    getMultipleCurations,
    getActiveCuration
  }
}
```

## Multi-Methodology Composables

### useSchemaValidator.js
```javascript
import { computed } from 'vue'

export function useSchemaValidator() {
  const generateRules = (fieldSchema) => {
    const rules = []
    
    if (fieldSchema.required) {
      rules.push(v => !!v || `${fieldSchema.label || 'Field'} is required`)
    }
    
    if (fieldSchema.type === 'string' && fieldSchema.min_length) {
      rules.push(v => !v || v.length >= fieldSchema.min_length || 
        `Minimum ${fieldSchema.min_length} characters required`)
    }
    
    if (fieldSchema.type === 'string' && fieldSchema.max_length) {
      rules.push(v => !v || v.length <= fieldSchema.max_length || 
        `Maximum ${fieldSchema.max_length} characters allowed`)
    }
    
    if (fieldSchema.type === 'number') {
      rules.push(v => !v || !isNaN(Number(v)) || 'Must be a valid number')
      
      if (fieldSchema.min !== undefined) {
        rules.push(v => !v || Number(v) >= fieldSchema.min || 
          `Must be at least ${fieldSchema.min}`)
      }
      
      if (fieldSchema.max !== undefined) {
        rules.push(v => !v || Number(v) <= fieldSchema.max || 
          `Must be at most ${fieldSchema.max}`)
      }
    }
    
    if (fieldSchema.validation) {
      const customRule = getCustomValidationRule(fieldSchema.validation)
      if (customRule) rules.push(customRule)
    }
    
    return rules
  }
  
  const getCustomValidationRule = (validationType) => {
    const validationRules = {
      pmid_format: v => !v || /^[0-9]{7,8}$/.test(v) || 'Invalid PMID format (7-8 digits)',
      mondo_format: v => !v || /^MONDO:\d+$/.test(v) || 'Invalid MONDO ID format (MONDO:######)',
      hgnc_format: v => !v || /^HGNC:\d+$/.test(v) || 'Invalid HGNC ID format (HGNC:######)',
      email: v => !v || /.+@.+\..+/.test(v) || 'Invalid email format',
      url: v => !v || /^https?:\/\/.+/.test(v) || 'Invalid URL format'
    }
    
    return validationRules[validationType]
  }
  
  const validateSchema = (data, schema) => {
    const errors = []
    const warnings = []
    
    if (schema.field_definitions) {
      validateFields(data, schema.field_definitions, errors, warnings, '')
    }
    
    return {
      isValid: errors.length === 0,
      errors,
      warnings
    }
  }
  
  const validateFields = (data, fieldDefs, errors, warnings, prefix) => {
    Object.entries(fieldDefs).forEach(([key, fieldSchema]) => {
      const fieldPath = prefix ? `${prefix}.${key}` : key
      const value = data[key]
      
      // Required field validation
      if (fieldSchema.required && (value === null || value === undefined || value === '')) {
        errors.push(`${fieldSchema.label || key} is required`)
        return
      }
      
      // Skip further validation if field is empty and not required
      if (!value && !fieldSchema.required) return
      
      // Type-specific validation
      switch (fieldSchema.type) {
        case 'object':
          if (fieldSchema.properties && typeof value === 'object') {
            validateFields(value, fieldSchema.properties, errors, warnings, fieldPath)
          }
          break
          
        case 'array':
          if (Array.isArray(value) && fieldSchema.item_schema) {
            value.forEach((item, index) => {
              if (fieldSchema.item_schema.properties) {
                validateFields(item, fieldSchema.item_schema.properties, errors, warnings, `${fieldPath}[${index}]`)
              }
            })
          }
          break
          
        case 'enum':
          if (fieldSchema.options && !fieldSchema.options.includes(value)) {
            errors.push(`${fieldSchema.label || key} must be one of: ${fieldSchema.options.join(', ')}`)
          }
          break
      }
      
      // Custom validation
      if (fieldSchema.validation) {
        const rule = getCustomValidationRule(fieldSchema.validation)
        if (rule) {
          const result = rule(value)
          if (result !== true) {
            errors.push(result)
          }
        }
      }
    })
  }
  
  return {
    generateRules,
    validateSchema,
    getCustomValidationRule
  }
}
```

### useDynamicScoring.js
```javascript
import { ref } from 'vue'
import { useScoringStore } from '@/stores/scoring'

export function useDynamicScoring() {
  const scoringStore = useScoringStore()
  const currentScores = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const calculateScores = async (request) => {
    loading.value = true
    error.value = null
    
    try {
      const result = await scoringStore.calculateScores(request)
      currentScores.value = result
      return result
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }
  
  const validateEvidence = async (request) => {
    try {
      const result = await scoringStore.validateEvidence(request)
      return result
    } catch (err) {
      error.value = err.message
      throw err
    }
  }
  
  const previewScores = async (evidenceData, workflowPairId) => {
    if (!evidenceData || !workflowPairId) return null
    
    try {
      const result = await calculateScores({
        workflow_pair_id: workflowPairId,
        evidence_data: evidenceData
      })
      return result
    } catch (err) {
      console.warn('Score preview failed:', err)
      return null
    }
  }
  
  return {
    currentScores,
    loading,
    error,
    calculateScores,
    validateEvidence,
    previewScores
  }
}
```

## User Interface Patterns

### Multi-Methodology Data Tables

```vue
<template>
  <div>
    <!-- Methodology Filter -->
    <v-row class="mb-4">
      <v-col cols="12" md="4">
        <v-select
          v-model="selectedMethodology"
          :items="availableMethodologies"
          label="Filter by Methodology"
          clearable
          @update:model-value="filterByMethodology"
        />
      </v-col>
      <v-col cols="12" md="4">
        <v-select
          v-model="selectedEngine"
          :items="availableEngines"
          item-title="description"
          item-value="name"
          label="Filter by Scoring Engine"
          clearable
        />
      </v-col>
    </v-row>
    
    <!-- Dynamic data table -->
    <v-data-table
      :headers="dynamicHeaders"
      :items="curations"
      :loading="loading"
      :items-per-page="25"
      :search="search"
      class="elevation-1"
    >
      <!-- Gene symbol with link -->
      <template v-slot:item.gene.approved_symbol="{ item }">
        <router-link 
          :to="{ name: 'GeneDetail', params: { id: item.gene_id } }"
          class="text-decoration-none font-weight-medium"
        >
          {{ item.gene.approved_symbol }}
        </router-link>
      </template>
      
      <!-- Methodology with engine info -->
      <template v-slot:item.methodology="{ item }">
        <div class="d-flex flex-column">
          <span class="font-weight-medium">{{ item.workflow_pair?.name }}</span>
          <span class="text-caption text-medium-emphasis">
            {{ item.workflow_pair?.scoring_engine }}
          </span>
        </div>
      </template>

      <!-- Dynamic verdict with methodology-aware coloring -->
      <template v-slot:item.computed_verdict="{ item }">
        <v-chip 
          :color="getVerdictColor(item.computed_verdict, item.workflow_pair?.scoring_engine)" 
          size="small"
          variant="tonal"
        >
          {{ item.computed_verdict }}
        </v-chip>
      </template>

      <!-- Dynamic score display -->
      <template v-slot:item.scores="{ item }">
        <div class="d-flex align-center">
          <span class="mr-2">{{ formatTotalScore(item.computed_scores) }}</span>
          <v-progress-linear
            :model-value="getScoreProgress(item.computed_scores, item.workflow_pair)"
            :color="getScoreColor(item.computed_scores, item.workflow_pair)"
            height="4"
            width="60"
          />
        </div>
      </template>

      <!-- Workflow status -->
      <template v-slot:item.current_status="{ item }">
        <div class="d-flex align-center">
          <v-icon 
            :color="getStatusColor(item.current_status)" 
            size="small" 
            class="mr-1"
          >
            {{ getStatusIcon(item.current_status) }}
          </v-icon>
          <span>{{ formatStatus(item.current_status) }}</span>
        </div>
      </template>

      <!-- Methodology-aware actions -->
      <template v-slot:item.actions="{ item }">
        <v-btn
          icon
          size="small"
          variant="text"
          :to="{ name: 'CurationDetail', params: { id: item.id } }"
        >
          <v-icon>mdi-eye</v-icon>
          <v-tooltip activator="parent" location="top">View Details</v-tooltip>
        </v-btn>
        
        <v-btn
          v-if="canEdit(item)"
          icon
          size="small"
          variant="text"
          @click="editCuration(item)"
        >
          <v-icon>mdi-pencil</v-icon>
          <v-tooltip activator="parent" location="top">Edit</v-tooltip>
        </v-btn>
        
        <v-btn
          v-if="canRecalculateScores(item)"
          icon
          size="small"
          variant="text"
          @click="recalculateScores(item)"
        >
          <v-icon>mdi-calculator</v-icon>
          <v-tooltip activator="parent" location="top">Recalculate Scores</v-tooltip>
        </v-btn>
      </template>
    </v-data-table>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useCurationsStore } from '@/stores/curations'
import { useSchemaStore } from '@/stores/schemas'
import { useScoringStore } from '@/stores/scoring'

const authStore = useAuthStore()
const curationsStore = useCurationsStore()
const schemaStore = useSchemaStore()
const scoringStore = useScoringStore()

const selectedMethodology = ref(null)
const selectedEngine = ref(null)

// Dynamic headers based on available data
const dynamicHeaders = computed(() => {
  const baseHeaders = [
    { title: 'Gene', key: 'gene.approved_symbol', sortable: true },
    { title: 'Methodology', key: 'methodology', sortable: false }
  ]
  
  // Add disease column if any curations have disease names
  const hasDiseaseNames = curations.value.some(c => 
    c.precuration_data?.disease_name || c.curation_data?.disease_name
  )
  
  if (hasDiseaseNames) {
    baseHeaders.push({ title: 'Disease', key: 'disease_name', sortable: true })
  }
  
  baseHeaders.push(
    { title: 'Verdict', key: 'computed_verdict', sortable: true },
    { title: 'Scores', key: 'scores', sortable: false },
    { title: 'Status', key: 'current_status', sortable: true },
    { title: 'Created', key: 'created_at', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false }
  )
  
  return baseHeaders
})

const availableMethodologies = computed(() => {
  const methodologies = new Set()
  curations.value.forEach(curation => {
    if (curation.workflow_pair?.name) {
      methodologies.add(curation.workflow_pair.name)
    }
  })
  return Array.from(methodologies)
})

const availableEngines = computed(() => {
  return scoringStore.availableEngines || []
})

const canEdit = (curation) => {
  return authStore.isAdmin || 
         (authStore.isCurator && curation.current_status === 'Draft' && curation.created_by === authStore.user.id)
}

const canRecalculateScores = (curation) => {
  return authStore.isCurator || authStore.isAdmin
}

const recalculateScores = async (curation) => {
  try {
    await curationsStore.recalculateScores(curation.id)
    showSuccess('Scores recalculated successfully')
  } catch (error) {
    showError('Failed to recalculate scores')
  }
}

const filterByMethodology = () => {
  const filters = {}
  
  if (selectedMethodology.value) {
    // Find workflow pair ID for the selected methodology
    const workflowPair = schemaStore.workflowPairs.find(wp => wp.name === selectedMethodology.value)
    if (workflowPair) {
      filters.workflow_pair_id = workflowPair.id
    }
  }
  
  if (selectedEngine.value) {
    filters.scoring_engine = selectedEngine.value
  }
  
  curationsStore.fetchCurations(filters)
}

const getVerdictColor = (verdict, scoringEngine) => {
  // Methodology-specific color mapping
  const colorMaps = {
    'clingen_sop_v11': {
      'Definitive': 'success',
      'Strong': 'info',
      'Moderate': 'warning',
      'Limited': 'orange',
      'No Known Disease Relationship': 'grey',
      'Disputed': 'error',
      'Refuted': 'error'
    },
    'gencc_based': {
      'Definitive': 'success',
      'Strong': 'info',
      'Moderate': 'warning',
      'Limited': 'orange'
    },
    'qualitative_assessment': {
      'Strong Association': 'success',
      'Moderate Association': 'warning',
      'Weak Association': 'orange',
      'Insufficient Evidence': 'grey'
    }
  }
  
  const colorMap = colorMaps[scoringEngine] || colorMaps['clingen_sop_v11']
  return colorMap[verdict] || 'grey'
}

const formatTotalScore = (scores) => {
  if (!scores || typeof scores !== 'object') return 'N/A'
  
  const totalScore = scores.total_score || 0
  
  // Try to determine max score from the scores object
  if (scores.genetic_evidence_score !== undefined && scores.experimental_evidence_score !== undefined) {
    // ClinGen-style scoring
    return `${totalScore}/18`
  }
  
  return totalScore.toString()
}

const getScoreProgress = (scores, workflowPair) => {
  if (!scores || !workflowPair) return 0
  
  const totalScore = scores.total_score || 0
  const scoringConfig = workflowPair.curation_schema?.scoring_configuration
  
  if (scoringConfig?.max_total_score) {
    return Math.min((totalScore / scoringConfig.max_total_score) * 100, 100)
  }
  
  // Default assumption for ClinGen
  if (scores.genetic_evidence_score !== undefined) {
    return Math.min((totalScore / 18) * 100, 100)
  }
  
  return 0
}

const getScoreColor = (scores, workflowPair) => {
  if (!scores) return 'grey'
  
  const progress = getScoreProgress(scores, workflowPair)
  
  if (progress >= 75) return 'success'
  if (progress >= 50) return 'info'
  if (progress >= 25) return 'warning'
  return 'grey'
}

const getStatusColor = (status) => {
  const colors = {
    'Draft': 'grey',
    'In_Primary_Review': 'info',
    'In_Secondary_Review': 'warning',
    'Internal_Review': 'info',
    'Final_Review': 'warning',
    'Approved': 'success',
    'Published': 'success',
    'Rejected': 'error'
  }
  return colors[status] || 'grey'
}

const getStatusIcon = (status) => {
  const icons = {
    'Draft': 'mdi-file-document-outline',
    'In_Primary_Review': 'mdi-account-search',
    'In_Secondary_Review': 'mdi-account-multiple-check',
    'Internal_Review': 'mdi-account-search',
    'Final_Review': 'mdi-account-multiple-check',
    'Approved': 'mdi-check-circle',
    'Published': 'mdi-publish',
    'Rejected': 'mdi-close-circle'
  }
  return icons[status] || 'mdi-help-circle'
}

const formatStatus = (status) => {
  return status.replace(/_/g, ' ')
}

const getDiseaseNameFromCuration = (curation) => {
  return curation.precuration_data?.disease_name || 
         curation.curation_data?.disease_name || 
         'Unknown Disease'
}
</script>
```

### Form Validation Patterns

```vue
<template>
  <v-form ref="formRef" @submit.prevent="handleSubmit">
    <v-text-field
      v-model="formData.mondo_id"
      label="MONDO ID *"
      :rules="mondoIdRules"
      :error-messages="fieldErrors.mondo_id"
      @input="clearFieldError('mondo_id')"
    />
    
    <v-textarea
      v-model="formData.rationale"
      label="Rationale *"
      :rules="rationaleRules"
      :counter="500"
      :error-messages="fieldErrors.rationale"
      @input="clearFieldError('rationale')"
    />
    
    <v-btn type="submit" :loading="submitting">Submit</v-btn>
  </v-form>
</template>

<script setup>
import { ref, reactive } from 'vue'

const formRef = ref(null)
const submitting = ref(false)
const fieldErrors = reactive({})

const formData = reactive({
  mondo_id: '',
  rationale: ''
})

// Validation rules
const mondoIdRules = [
  v => !!v || 'MONDO ID is required',
  v => /^MONDO:\d+$/.test(v) || 'Invalid MONDO ID format'
]

const rationaleRules = [
  v => !!v || 'Rationale is required',
  v => v.length >= 50 || 'Rationale must be at least 50 characters',
  v => v.length <= 500 || 'Rationale must not exceed 500 characters'
]

const clearFieldError = (field) => {
  if (fieldErrors[field]) {
    delete fieldErrors[field]
  }
}

const handleSubmit = async () => {
  const validation = await formRef.value.validate()
  if (!validation.valid) {
    return
  }

  submitting.value = true
  
  try {
    await submitForm(formData)
    emit('success')
  } catch (error) {
    // Handle API validation errors
    if (error.response?.data?.detail && Array.isArray(error.response.data.detail)) {
      error.response.data.detail.forEach(err => {
        if (err.loc && err.loc.length > 1) {
          const field = err.loc[err.loc.length - 1]
          fieldErrors[field] = [err.msg]
        }
      })
    }
  } finally {
    submitting.value = false
  }
}
</script>
```

## Routing and Navigation

### Scope-Based Router Configuration

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/scopes',
    name: 'ScopeManagement',
    component: () => import('@/views/ScopeManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/scope/:scopeId/genes',
    name: 'ScopedGenes',
    component: () => import('@/views/GenesTable.vue'),
    meta: { requiresAuth: true, requiresScopeAccess: true }
  },
  {
    path: '/scope/:scopeId/genes/:geneId',
    name: 'ScopedGeneDetail',
    component: () => import('@/views/GeneDetail.vue'),
    meta: { requiresAuth: true, requiresScopeAccess: true }
  },
  {
    path: '/scope/:scopeId/workflow/:geneId',
    name: 'MultiStageWorkflow',
    component: () => import('@/views/WorkflowDetail.vue'),
    meta: { requiresAuth: true, requiresScopeAccess: true }
  },
  {
    path: '/scope/:scopeId/precurations',
    name: 'ScopedPrecurations',
    component: () => import('@/views/PrecurationsTable.vue'),
    meta: { requiresAuth: true, requiresScopeAccess: true }
  },
  {
    path: '/scope/:scopeId/curations',
    name: 'ScopedCurations',
    component: () => import('@/views/CurationsTable.vue'),
    meta: { requiresAuth: true, requiresScopeAccess: true }
  },
  {
    path: '/scope/:scopeId/curations/:curationId',
    name: 'ScopedCurationDetail',
    component: () => import('@/views/CurationDetail.vue'),
    meta: { requiresAuth: true, requiresScopeAccess: true }
  },
  {
    path: '/reviews',
    name: 'ReviewDashboard',
    component: () => import('@/views/ReviewDashboard.vue'),
    meta: { requiresAuth: true, requiresCurator: true }
  },
  {
    path: '/reviews/:reviewId',
    name: 'ReviewDetail',
    component: () => import('@/views/ReviewDetail.vue'),
    meta: { requiresAuth: true, requiresCurator: true }
  },
  {
    path: '/active-curations',
    name: 'ActiveCurations',
    component: () => import('@/views/ActiveCurations.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/users',
    name: 'UserManagement',
    component: () => import('@/views/UserManagement.vue'),
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { guest: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Enhanced navigation guards with scope-based access control
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const scopesStore = useScopesStore()
  
  // Initialize stores if needed
  if (!authStore.initialized) {
    await authStore.initialize()
  }
  
  if (!scopesStore.scopes.length && authStore.isAuthenticated) {
    await scopesStore.fetchScopes()
  }
  
  // Redirect authenticated users away from guest pages
  if (to.meta.guest && authStore.isAuthenticated) {
    return next({ name: 'Dashboard' })
  }
  
  // Require authentication
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return next({ name: 'Login', query: { redirect: to.fullPath } })
  }
  
  // Require curator role
  if (to.meta.requiresCurator && !authStore.isCurator && !authStore.isAdmin) {
    return next({ name: 'NotAuthorized' })
  }
  
  // Require admin role
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return next({ name: 'NotAuthorized' })
  }
  
  // Scope-based access control
  if (to.meta.requiresScopeAccess && to.params.scopeId) {
    const scopeId = to.params.scopeId
    const userScopes = authStore.user?.assigned_scopes || []
    
    // Admin can access all scopes
    if (!authStore.isAdmin && !userScopes.includes(scopeId)) {
      return next({ name: 'NotAuthorized' })
    }
    
    // Set active scope if accessing scoped route
    const scope = scopesStore.getScopeById(scopeId)
    if (scope) {
      scopesStore.setActiveScope(scope)
    }
  }
  
  next()
})

export default router
```

### Scope-Based Navigation Component

```vue
<template>
  <v-app-bar color="primary" dark>
    <v-app-bar-title>
      <router-link to="/" class="text-decoration-none text-white">
        Gene Curator
      </router-link>
    </v-app-bar-title>

    <!-- Scope Selector -->
    <template v-if="isAuthenticated">
      <v-select
        v-model="selectedScope"
        :items="userScopes"
        item-title="display_name"
        item-value="id"
        label="Clinical Specialty"
        density="compact"
        variant="outlined"
        class="mx-4"
        style="max-width: 200px;"
        @update:model-value="handleScopeChange"
      >
        <template v-slot:selection="{ item }">
          <v-chip color="white" text-color="primary" size="small">
            {{ item.title }}
          </v-chip>
        </template>
      </v-select>
    </template>

    <v-spacer />

    <template v-if="isAuthenticated && activeScope">
      <!-- Scope-based navigation menu -->
      <v-btn 
        variant="text" 
        :to="{ name: 'ScopedGenes', params: { scopeId: activeScope.id } }"
      >
        <v-icon start>mdi-dna</v-icon>
        Genes
      </v-btn>
      
      <v-btn 
        variant="text" 
        :to="{ name: 'ScopedPrecurations', params: { scopeId: activeScope.id } }"
      >
        <v-icon start>mdi-clipboard-text</v-icon>
        Precurations
      </v-btn>
      
      <v-btn 
        variant="text" 
        :to="{ name: 'ScopedCurations', params: { scopeId: activeScope.id } }"
      >
        <v-icon start>mdi-file-document</v-icon>
        Curations
      </v-btn>
      
      <v-btn 
        variant="text" 
        :to="{ name: 'ReviewDashboard' }"
        v-if="isCurator || isAdmin"
      >
        <v-icon start>mdi-account-multiple-check</v-icon>
        Reviews
        <v-badge 
          v-if="pendingReviewCount > 0"
          :content="pendingReviewCount"
          color="error"
          inline
        />
      </v-btn>
      
      <v-btn 
        variant="text" 
        :to="{ name: 'ActiveCurations' }"
      >
        <v-icon start>mdi-star</v-icon>
        Active
      </v-btn>

      <!-- Admin menu -->
      <v-menu v-if="isAdmin">
        <template v-slot:activator="{ props }">
          <v-btn variant="text" v-bind="props">
            <v-icon start>mdi-cog</v-icon>
            Admin
            <v-icon end>mdi-chevron-down</v-icon>
          </v-btn>
        </template>
        
        <v-list>
          <v-list-item :to="{ name: 'ScopeManagement' }">
            <v-list-item-title>Scope Management</v-list-item-title>
          </v-list-item>
          <v-list-item :to="{ name: 'UserManagement' }">
            <v-list-item-title>User Management</v-list-item-title>
          </v-list-item>
          <v-list-item>
            <v-list-item-title>Schema Management</v-list-item-title>
          </v-list-item>
          <v-list-item>
            <v-list-item-title>System Settings</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>

      <!-- User menu -->
      <v-menu>
        <template v-slot:activator="{ props }">
          <v-btn variant="text" v-bind="props">
            <v-avatar size="32" class="mr-2">
              <v-icon>mdi-account</v-icon>
            </v-avatar>
            {{ user.name }}
            <v-icon end>mdi-chevron-down</v-icon>
          </v-btn>
        </template>
        
        <v-list>
          <v-list-item :to="{ name: 'UserProfile' }">
            <v-list-item-title>Profile</v-list-item-title>
          </v-list-item>
          <v-list-item @click="logout">
            <v-list-item-title>Logout</v-list-item-title>
          </v-list-item>
        </v-list>
      </v-menu>
    </template>

    <!-- Guest navigation -->
    <template v-else>
      <v-btn variant="text" :to="{ name: 'Login' }">
        Login
      </v-btn>
    </template>
  </v-app-bar>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useScopesStore } from '@/stores/scopes'
import { useReviewsStore } from '@/stores/reviews'

const router = useRouter()
const authStore = useAuthStore()
const scopesStore = useScopesStore()
const reviewsStore = useReviewsStore()

const selectedScope = ref(null)

const isAuthenticated = computed(() => authStore.isAuthenticated)
const isAdmin = computed(() => authStore.isAdmin)
const isCurator = computed(() => authStore.isCurator)
const user = computed(() => authStore.user)
const activeScope = computed(() => scopesStore.activeScope)
const userScopes = computed(() => scopesStore.getUserScopes(authStore.user?.id))
const pendingReviewCount = computed(() => reviewsStore.myPendingReviews.length)

// Initialize selected scope
if (activeScope.value) {
  selectedScope.value = activeScope.value.id
}

const handleScopeChange = (scopeId) => {
  const scope = userScopes.value.find(s => s.id === scopeId)
  if (scope) {
    scopesStore.setActiveScope(scope)
    // Navigate to scoped dashboard or current page with new scope
    if (router.currentRoute.value.params.scopeId) {
      router.push({ 
        ...router.currentRoute.value, 
        params: { ...router.currentRoute.value.params, scopeId: scope.id } 
      })
    }
  }
}

const logout = async () => {
  await authStore.logout()
  router.push({ name: 'Login' })
}
</script>
```

## Development Workflow

### Local Development Setup

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run linting
npm run lint

# Run tests
npm run test

# Build for production
npm run build
```

### Code Quality Tools

**ESLint Configuration** (`.eslintrc.js`):
```javascript
module.exports = {
  env: {
    node: true,
  },
  extends: [
    'eslint:recommended',
    '@vue/eslint-config-typescript',
    'plugin:vue/vue3-recommended',
  ],
  parserOptions: {
    ecmaVersion: 'latest',
  },
  rules: {
    'vue/multi-word-component-names': 'off',
    'vue/no-unused-vars': 'error',
    'vue/no-mutating-props': 'error',
    '@typescript-eslint/no-unused-vars': 'error',
  },
}
```

**Prettier Configuration** (`.prettierrc`):
```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "vueIndentScriptAndStyle": true
}
```

### Testing Strategy

**Component Testing with Vitest**:
```javascript
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import PrecurationForm from '@/components/clingen/PrecurationForm.vue'

describe('PrecurationForm', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('validates MONDO ID format', async () => {
    const wrapper = mount(PrecurationForm, {
      props: {
        precuration: null
      }
    })

    const mondoField = wrapper.find('[data-testid="mondo-id-field"]')
    await mondoField.setValue('INVALID')
    
    const form = wrapper.find('form')
    await form.trigger('submit')
    
    expect(wrapper.text()).toContain('Invalid MONDO ID format')
  })

  it('emits submit event with valid data', async () => {
    const wrapper = mount(PrecurationForm)
    
    // Fill form with valid data
    await wrapper.find('[data-testid="mondo-id-field"]').setValue('MONDO:0002113')
    await wrapper.find('[data-testid="rationale-field"]').setValue('This is a valid rationale with sufficient length to pass validation rules.')
    
    const form = wrapper.find('form')
    await form.trigger('submit')
    
    expect(wrapper.emitted('submit')).toBeTruthy()
    expect(wrapper.emitted('submit')[0][0]).toMatchObject({
      mondo_id: 'MONDO:0002113',
      rationale: expect.any(String)
    })
  })
})
```

### Performance Optimization

**Lazy Loading Routes**:
```javascript
const routes = [
  {
    path: '/curations/:id',
    name: 'CurationDetail',
    component: () => import(/* webpackChunkName: "curation-detail" */ '@/views/CurationDetail.vue')
  }
]
```

**Component Lazy Loading**:
```vue
<script setup>
import { defineAsyncComponent } from 'vue'

const ClinGenScoreCard = defineAsyncComponent(() =>
  import('@/components/clingen/ClinGenScoreCard.vue')
)
</script>
```

**Virtual Scrolling for Large Lists**:
```vue
<template>
  <v-virtual-scroll
    :items="curations"
    :item-height="64"
    height="400"
  >
    <template v-slot:default="{ item }">
      <CurationListItem :curation="item" />
    </template>
  </v-virtual-scroll>
</template>
```

---

---

## Summary

This frontend development guide describes a comprehensive **scope-based, multi-stage workflow system** that:

- **Organizes curation work by clinical specialties** (kidney-genetics, cardio-genetics, etc.)
- **Implements 5-stage workflow management** (Entry → Precuration → Curation → Review → Active)
- **Enforces 4-eyes principle quality assurance** with mandatory independent review
- **Supports multiple curations per gene-scope** with active/archived status management
- **Provides schema-agnostic flexibility** adapting to any scientific methodology
- **Enables real-time collaboration** with auto-save and draft management
- **Maintains complete audit trails** throughout all workflow stages

The frontend architecture transforms gene-disease curation from a single-methodology interface into a universal platform that can serve any clinical specialty using any scientific approach, while maintaining the highest standards of user experience and quality assurance.

## Related Documentation

- [Architecture](./ARCHITECTURE.md) - Scope-based system design and schema-agnostic architecture
- [API Reference](./API_REFERENCE.md) - Multi-stage workflow API endpoints and scope-based filtering
- [Database Schema](./DATABASE_SCHEMA.md) - Multi-curation data structure with scope organization
- [Workflow Documentation](./WORKFLOW.md) - 5-stage business process flows with 4-eyes principle
- [Scoring Engine Guide](../plan/SCORING_ENGINE_GUIDE.md) - Pluggable scoring system integration