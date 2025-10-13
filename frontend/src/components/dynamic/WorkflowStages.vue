<template>
  <v-card>
    <v-card-title class="d-flex align-center">
      <v-icon start>mdi-workflow</v-icon>
      Multi-Stage Workflow Pipeline
    </v-card-title>

    <v-card-text>
      <div v-if="loading" class="text-center py-8">
        <v-progress-circular indeterminate color="primary" />
        <div class="mt-4">Loading workflow stages...</div>
      </div>

      <div v-else-if="workflowStages.length">
        <v-stepper
          :model-value="currentStageIndex + 1"
          :items="workflowStages"
          alt-labels
          class="mb-6"
        >
          <template #item.icon="{ item, index }">
            <v-icon
              :color="getStageColor(index)"
              :class="{ 'v-stepper-item__icon--active': index <= currentStageIndex }"
            >
              {{ getStageIcon(item.raw) }}
            </v-icon>
          </template>

          <template #item.title="{ item, index }">
            <div class="text-subtitle-2">
              {{ item.raw.name }}
              <v-chip
                v-if="index === currentStageIndex"
                size="small"
                color="primary"
                variant="flat"
                class="ml-2"
              >
                Current
              </v-chip>
            </div>
          </template>

          <template #item.subtitle="{ item }">
            <div class="text-caption text-medium-emphasis mt-1">
              {{ item.raw.description }}
            </div>
          </template>
        </v-stepper>

        <!-- Current Stage Details -->
        <v-card v-if="currentStage" variant="outlined" class="mb-6">
          <v-card-title class="d-flex align-center">
            <v-icon :color="getStageColor(currentStageIndex)" start>
              {{ getStageIcon(currentStage) }}
            </v-icon>
            {{ currentStage.name }}
            <v-spacer />
            <v-chip :color="getStageColor(currentStageIndex)" size="small" variant="flat">
              Stage {{ currentStageIndex + 1 }} of {{ workflowStages.length }}
            </v-chip>
          </v-card-title>

          <v-card-text>
            <div class="text-body-1 mb-4">{{ currentStage.description }}</div>

            <v-row>
              <v-col cols="12" sm="6">
                <div class="text-subtitle-2 mb-2">Required Roles</div>
                <div class="d-flex flex-wrap gap-2">
                  <v-chip
                    v-for="role in currentStage.required_roles"
                    :key="role"
                    size="small"
                    color="info"
                    variant="outlined"
                  >
                    {{ formatRole(role) }}
                  </v-chip>
                </div>
              </v-col>

              <v-col cols="12" sm="6">
                <div class="text-subtitle-2 mb-2">Stage Status</div>
                <v-chip :color="getStatusColor(currentStage.status)" size="large" variant="flat">
                  <v-icon start size="small">{{ getStatusIcon(currentStage.status) }}</v-icon>
                  {{ formatStatus(currentStage.status) }}
                </v-chip>
              </v-col>
            </v-row>

            <div v-if="currentStage.validation_rules?.length" class="mt-4">
              <div class="text-subtitle-2 mb-2">Validation Requirements</div>
              <v-list density="compact">
                <v-list-item
                  v-for="rule in currentStage.validation_rules"
                  :key="rule.id"
                  :prepend-icon="rule.is_satisfied ? 'mdi-check-circle' : 'mdi-circle-outline'"
                  :class="{ 'text-success': rule.is_satisfied, 'text-warning': !rule.is_satisfied }"
                >
                  <v-list-item-title>{{ rule.description }}</v-list-item-title>
                  <v-list-item-subtitle v-if="rule.error_message">
                    {{ rule.error_message }}
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </div>
          </v-card-text>
        </v-card>

        <!-- Stage Actions -->
        <v-card variant="outlined">
          <v-card-title class="text-h6">Available Actions</v-card-title>
          <v-card-text>
            <div class="d-flex flex-wrap gap-3">
              <v-btn
                v-if="canAdvanceStage"
                color="success"
                variant="flat"
                :loading="advancing"
                @click="advanceStage"
              >
                <v-icon start>mdi-arrow-right-circle</v-icon>
                Advance to {{ getNextStageName() }}
              </v-btn>

              <v-btn
                v-if="canRejectStage"
                color="error"
                variant="outlined"
                :loading="rejecting"
                @click="rejectStage"
              >
                <v-icon start>mdi-close-circle</v-icon>
                Reject & Return
              </v-btn>

              <v-btn
                v-if="canRequestRevision"
                color="warning"
                variant="outlined"
                :loading="requesting"
                @click="requestRevision"
              >
                <v-icon start>mdi-comment-edit</v-icon>
                Request Revision
              </v-btn>

              <v-btn color="secondary" variant="outlined" :loading="saving" @click="saveDraft">
                <v-icon start>mdi-content-save</v-icon>
                Save Draft
              </v-btn>
            </div>
          </v-card-text>
        </v-card>

        <!-- Stage History -->
        <v-expansion-panels v-if="stageHistory.length" class="mt-4">
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon start>mdi-history</v-icon>
              Workflow History ({{ stageHistory.length }} events)
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <v-timeline density="compact">
                <v-timeline-item
                  v-for="event in stageHistory"
                  :key="event.id"
                  :dot-color="getEventColor(event.action)"
                  size="small"
                >
                  <template #icon>
                    <v-icon size="small">{{ getEventIcon(event.action) }}</v-icon>
                  </template>

                  <div class="d-flex justify-space-between align-center mb-1">
                    <span class="font-weight-medium">{{ formatAction(event.action) }}</span>
                    <span class="text-caption text-medium-emphasis">
                      {{ formatDate(event.created_at) }}
                    </span>
                  </div>

                  <div class="text-body-2 mb-1">
                    Stage: {{ event.from_stage }} → {{ event.to_stage }}
                  </div>

                  <div class="text-caption text-medium-emphasis mb-1">
                    By: {{ event.user_name }} ({{ event.user_role }})
                  </div>

                  <div v-if="event.comment" class="text-body-2 mt-2 pa-2 bg-grey-lighten-4 rounded">
                    "{{ event.comment }}"
                  </div>
                </v-timeline-item>
              </v-timeline>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>
      </div>

      <v-alert v-else-if="error" type="error" variant="tonal">
        <template #prepend>
          <v-icon>mdi-alert-circle</v-icon>
        </template>
        Failed to load workflow stages: {{ error }}
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { useLogger } from '@/composables/useLogger'

