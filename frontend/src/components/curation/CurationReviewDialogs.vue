<template>
  <BaseDialog v-model="approveOpen" size="md">
    <template #title
      ><v-icon start color="success">mdi-check-circle</v-icon> Approve curation</template
    >
    <v-alert type="info" variant="tonal" class="mb-4">
      Approving this curation will move it to the <strong>Active</strong> stage.
    </v-alert>
    <p class="mb-2">
      Approve the <strong>{{ classification }}</strong> classification for
      <strong>{{ geneSymbol }}</strong
      >?
    </p>
    <div class="d-flex justify-space-between mb-2">
      <div>
        <span class="text-medium-emphasis">Total Score:</span>
        <strong class="ml-2">{{ scores.total.toFixed(2) }}</strong>
      </div>
      <div>
        <span class="text-medium-emphasis">Genetic:</span>
        <strong class="ml-2">{{ scores.genetic.toFixed(2) }}</strong>
      </div>
      <div>
        <span class="text-medium-emphasis">Experimental:</span>
        <strong class="ml-2">{{ scores.experimental.toFixed(2) }}</strong>
      </div>
    </div>
    <div class="text-body-small text-medium-emphasis mb-2">{{ counts }}</div>
    <div v-if="summary" class="text-body-medium mb-4 summary">{{ summary }}</div>
    <v-textarea
      v-model="approveComment"
      label="Approval Comments (optional)"
      placeholder="Add any comments about this approval..."
      rows="3"
      variant="outlined"
    />
    <v-alert v-if="errorDetail" type="error" variant="tonal">{{ errorDetail }}</v-alert>
    <template #actions>
      <v-btn variant="text" @click="approveOpen = false">Cancel</v-btn>
      <v-btn
        color="success"
        variant="elevated"
        :loading="busy"
        @click="emit('approve', approveComment)"
      >
        Approve
      </v-btn>
    </template></BaseDialog
  >

  <BaseDialog v-model="rejectOpen" size="md">
    <template #title><v-icon start color="warning">mdi-undo</v-icon> Request changes</template>
    <v-alert type="warning" variant="tonal" class="mb-4">
      This will return the curation to the curator for revisions.
    </v-alert>
    <p class="mb-4">
      Request changes for the curation of <strong>{{ geneSymbol }}</strong
      >?
    </p>
    <v-textarea
      v-model="rejectComment"
      label="Feedback for Curator"
      placeholder="Describe what changes are needed..."
      rows="4"
      variant="outlined"
      :rules="[v => !!v || 'Please provide feedback for the curator']"
      required
    />
    <v-alert v-if="errorDetail" type="error" variant="tonal">{{ errorDetail }}</v-alert>
    <template #actions>
      <span v-if="!rejectComment" class="text-body-small text-medium-emphasis">
        Feedback is required
      </span>
      <v-btn variant="text" @click="rejectOpen = false">Cancel</v-btn>
      <v-btn
        color="warning"
        variant="elevated"
        :loading="busy"
        :disabled="!rejectComment"
        @click="emit('reject', rejectComment)"
      >
        Request changes
      </v-btn>
    </template></BaseDialog
  >
</template>

<script setup lang="ts">
  import { ref } from 'vue'
  import BaseDialog from '@/components/BaseDialog.vue'

  defineProps<{
    geneSymbol?: string | null
    classification: string
    scores: { total: number; genetic: number; experimental: number }
    summary?: string
    counts: string
    busy: boolean
    errorDetail: string | null
  }>()
  const emit = defineEmits<{ approve: [comment: string]; reject: [comment: string] }>()
  const approveOpen = defineModel<boolean>('approveOpen', { default: false })
  const rejectOpen = defineModel<boolean>('rejectOpen', { default: false })

  // Separate fields: text typed for one decision must not leak into the other
  const approveComment = ref('')
  const rejectComment = ref('')
</script>

<style scoped>
  .summary {
    white-space: pre-wrap;
    max-height: 8rem;
    overflow-y: auto;
  }
</style>
