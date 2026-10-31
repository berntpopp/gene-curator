<template>
  <header class="ws-header" :class="{ 'ws-header--sticky': state && !readonly }">
    <nav aria-label="Breadcrumb" class="ws-crumbs">
      <template v-for="(c, i) in crumbs" :key="i">
        <router-link v-if="c.to" :to="c.to">{{ c.text }}</router-link>
        <span v-else aria-current="page">{{ c.text }}</span>
        <span v-if="i < crumbs.length - 1" class="ws-crumbs__sep" aria-hidden="true">/</span>
      </template>
    </nav>

    <div class="ws-title">
      <div class="ws-title__text">
        <h1 class="mono">{{ title }}</h1>
        <span v-if="subtitle" class="ws-title__disease">{{ subtitle }}</span>
        <span v-if="moi" class="text-medium-emphasis">{{ formatInheritance(moi) }}</span>
        <span v-if="relationshipLabel(relationship)" class="text-medium-emphasis">
          {{ relationshipLabel(relationship) }}
        </span>
        <StageLine :stage="stage" :archived="archived" />
      </div>

      <div class="ws-actions">
        <SaveState v-if="state" :state="state" :saved-at="savedAt" @retry="emit('retry')" />
        <!-- No save state: the page has no draft here (precuration shell), so no actions -->
        <template v-if="state">
          <v-btn
            data-testid="ws-save"
            variant="outlined"
            :loading="saving"
            :disabled="readonly"
            @click="emit('save')"
          >
            Save draft
          </v-btn>
          <v-btn
            v-if="showSubmit"
            data-testid="ws-submit"
            color="primary"
            variant="flat"
            :disabled="readonly"
            :aria-disabled="!canSubmit"
            :class="{ 'ws-submit--blocked': !canSubmit }"
            :aria-describedby="reasons.length ? 'ws-blockers' : undefined"
            @click="onSubmit"
          >
            Submit for review
          </v-btn>
        </template>
      </div>
    </div>
    <!-- Own line below the buttons: text appearing between mousedown and mouseup must not move them (#267) -->
    <p
      v-if="showSubmit && reasons.length"
      id="ws-blockers"
      data-testid="ws-blockers"
      class="ws-blockers text-error"
      aria-live="polite"
    >
      {{ reasons.join('; ') }}
    </p>
  </header>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue'
  import { formatInheritance, relationshipLabel } from '@/utils/inheritance'
  import { rowLabel } from '@/views/curation/curationScores'
  import { useValidationStore } from '@/stores/validation'
  import StageLine from './StageLine.vue'
  import SaveState from './SaveState.vue'
  import type { SaveState as SaveStateName } from './useWorkspaceFrame'

  const props = defineProps<{
    crumbs: { text: string; to?: string }[]
    title: string
    subtitle?: string
    moi?: string
    relationship?: string
    stage?: string | null
    archived?: boolean
    /** Omitted where the page has no draft to save (precuration shell). */
    state?: SaveStateName
    savedAt: number | null
    readonly: boolean
    showSubmit: boolean
    canSubmit: boolean
    /** Why Submit is blocked (e.g. an unknown PMID), shown below the buttons. */
    blockers?: string[]
    saving: boolean
  }>()
  const emit = defineEmits<{ save: []; submit: []; retry: [] }>()

  // A blocked Submit without blocker text (form invalid or empty) says why once clicked
  const tried = ref(false)
  // The form's validation errors name the field; the generic text is the last resort
  const validation = useValidationStore()
  const reasons = computed(() => {
    if (props.blockers?.length) return props.blockers
    if (!tried.value || props.canSubmit) return []
    const errors = (validation.getValidationResult('form')?.errors ?? []).map(
      e => `${rowLabel(String(e.field))}: ${String(e.message)}`
    )
    return errors.length ? errors : ['Complete the required evidence before submitting']
  })
  function onSubmit() {
    tried.value = !props.canSubmit
    emit('submit')
  }
</script>

<style scoped>
  .ws-header {
    margin-bottom: 16px;
  }

  .ws-header--sticky {
    position: sticky;
    top: var(--v-layout-top, 0px);
    z-index: 5;
    padding-block: 8px;
    background: rgb(var(--v-theme-surface));
  }

  .ws-crumbs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    font-size: 13px;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .ws-crumbs a {
    color: rgb(var(--v-theme-secondary));
  }

  .ws-title {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    justify-content: space-between;
    gap: 12px 24px;
    margin-top: 6px;
  }

  .ws-title__text {
    display: flex;
    min-width: 0;
    overflow-wrap: anywhere;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 6px 16px;
  }

  .ws-title h1 {
    font-size: 22px;
    font-weight: 600;
  }

  .ws-title__disease {
    font-size: 22px;
  }

  .ws-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
  }

  /* Fits "Unsaved changes": the label flipping at mousedown must not move the buttons (#267) */
  .ws-actions > .save-state {
    min-width: 9.5em;
    justify-content: flex-end;
  }

  /* Not `disabled`: the click whose mousedown commits a cell edit must land (#406); the frame
     refuses a submit that is still not allowed */
  .ws-submit--blocked {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .ws-blockers {
    margin-top: 6px;
    text-align: right;
  }

  .mono {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
  }

  /* Phones: a sticky header would take half the screen; Save and Submit sit in a bar above the
     bottom tabs instead, always in reach (390 px monkey) */
  @media (max-width: 599.98px) {
    .ws-header--sticky {
      position: static;
    }

    .ws-header--sticky .ws-actions {
      position: fixed;
      inset: auto 0 var(--v-layout-bottom, 0px) 0;
      z-index: 5;
      justify-content: flex-end;
      padding: 8px 16px;
      background: rgb(var(--v-theme-surface));
      border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    }
  }
</style>