const logger = useLogger()
  import { ref, computed, onMounted, watch } from 'vue'
  import { useWorkflowStore } from '@/stores'

  const props = defineProps({
    workflowPairId: {
      type: String,
      required: true
    },
    entityId: {
      type: String,
      required: true
    },
    entityType: {
      type: String,
      required: true,
      validator: value => ['precuration', 'curation'].includes(value)
    }
  })

  const emit = defineEmits(['stage-changed', 'action-completed'])

  const workflowStore = useWorkflowStore()
  const advancing = ref(false)
  const rejecting = ref(false)
  const requesting = ref(false)
  const saving = ref(false)

  const loading = computed(() => workflowStore.loading)
  const error = computed(() => workflowStore.error)
  const workflowStages = computed(() => workflowStore.getWorkflowStages(props.workflowPairId))
  const currentStage = computed(() => workflowStore.getCurrentStage(props.entityId))
  const stageHistory = computed(() => workflowStore.getStageHistory(props.entityId))

  const currentStageIndex = computed(() => {
    if (!currentStage.value || !workflowStages.value.length) return 0
    return workflowStages.value.findIndex(stage => stage.id === currentStage.value.stage_id)
  })

  const canAdvanceStage = computed(() => {
    return (
      currentStage.value?.can_advance && currentStageIndex.value < workflowStages.value.length - 1
    )
  })

  const canRejectStage = computed(() => {
    return currentStage.value?.can_reject && currentStageIndex.value > 0
  })

  const canRequestRevision = computed(() => {
    return currentStage.value?.can_request_revision
  })

  const getNextStageName = () => {
    const nextIndex = currentStageIndex.value + 1
    return nextIndex < workflowStages.value.length ? workflowStages.value[nextIndex].name : ''
  }

  const getStageColor = index => {
    if (index < currentStageIndex.value) return 'success'
    if (index === currentStageIndex.value) return 'primary'
    return 'grey'
  }

  const getStageIcon = stage => {
    const iconMap = {
      draft: 'mdi-file-document-edit',
      primary_review: 'mdi-account-search',
      secondary_review: 'mdi-account-check',
      approved: 'mdi-check-circle',
      published: 'mdi-publish',
      rejected: 'mdi-close-circle'
    }
    return iconMap[stage.stage_type] || 'mdi-circle'
  }

  const getStatusColor = status => {
    const colorMap = {
      pending: 'warning',
      in_progress: 'primary',
      completed: 'success',
      rejected: 'error'
    }
    return colorMap[status] || 'grey'
  }

  const getStatusIcon = status => {
    const iconMap = {
      pending: 'mdi-clock-outline',
      in_progress: 'mdi-play-circle',
      completed: 'mdi-check-circle',
      rejected: 'mdi-close-circle'
    }
    return iconMap[status] || 'mdi-help-circle'
  }

  const getEventColor = action => {
    const colorMap = {
      advanced: 'success',
      rejected: 'error',
      revision_requested: 'warning',
      draft_saved: 'info'
    }
    return colorMap[action] || 'grey'
  }

  const getEventIcon = action => {
    const iconMap = {
      advanced: 'mdi-arrow-right-circle',
      rejected: 'mdi-close-circle',
      revision_requested: 'mdi-comment-edit',
      draft_saved: 'mdi-content-save'
    }
    return iconMap[action] || 'mdi-circle'
  }

  const formatRole = role => {
    return role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatStatus = status => {
    return status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatAction = action => {
    return action.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatDate = dateString => {
    return new Date(dateString).toLocaleString()
  }

  const advanceStage = async () => {
    advancing.value = true
    try {
      await workflowStore.advanceStage({
        entity_id: props.entityId,
        entity_type: props.entityType,
        comment: 'Stage advanced via UI'
      })
      emit('stage-changed', 'advanced')
      emit('action-completed', 'advance')
    } catch (error) {
      logger.error('Failed to advance stage:', { error: error.message, stack: error.stack })
    } finally {
      advancing.value = false
    }
  }

  const rejectStage = async () => {
    rejecting.value = true
    try {
      await workflowStore.rejectStage({
        entity_id: props.entityId,
        entity_type: props.entityType,
        comment: 'Stage rejected via UI'
      })
      emit('stage-changed', 'rejected')
      emit('action-completed', 'reject')
    } catch (error) {
      logger.error('Failed to reject stage:', { error: error.message, stack: error.stack })
    } finally {
      rejecting.value = false
    }
  }

  const requestRevision = async () => {
    requesting.value = true
    try {
      await workflowStore.requestRevision({
        entity_id: props.entityId,
        entity_type: props.entityType,
        comment: 'Revision requested via UI'
      })
      emit('stage-changed', 'revision_requested')
      emit('action-completed', 'request_revision')
    } catch (error) {
      logger.error('Failed to request revision:', { error: error.message, stack: error.stack })
    } finally {
      requesting.value = false
    }
  }

  const saveDraft = async () => {
    saving.value = true
    try {
      await workflowStore.saveDraft({
        entity_id: props.entityId,
        entity_type: props.entityType
      })
      emit('action-completed', 'save_draft')
    } catch (error) {
      logger.error('Failed to save draft:', { error: error.message, stack: error.stack })
    } finally {
      saving.value = false
    }
  }

  // Watch for workflow pair changes
  watch(
    () => props.workflowPairId,
    async newPairId => {
      if (newPairId) {
        try {
          await workflowStore.fetchWorkflowStages(newPairId)
        } catch (error) {
          logger.error('Failed to load workflow stages:', { error: error.message, stack: error.stack })
        }
      }
    },
    { immediate: true }
  )

  // Watch for entity changes
  watch(
    () => props.entityId,
    async newEntityId => {
      if (newEntityId) {
        try {
          await Promise.all([
            workflowStore.fetchCurrentStage(newEntityId, props.entityType),
            workflowStore.fetchStageHistory(newEntityId)
          ])
        } catch (error) {
          logger.error('Failed to load entity workflow data:', { error: error.message, stack: error.stack })
        }
      }
    },
    { immediate: true }
  )

  onMounted(async () => {
    if (props.workflowPairId && props.entityId) {
      try {
        await Promise.all([
          workflowStore.fetchWorkflowStages(props.workflowPairId),
          workflowStore.fetchCurrentStage(props.entityId, props.entityType),
          workflowStore.fetchStageHistory(props.entityId)
        ])
      } catch (error) {
        logger.error('Failed to initialize workflow stages:', { error: error.message, stack: error.stack })
      }
    }
  })
</script>

<style scoped>
  .v-stepper-item__icon--active {
    transform: scale(1.1);
  }
</style>
