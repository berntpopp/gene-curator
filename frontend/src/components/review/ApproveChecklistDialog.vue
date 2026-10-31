<template>
  <BaseDialog
    :model-value="modelValue"
    size="md"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template #title>
      <span class="text-title-large">Approve {{ geneSymbol }} for {{ scopeName }}?</span>
    </template>
    <p class="text-body-medium text-medium-emphasis mb-4">
      Once every required reviewer has approved, this becomes the active, public assertion for
      {{ geneSymbol }} in this scope<template v-if="replaces">
        and replaces its active version of this disease entity</template
      >.
    </p>
    <dl class="summary mb-4">
      <div>
        <dt>Calculated</dt>
        <dd data-testid="approve-calculated">{{ calculated || '—' }}</dd>
      </div>
      <div>
        <dt>Final (you confirm)</dt>
        <dd data-testid="approve-final">{{ classification || '—' }}</dd>
      </div>
      <div>
        <dt>Score</dt>
        <dd class="mono">{{ total }}</dd>
      </div>
      <div>
        <dt>Curator</dt>
        <dd>{{ curator || '—' }}</dd>
      </div>
    </dl>
    <p v-if="rationale" class="text-body-medium mb-4" data-testid="approve-rationale">
      <strong>Curator's rationale:</strong> {{ rationale }}
    </p>
    <p
      v-if="calculated && classification && calculated !== classification"
      class="text-body-small text-medium-emphasis mb-4"
    >
      Approving confirms the curator's final classification. If you disagree, request changes.
    </p>

    <fieldset class="checks">
      <legend class="text-body-small font-weight-medium mb-1">
        Checked against {{ methodology || 'the methodology' }}
      </legend>
      <v-checkbox
        v-for="item in items"
        :key="item.id"
        v-model="ticked"
        :value="item.id"
        :label="item.label"
        density="compact"
        hide-details
      />
    </fieldset>

    <v-alert
      v-if="blockers.length"
      type="warning"
      variant="tonal"
      density="compact"
      class="mt-3"
      data-testid="blockers"
    >
      <div v-if="unaccepted.length">Accept these items first: {{ unaccepted.join(', ') }}</div>
      <div v-if="queried.length">Resolve the open queries on: {{ queried.join(', ') }}</div>
    </v-alert>

    <v-textarea
      v-model="note"
      label="Note for the record (optional)"
      rows="2"
      variant="outlined"
      density="compact"
      class="mt-3"
      hide-details
    />
    <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mt-3">
      {{ error }}
    </v-alert>

    <template #actions>
      <span class="text-body-small text-medium-emphasis mr-auto" data-testid="checks-left">{{
        left ? `${left} ${left === 1 ? 'check' : 'checks'} left` : ''
      }}</span>
      <v-btn variant="text" data-testid="approve-cancel" @click="emit('update:modelValue', false)">
        Cancel
      </v-btn>
      <v-btn
        color="primary"
        variant="flat"
        :loading="busy"
        :disabled="left > 0 || blockers.length > 0"
        data-testid="approve-confirm"
        @click="emit('approve', note)"
      >
        Approve
      </v-btn>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
  /** Approve with an SOP checklist: every item ticked and no unreviewed or queried items left. */
  import { computed, ref } from 'vue'
  import BaseDialog from '@/components/BaseDialog.vue'
  import { checklistFor } from './reviewModel'

  const props = defineProps<{
    modelValue: boolean
    geneSymbol?: string | null
    scopeName?: string | null
    /** The final classification approval publishes; `calculated` is the computed verdict */
    classification?: string | null
    calculated?: string | null
    rationale?: string | null
    /** Approval replaces an active curation of the same entity */
    replaces?: boolean
    total: number | string
    curator?: string | null
    /** What the checklist is checked against, e.g. "SOP v11" or the schema's name */
    methodology?: string | null
    blockers: { key: string; label: string; queried?: boolean }[]
    busy: boolean
    error: string | null
  }>()
  const emit = defineEmits<{ 'update:modelValue': [boolean]; approve: [string] }>()

  const ticked = ref<string[]>([])
  const note = ref('')
  const items = computed(() => checklistFor(props.classification))
  const unaccepted = computed(() => props.blockers.filter(b => !b.queried).map(b => b.label))
  const queried = computed(() => props.blockers.filter(b => b.queried).map(b => b.label))
  // Ticks and note survive Cancel: the dialog is one per curation page
  const left = computed(() => items.value.filter(i => !ticked.value.includes(i.id)).length)
</script>

<style scoped>
  .summary {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 12px;
    padding: 12px;
    border: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
    border-radius: 6px;
    margin: 0;
  }

  .summary dt {
    font-size: 12px;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .summary dd {
    margin: 0;
    font-weight: 500;
  }

  .mono {
    font-family: 'IBM Plex Mono', monospace;
  }

  .checks {
    border: 0;
    padding: 0;
  }
</style>
