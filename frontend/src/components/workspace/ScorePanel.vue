<template>
  <div class="score-panel">
    <section class="panel">
      <h2 class="panel__title">Calculated classification</h2>
      <v-skeleton-loader v-if="loading" type="article" />
      <ScoreTrace v-else-if="score" :scores="score" :classification="score.classification" />
      <p v-else>Score preview unavailable.</p>
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
  import { useValidationStore } from '@/stores/validation'
  import type { ScoreSnapshot } from './useWorkspaceFrame'

  const props = withDefaults(
    defineProps<{
      score: ScoreSnapshot | null
      loading?: boolean
      canSubmit: boolean
      readonly: boolean
      blockers?: string[]
    }>(),
    { blockers: () => [] }
  )

  // Rows the scoring engine flags in the live preview (e.g. invalid or missing PMIDs)
  const validation = useValidationStore()
  const flags = computed(() => [
    ...new Set([
      ...(props.score?.excluded ?? []).map(e => e.text),
      ...(validation.getValidationResult('form')?.warnings ?? [])
        .filter(w => w.type === 'scoring')
        .map(w => String(w.message))
    ])
  ])
  const refused = computed(() => !!props.score?.excluded?.some(e => e.refused))

  const checks = computed(() => [
    ...props.blockers.map(text => ({ text, warn: true })),
    ...(props.blockers.length
      ? []
      : [
          props.loading
            ? { text: 'Checking evidence…', warn: false }
            : refused.value
              ? { text: 'Fix the rows that score 0 before submitting', warn: true }
              : props.canSubmit
                ? { text: 'Ready to submit', warn: false }
                : { text: 'Complete the required evidence before submitting', warn: true }
        ]),
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
