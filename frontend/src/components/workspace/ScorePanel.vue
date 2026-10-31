<template>
  <div class="score-panel">
    <section class="panel">
      <h2 class="panel__title">Calculated classification</h2>
      <v-skeleton-loader v-if="loading" type="article" />
      <template v-else>
        <v-alert
          v-if="validation.error"
          type="error"
          variant="tonal"
          density="compact"
          class="mb-2"
          data-testid="score-error"
        >
          Score preview failed: {{ validation.error }}
        </v-alert>
        <ScoreTrace v-if="score" :scores="score" :classification="score.classification" />
        <!-- A validated form without a score means the schema has no scoring -->
        <p
          v-else-if="!validation.error && validation.getValidationResult('form')"
          class="text-medium-emphasis"
          data-testid="score-none"
        >
          No scoring for this schema.
        </p>
        <p v-else-if="!validation.error" class="text-medium-emphasis" data-testid="score-empty">
          0 points so far. The classification appears here as you add evidence.
        </p>
      </template>
      <ul
        v-if="flags.length"
        data-testid="score-flags"
        class="checklist"
        aria-label="Rows to check"
      >
        <li v-for="f in flags" :key="f" class="checklist--warn">
          <v-icon size="16" aria-hidden="true">mdi-alert-circle-outline</v-icon>
          {{ f }}
        </li>
      </ul>
    </section>

    <section v-if="!readonly" class="panel">
      <h2 class="panel__title">Before you submit</h2>
      <ul class="checklist">
        <li v-for="c in checks" :key="c.text" :class="{ 'checklist--warn': c.warn }">
          <v-icon size="16" aria-hidden="true">{{
            c.warn ? 'mdi-alert-circle-outline' : 'mdi-check'
          }}</v-icon>
          {{ c.text }}
        </li>
      </ul>
    </section>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import ScoreTrace from '@/components/curation/ScoreTrace.vue'
  import { rowLabel } from '@/views/curation/curationScores'
  import { useValidationStore } from '@/stores/validation'
  import type { ScoreSnapshot } from './useWorkspaceFrame'

  const props = withDefaults(
    defineProps<{
      score: ScoreSnapshot | null
      loading?: boolean
      canSubmit: boolean
      readonly: boolean
      /** Why Submit is blocked, including rows it would refuse (the workspace frame) */
      blockers?: string[]
    }>(),
    { blockers: () => [] }
  )

  // Rows the scoring engine flags in the live preview (e.g. invalid or missing PMIDs)
  const validation = useValidationStore()
  // Scoring warnings start with the row's evidence path (`a.rows[0].points = 5 ...`)
  const labelled = (message: string) =>
    message.replace(/^(\S+\[\d+\]\S*)(?= = )/, path => rowLabel(path))
  const flags = computed(() => [
    ...new Set([
      ...(props.score?.excluded ?? []).map(e => e.text),
      ...(validation.getValidationResult('form')?.warnings ?? [])
        .filter(w => w.type === 'scoring')
        .map(w => labelled(String(w.message)))
    ])
  ])
  // Why the form is invalid, by field label (e.g. a row outside its range)
  const errors = computed(() =>
    (validation.getValidationResult('form')?.errors ?? []).map(
      e => `${rowLabel(String(e.field))}: ${String(e.message)}`
    )
  )

  const status = () => {
    if (props.blockers.length) return props.blockers.map(text => ({ text, warn: true }))
    if (props.loading) return [{ text: 'Checking evidence…', warn: false }]
    if (props.canSubmit) return [{ text: 'Ready to submit', warn: false }]
    const why = errors.value.length
      ? errors.value
      : ['Complete the required evidence before submitting']
    return why.map(text => ({ text, warn: true }))
  }

  const checks = computed(() => [
    ...status(),
    ...(props.score?.hasContradictory
      ? [
          {
            text: 'Contradictory evidence is recorded',
            warn: true
          }
        ]
      : [])
  ])
</script>

<style scoped>
  .panel {
    background: rgb(var(--v-theme-surface));
    border: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
    border-radius: 6px;
    padding: 16px;
    margin-bottom: 16px;
  }

  .panel__title {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    font-size: 14px;
    font-weight: 600;
  }

  .checklist {
    margin: 8px 0 0;
    padding: 0;
    list-style: none;
    font-size: 13px;
  }

  .checklist li {
    display: flex;
    gap: 8px;
    padding: 4px 0;
  }

  .checklist--warn {
    color: rgb(var(--v-theme-warning));
  }
</style>
