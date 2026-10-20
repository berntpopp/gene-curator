<template>
  <v-container fluid>
    <!-- Page Header -->
    <div class="d-flex align-center mb-6">
      <div>
        <h1 class="text-h4 font-weight-bold">Validation Dashboard</h1>
        <p class="text-body-1 text-medium-emphasis mt-1">
          Validation results collected in this session. The API provides no aggregate validation
          statistics, so the figures below are derived from these results.
        </p>
      </div>
    </div>

    <!-- Summary Cards -->
    <v-row class="mb-6">
      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="success" class="mb-2">mdi-check-circle</v-icon>
            <div class="text-h4 font-weight-bold text-success">{{ stats.valid }}</div>
            <div class="text-body-2 text-medium-emphasis">Valid</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="error" class="mb-2">mdi-alert-circle</v-icon>
            <div class="text-h4 font-weight-bold text-error">{{ stats.invalid }}</div>
            <div class="text-body-2 text-medium-emphasis">Invalid</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="warning" class="mb-2">mdi-alert</v-icon>
            <div class="text-h4 font-weight-bold text-warning">{{ stats.withWarnings }}</div>
            <div class="text-body-2 text-medium-emphasis">With warnings</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" md="3">
        <v-card>
          <v-card-text class="text-center">
            <v-icon size="48" color="info" class="mb-2">mdi-chart-line</v-icon>
            <div class="text-h4 font-weight-bold text-info">{{ stats.complianceRate }}%</div>
            <div class="text-body-2 text-medium-emphasis">Compliance Rate</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Filters -->
    <v-card class="mb-6">
      <v-card-text>
        <v-row>
          <v-col cols="12" sm="6">
            <v-select
              v-model="selectedStatus"
              :items="validationStatuses"
              label="Validation Status"
              variant="outlined"
              density="compact"
              hide-details
              clearable
            />
          </v-col>
          <v-col cols="12" sm="6">
            <v-select
              v-model="selectedSeverity"
              :items="severityLevels"
              label="Issue Severity"
              variant="outlined"
              density="compact"
              hide-details
              clearable
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
        item-value="id"
        :items-per-page="25"
      >
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
          <div class="d-flex flex-column ga-1">
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

        <template #item.actions="{ item }">
          <v-btn
            aria-label="View validation details"
            icon="mdi-eye"
            size="small"
            variant="text"
            @click="viewValidationDetails(item)"
          />
        </template>
      </v-data-table>
    </v-card>

    <!-- Common Issues -->
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

    <!-- Validation Detail Dialog -->
    <v-dialog v-model="detailDialog" max-width="800">
      <v-card v-if="selectedValidation">
        <v-card-title class="d-flex align-center">
          <v-icon start>mdi-clipboard-check</v-icon>
          Validation Details
        </v-card-title>
        <v-card-text>
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
                <v-list-item-subtitle v-if="issue.field_path">
                  Field: {{ issue.field_path }}
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
            <div class="text-body-2">This result passes all validation rules</div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="outlined" @click="detailDialog = false">Close</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
  import { ref, computed } from 'vue'
  import { useValidationStore } from '@/stores'
  import {
    getValidationStatusColor,
    getValidationStatusIcon,
    getSeverityColor,
    formatValidationStatus
  } from './validationDashboardHelpers'

  interface ValidationIssue {
    id: string
    message: string
    severity: string
    field_path?: string
  }

  interface ValidationRow {
    id: string
    validation_status: string
    issues: ValidationIssue[]
  }

  const validationStore = useValidationStore()

  const detailDialog = ref(false)
  const selectedValidation = ref<ValidationRow | null>(null)
  const selectedStatus = ref<string | null>(null)
  const selectedSeverity = ref<string | null>(null)

  const validationHeaders = [
    { title: 'Result', key: 'id', sortable: true },
    { title: 'Status', key: 'status', sortable: false },
    { title: 'Issues', key: 'issues', sortable: false },
    { title: 'Actions', key: 'actions', sortable: false }
  ]

  const validationStatuses = [
    { title: 'Valid', value: 'valid' },
    { title: 'Invalid', value: 'invalid' }
  ]

  const severityLevels = [
    { title: 'Error', value: 'error' },
    { title: 'Warning', value: 'warning' }
  ]

  const toIssues = (
    id: string,
    entries: Record<string, unknown>[],
    severity: string
  ): ValidationIssue[] =>
    entries.map((entry, i) => ({
      id: `${id}-${severity}-${i}`,
      severity,
      message: String(entry.message ?? entry.error ?? JSON.stringify(entry)),
      field_path: typeof entry.field === 'string' ? entry.field : undefined
    }))

  const validationResults = computed((): ValidationRow[] =>
    Object.entries(validationStore.validationResults).map(([id, r]) => ({
      id,
      validation_status: r.is_valid ? 'valid' : 'invalid',
      issues: [...toIssues(id, r.errors, 'error'), ...toIssues(id, r.warnings, 'warning')]
    }))
  )

  const stats = computed(() => {
    const rows = validationResults.value
    const valid = rows.filter(r => r.validation_status === 'valid').length
    return {
      valid,
      invalid: rows.length - valid,
      withWarnings: rows.filter(r => r.issues.some(i => i.severity === 'warning')).length,
      complianceRate: rows.length ? Math.round((valid / rows.length) * 100) : 0
    }
  })

  const commonIssues = computed(() => {
    const counts = new Map<string, { message: string; severity: string; count: number }>()
    for (const issue of validationResults.value.flatMap(r => r.issues)) {
      const key = `${issue.severity}:${issue.message}`
      const entry = counts.get(key) ?? {
        message: issue.message,
        severity: issue.severity,
        count: 0
      }
      entry.count++
      counts.set(key, entry)
    }
    return [...counts.entries()]
      .map(([type, e]) => ({ type, ...e }))
      .sort((x, y) => y.count - x.count)
      .slice(0, 5)
  })

  const filteredResults = computed(() =>
    validationResults.value.filter(
      r =>
        (!selectedStatus.value || r.validation_status === selectedStatus.value) &&
        (!selectedSeverity.value || r.issues.some(i => i.severity === selectedSeverity.value))
    )
  )

  const viewValidationDetails = (validation: ValidationRow) => {
    selectedValidation.value = validation
    detailDialog.value = true
  }
</script>

<style scoped>
  .border {
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }

  .v-data-table {
    border-radius: 8px;
  }
</style>
