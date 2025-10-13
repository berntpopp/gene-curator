<template>
  <v-container fluid>
    <!-- Page Header -->
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="text-h4 font-weight-bold">Validation Dashboard</h1>
        <p class="text-body-1 text-medium-emphasis mt-1">
          Monitor validation results and schema compliance across curations
        </p>
      </div>
      <v-spacer />
      <v-btn color="primary" variant="outlined" :loading="refreshing" @click="refreshAll">
        <v-icon start>mdi-refresh</v-icon>
        Refresh All
      </v-btn>
    </div>

    <!-- Summary Cards -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="success" class="mb-2">mdi-check-circle</v-icon>
            <div class="text-h4 font-weight-bold text-success">
              {{ stats.valid_curations || 0 }}
            </div>
            <div class="text-body-2 text-medium-emphasis">Valid Curations</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="error" class="mb-2">mdi-alert-circle</v-icon>
            <div class="text-h4 font-weight-bold text-error">
              {{ stats.invalid_curations || 0 }}
            </div>
            <div class="text-body-2 text-medium-emphasis">Invalid Curations</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="warning" class="mb-2">mdi-alert</v-icon>
            <div class="text-h4 font-weight-bold text-warning">{{ stats.warnings_count || 0 }}</div>
            <div class="text-body-2 text-medium-emphasis">Warnings</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="info" class="mb-2">mdi-chart-line</v-icon>
            <div class="text-h4 font-weight-bold text-info">
              {{ stats.schema_compliance_rate || 0 }}%
            </div>
            <div class="text-body-2 text-medium-emphasis">Compliance Rate</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-card class="mb-6">
      <v-card-text>
        <v-row>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="selectedScope"
              :items="availableScopes"
              item-title="display_name"
              item-value="id"
              label="Filter by Scope"
              variant="outlined"
              density="compact"
              hide-details
              clearable
              @update:model-value="applyFilters"
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="selectedSchema"
              :items="availableSchemas"
              item-title="name"
              item-value="id"
              label="Filter by Schema"
              variant="outlined"
              density="compact"
              hide-details
              clearable
              @update:model-value="applyFilters"
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="selectedStatus"
              :items="validationStatuses"
              label="Validation Status"
              variant="outlined"
              density="compact"
              hide-details
              clearable
              @update:model-value="applyFilters"
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="selectedSeverity"
              :items="severityLevels"
              label="Issue Severity"
              variant="outlined"
              density="compact"
              hide-details
              clearable
              @update:model-value="applyFilters"
            />
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- Validation Results Table -->
    <v-card class="mb-6">
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-clipboard-check</v-icon>
        Validation Results ({{ filteredResults.length }})
      </v-card-title>

      <v-data-table
        :headers="validationHeaders"
        :items="filteredResults"
        :loading="loading"
        item-value="id"
        :items-per-page="25"
      >
        <template #item.entity="{ item }">
          <div>
            <div class="font-weight-medium">{{ item.gene_symbol }} - {{ item.disease_name }}</div>
            <div class="text-caption">{{ item.entity_type }} • {{ item.scope_name }}</div>
          </div>
        </template>

        <template #item.schema="{ item }">
          <div>
            <div class="text-body-2">{{ item.schema_name }}</div>
            <div class="text-caption">v{{ item.schema_version }}</div>
          </div>
        </template>

        <template #item.status="{ item }">
          <v-chip
            :color="getValidationStatusColor(item.validation_status)"
            size="small"
            variant="flat"
          >
            <v-icon start size="small">{{
              getValidationStatusIcon(item.validation_status)
            }}</v-icon>
            {{ formatValidationStatus(item.validation_status) }}
          </v-chip>
        </template>

        <template #item.issues="{ item }">
          <div class="d-flex flex-column gap-1">
            <v-chip
              v-for="issue in item.issues.slice(0, 2)"
              :key="issue.id"
              :color="getSeverityColor(issue.severity)"
              size="x-small"
              variant="outlined"
            >
              {{ issue.message }}
            </v-chip>
            <v-chip v-if="item.issues.length > 2" size="x-small" variant="outlined" color="grey">
              +{{ item.issues.length - 2 }} more
            </v-chip>
          </div>
        </template>

        <template #item.last_validated="{ item }">
          <div>
            <div class="text-body-2">{{ formatDate(item.last_validated) }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ getTimeAgo(item.last_validated) }}
            </div>
          </div>
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex gap-1">
            <v-btn
              icon="mdi-eye"
              size="small"
              variant="text"
              @click="viewValidationDetails(item)"
            />
            <v-btn
              icon="mdi-refresh"
              size="small"
              variant="text"
              :loading="revalidating[item.id]"
              @click="revalidateEntity(item)"
            />
            <v-btn icon="mdi-file-document" size="small" variant="text" @click="viewEntity(item)" />
          </div>
        </template>
      </v-data-table>
    </v-card>

    <!-- Schema Compliance Chart -->
    <v-row>
      <v-col cols="12" lg="8">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-chart-bar</v-icon>
            Schema Compliance Overview
          </v-card-title>
          <v-card-text>
            <div class="text-center py-8 text-medium-emphasis">
              <v-icon size="64" class="mb-4">mdi-chart-bar</v-icon>
              <div class="text-body-1">Compliance chart would be implemented here</div>
              <div class="text-body-2">Showing validation trends over time</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" lg="4">
        <v-card>
          <v-card-title class="d-flex align-center">
            <v-icon start>mdi-alert-octagon</v-icon>
            Common Issues
          </v-card-title>
          <v-card-text>
            <v-list density="compact">
              <v-list-item v-for="issue in commonIssues" :key="issue.type">
                <template #prepend>
                  <v-icon :color="getSeverityColor(issue.severity)" size="small">
                    mdi-alert-circle
                  </v-icon>
                </template>

                <v-list-item-title>{{ issue.message }}</v-list-item-title>
                <v-list-item-subtitle>{{ issue.count }} occurrences</v-list-item-subtitle>

                <template #append>
                  <v-chip :color="getSeverityColor(issue.severity)" size="small" variant="outlined">
                    {{ issue.severity }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Validation Detail Dialog -->
    <v-dialog v-model="detailDialog" max-width="800">
      <v-card v-if="selectedValidation">
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-clipboard-check</v-icon>
          Validation Details
        </v-card-title>
        <v-card-text>
          <div class="mb-4">
            <h3 class="text-h6 mb-2">
              {{ selectedValidation.gene_symbol }} - {{ selectedValidation.disease_name }}
            </h3>
            <div class="text-body-2 text-medium-emphasis">
              Schema: {{ selectedValidation.schema_name }} v{{ selectedValidation.schema_version }}
            </div>
          </div>

          <v-divider class="my-4" />

          <div v-if="selectedValidation.issues.length">
            <h4 class="text-subtitle-1 mb-3">
              Validation Issues ({{ selectedValidation.issues.length }})
            </h4>
            <v-list>
              <v-list-item
                v-for="issue in selectedValidation.issues"
                :key="issue.id"
                class="mb-2 border rounded"
              >
                <template #prepend>
                  <v-icon :color="getSeverityColor(issue.severity)"> mdi-alert-circle </v-icon>
                </template>

                <v-list-item-title>{{ issue.message }}</v-list-item-title>
                <v-list-item-subtitle>
                  Field: {{ issue.field_path }} • {{ issue.rule_type }}
                </v-list-item-subtitle>

                <template #append>
                  <v-chip :color="getSeverityColor(issue.severity)" size="small" variant="flat">
                    {{ issue.severity }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </div>

          <div v-else class="text-center py-4 text-success">
            <v-icon size="64" color="success" class="mb-2">mdi-check-circle</v-icon>
            <div class="text-h6">No Issues Found</div>
            <div class="text-body-2">This entity passes all validation rules</div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" @click="detailDialog = false">Close</v-btn>
          <v-btn color="primary" variant="flat" @click="revalidateEntity(selectedValidation)">
            Re-validate
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup>
  import { ref, computed, onMounted, onErrorCaptured } from 'vue'
  import { useRouter } from 'vue-router'
  import { useValidationStore, useScopesStore, useSchemasStore } from '@/stores'
  import { useLogger } from '@/composables/useLogger'
  import { showError, showSuccess } from '@/composables/useNotifications'

  const router = useRouter()
  const validationStore = useValidationStore()
  const scopesStore = useScopesStore()
  const schemasStore = useSchemasStore()
  const logger = useLogger()

  const loading = ref(false)
  const refreshing = ref(false)
  const revalidating = ref({})
  const detailDialog = ref(false)
  const selectedValidation = ref(null)

  // Filters
  const selectedScope = ref(null)
  const selectedSchema = ref(null)
  const selectedStatus = ref(null)
  const selectedSeverity = ref(null)

  const validationHeaders = [
    { title: 'Entity', key: 'entity', sortable: true },
    { title: 'Schema', key: 'schema', sortable: true },
    { title: 'Status', key: 'status', sortable: true },
    { title: 'Issues', key: 'issues', sortable: false },
    { title: 'Last Validated', key: 'last_validated', sortable: true },
    { title: 'Actions', key: 'actions', sortable: false }
  ]

  const validationStatuses = [
    { title: 'Valid', value: 'valid' },
    { title: 'Invalid', value: 'invalid' },
    { title: 'Warning', value: 'warning' },
    { title: 'Pending', value: 'pending' }
  ]

  const severityLevels = [
    { title: 'Error', value: 'error' },
    { title: 'Warning', value: 'warning' },
    { title: 'Info', value: 'info' }
  ]

  // Computed properties with defensive defaults
  const stats = computed(
    () =>
      validationStore.validationStats || {
        valid_curations: 0,
        invalid_curations: 0,
        warnings_count: 0,
        schema_compliance_rate: 0
      }
  )

  const validationResults = computed(() => {
    // validationStore.validationResults is an object, not array
    // Convert to array for data table
    const results = validationStore.validationResults
    if (!results || typeof results !== 'object') return []

    // If it's already an array, return it
    if (Array.isArray(results)) return results

    // If it's an object with values, convert to array
    return Object.values(results).filter(v => v && typeof v === 'object')
  })

  const commonIssues = computed(() => validationStore.commonIssues || [])
  const availableScopes = computed(() => scopesStore.scopes || [])
  const availableSchemas = computed(() => schemasStore.schemas || [])

  const filteredResults = computed(() => {
    // Defensive: ensure validationResults is always an array
    let filtered = Array.isArray(validationResults.value) ? [...validationResults.value] : []

    if (selectedScope.value) {
      filtered = filtered.filter(r => r.scope_id === selectedScope.value)
    }

    if (selectedSchema.value) {
      filtered = filtered.filter(r => r.schema_id === selectedSchema.value)
    }

    if (selectedStatus.value) {
      filtered = filtered.filter(r => r.validation_status === selectedStatus.value)
    }

    if (selectedSeverity.value) {
      filtered = filtered.filter(
        r =>
          r.issues &&
          Array.isArray(r.issues) &&
          r.issues.some(issue => issue.severity === selectedSeverity.value)
      )
    }

    return filtered
  })

  // Error boundary for component-level errors
  onErrorCaptured((err, instance, info) => {
    logger.error('Component error caught', {
      error: err.message,
      stack: err.stack,
      component: instance?.$options?.name || 'ValidationDashboard',
      errorInfo: info
    })

    showError('An error occurred while rendering the dashboard')

    // Don't propagate error up - handle it here
    return false
  })

  // Helper functions
  const getValidationStatusColor = status => {
    const colorMap = {
      valid: 'success',
      invalid: 'error',
      warning: 'warning',
      pending: 'info'
    }
    return colorMap[status] || 'grey'
  }

  const getValidationStatusIcon = status => {
    const iconMap = {
      valid: 'mdi-check',
      invalid: 'mdi-close',
      warning: 'mdi-alert',
      pending: 'mdi-clock'
    }
    return iconMap[status] || 'mdi-help'
  }

  const getSeverityColor = severity => {
    const colorMap = {
      error: 'error',
      warning: 'warning',
      info: 'info'
    }
    return colorMap[severity] || 'grey'
  }

  const formatValidationStatus = status => {
    return status.charAt(0).toUpperCase() + status.slice(1)
  }

  const formatDate = dateString => {
    return new Date(dateString).toLocaleDateString()
  }

  const getTimeAgo = dateString => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return 'Over a week ago'
  }

  // Actions
  const applyFilters = () => {
    // Filters are applied reactively through computed property
  }

  const refreshAll = async () => {
    refreshing.value = true
    try {
      // Call existing methods that actually exist
      await Promise.all([scopesStore.fetchScopes(), schemasStore.fetchSchemas()])

      logger.info('Validation dashboard refreshed', {
        scopeCount: scopesStore.scopes?.length || 0,
        schemaCount: schemasStore.schemas?.length || 0
      })
      showSuccess('Dashboard refreshed successfully')
    } catch (error) {
      logger.error('Failed to refresh validations', {
        error: error.message,
        stack: error.stack
      })
      showError('Failed to refresh dashboard')
    } finally {
      refreshing.value = false
    }
  }

  const viewValidationDetails = validation => {
    selectedValidation.value = validation
    detailDialog.value = true
  }

  const revalidateEntity = async validation => {
    revalidating.value[validation.id] = true
    try {
      // Use existing validation API method
      await validationStore.validateEvidence(
        validation.evidence_data,
        validation.schema_id,
        validation.id // key for storing result
      )

      logger.info('Entity revalidated', {
        entityId: validation.entity_id,
        entityType: validation.entity_type
      })
      showSuccess('Revalidation complete')
    } catch (error) {
      logger.error('Failed to revalidate entity', {
        entityId: validation.entity_id,
        error: error.message,
        stack: error.stack
      })
      showError('Revalidation failed')
    } finally {
      revalidating.value[validation.id] = false
    }
  }

  const viewEntity = validation => {
    try {
      router.push({ name: 'AssignmentDetail', params: { id: validation.entity_id } })
    } catch (error) {
      logger.error('Failed to navigate to entity', {
        entityId: validation.entity_id,
        error: error.message
      })
      showError('Failed to open entity details')
    }
  }

  onMounted(async () => {
    loading.value = true
    try {
      // Only call methods that exist in stores
      await Promise.all([scopesStore.fetchScopes(), schemasStore.fetchSchemas()])

      logger.info('ValidationDashboard mounted', {
        scopeCount: scopesStore.scopes?.length || 0,
        schemaCount: schemasStore.schemas?.length || 0
      })
    } catch (error) {
      logger.error('Failed to load validation dashboard', {
        error: error.message,
        stack: error.stack
      })
      showError('Failed to load dashboard data. Please refresh.')
    } finally {
      loading.value = false
    }
  })
</script>

<style scoped>
  .border {
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }

  .v-data-table {
    border-radius: 8px;
  }
</style>
