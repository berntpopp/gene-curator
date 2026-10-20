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
          <!-- @vue-expect-error Vuetify types the stepper item.* slot props as StepperItem -->
          <template #item.icon="{ item, index }">
            <v-icon
              :color="getStageColor(index)"
              :class="{ 'v-stepper-item__icon--active': index <= currentStageIndex }"
            >
              {{ getStageIcon(item.raw) }}
            </v-icon>
          </template>

          <!-- @vue-expect-error Vuetify types the stepper item.* slot props as StepperItem -->
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

          <!-- @vue-expect-error Vuetify types the stepper item.* slot props as StepperItem -->
          <template #item.subtitle="{ item }">
            <div class="text-caption text-medium-emphasis mt-1">
              {{ item.raw.description }}
            </div>
          </template>
        </v-stepper>

        <!-- Current Stage Details -->
        <v-card v-if="currentStageInfo" variant="outlined" class="mb-6">
          <v-card-title class="d-flex align-center">
            <v-icon :color="getStageColor(currentStageIndex)" start>
              {{ getStageIcon(currentStageInfo) }}
            </v-icon>
            {{ currentStageInfo.name }}
            <v-spacer />
            <v-chip :color="getStageColor(currentStageIndex)" size="small" variant="flat">
              Stage {{ currentStageIndex + 1 }} of {{ workflowStages.length }}
            </v-chip>
          </v-card-title>

          <v-card-text>
            <div class="text-body-1 mb-4">{{ currentStageInfo.description }}</div>

            <v-row>
              <v-col cols="12" sm="6">
                <div class="text-subtitle-2 mb-2">Required Roles</div>
                <div class="d-flex flex-wrap gap-2">
                  <v-chip
                    v-for="role in currentStageInfo.required_roles"
                    :key="role"
                    size="small"
                    color="info"
                    variant="outlined"
                  >
                    {{ formatRole(role) }}
                  </v-chip>
                </div>
              </v-col>
            </v-row>
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
                  :dot-color="getEventColor(event)"
                  size="small"
                >
                  <template #icon>
                    <v-icon size="small">{{ getEventIcon(event) }}</v-icon>
                  </template>

                  <div class="d-flex justify-space-between align-center mb-1">
                    <span class="font-weight-medium">{{ formatTransition(event) }}</span>
                    <span class="text-caption text-medium-emphasis">
                      {{ formatDate(event.executed_at) }}
                    </span>
                  </div>

                  <div class="text-body-2 mb-1">
                    Stage: {{ event.from_stage ?? 'none' }} → {{ event.to_stage }}
                  </div>

                  <div v-if="event.notes" class="text-body-2 mt-2 pa-2 bg-grey-lighten-4 rounded">
                    "{{ event.notes }}"
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

<script setup lang="ts">
  import { ref, computed, watch, type PropType } from 'vue'
  import { useLogger } from '@/composables/useLogger'
  import { useWorkflowStore, type WorkflowItemType } from '@/stores/workflow'
  import type { Schema } from '@/types/api'
  import { errorDetails } from './errorDetails'

  const logger = useLogger()

  const props = defineProps({
    entityId: {
      type: String,
      required: true
    },
    entityType: {
      type: String as PropType<WorkflowItemType>,
      required: true,
      validator: (value: string) => ['precuration', 'curation'].includes(value)
    }
  })

  const emit = defineEmits<{
    'stage-changed': [action: string]
    'action-completed': [action: string]
  }>()

  const workflowStore = useWorkflowStore()
  const advancing = ref(false)
  const rejecting = ref(false)

  const loading = computed(() => workflowStore.loading)
  const error = computed(() => workflowStore.error)
  const workflowStages = computed(() => workflowStore.workflowStages)
  const itemState = computed(() => workflowStore.getCurrentStage(props.entityId))
  const stageHistory = computed(() => workflowStore.getStageHistory(props.entityId))

  const stageIndexOf = (stage: Schema<'WorkflowStage'>): number =>
    workflowStages.value.findIndex(s => s.id === stage)

  const currentStageIndex = computed(() =>
    itemState.value ? stageIndexOf(itemState.value.current_stage) : 0
  )
  const currentStageInfo = computed(() => workflowStages.value[currentStageIndex.value])

  // The backend decides which transitions are allowed; forward/backward is by stage order
  const canAdvanceStage = computed(() =>
    itemState.value?.available_transitions.some(t => stageIndexOf(t) > currentStageIndex.value)
  )
  const canRejectStage = computed(() =>
    itemState.value?.available_transitions.some(t => stageIndexOf(t) < currentStageIndex.value)
  )

  const getNextStageName = (): string =>
    workflowStages.value[currentStageIndex.value + 1]?.name ?? ''

  const getStageColor = (index: number): string => {
    if (index < currentStageIndex.value) return 'success'
    if (index === currentStageIndex.value) return 'primary'
    return 'grey'
  }

  const getStageIcon = (stage: { stage_type: string }): string => {
    const iconMap: Record<string, string> = {
      entry: 'mdi-file-document-edit',
      precuration: 'mdi-account-search',
      curation: 'mdi-account-check',
      review: 'mdi-eye-check',
      active: 'mdi-check-circle'
    }
    return iconMap[stage.stage_type] ?? 'mdi-circle'
  }

  const isBackward = (event: Schema<'WorkflowAuditEntry'>): boolean =>
    event.from_stage !== null && stageIndexOf(event.to_stage) < stageIndexOf(event.from_stage)

  const getEventColor = (event: Schema<'WorkflowAuditEntry'>): string =>
    isBackward(event) ? 'error' : 'success'

  const getEventIcon = (event: Schema<'WorkflowAuditEntry'>): string =>
    isBackward(event) ? 'mdi-close-circle' : 'mdi-arrow-right-circle'

  const formatTransition = (event: Schema<'WorkflowAuditEntry'>): string =>
    isBackward(event) ? 'Returned' : 'Advanced'

  const formatRole = (role: string): string => {
    return role.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  const formatDate = (dateString: string): string => {
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
    } catch (err) {
      logger.error('Failed to advance stage:', errorDetails(err))
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
    } catch (err) {
      logger.error('Failed to reject stage:', errorDetails(err))
    } finally {
      rejecting.value = false
    }
  }

  // Load the entity's workflow state on mount and whenever the entity changes
  watch(
    () => props.entityId,
    async entityId => {
      if (!entityId) return
      try {
        await Promise.all([
          workflowStore.fetchCurrentStage(entityId, props.entityType),
          workflowStore.fetchStageHistory(entityId, props.entityType)
        ])
      } catch (err) {
        logger.error('Failed to load entity workflow data:', errorDetails(err))
      }
    },
    { immediate: true }
  )
</script>

<style scoped>
  .v-stepper-item__icon--active {
    transform: scale(1.1);
  }
</style>
