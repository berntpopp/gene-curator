<template>
  <div class="score-panel">
    <section class="panel">
      <h2 class="panel__title">
        Calculated classification
        <span class="panel__total mono">
          {{ score.total.toFixed(1) }} <small>/ {{ MAX }}</small>
        </span>
      </h2>
      <ClassificationMark :classification="score.classification" class="my-2" />
      <div
        class="band"
        role="meter"
        aria-label="Evidence score"
        :aria-valuenow="Number(score.total.toFixed(1))"
        aria-valuemin="0"
        :aria-valuemax="MAX"
      >
        <div class="band__fill" :style="{ width: `${Math.min(score.total / MAX, 1) * 100}%` }" />
        <i
          v-for="t in TICKS"
          :key="t"
          class="band__tick"
          :style="{ left: `${(t / MAX) * 100}%` }"
        />
      </div>
      <div class="band__labels mono" aria-hidden="true">
        <span v-for="t in TICKS" :key="t" :style="{ left: `${(t / MAX) * 100}%` }">{{ t }}</span>
        <span style="left: 100%">{{ MAX }}</span>
      </div>
      <p v-if="next" class="text-body-small text-medium-emphasis mt-2">
        {{ next.points.toFixed(1) }} points to {{ next.label }}
      </p>

      <table class="breakdown">
        <thead>
          <tr>
            <th scope="col">Category</th>
            <th scope="col" class="num">Counted</th>
            <th scope="col" class="num">Max</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rows" :key="r.label" :class="{ breakdown__sum: r.sum }">
            <td>{{ r.label }}</td>
            <td class="num mono">{{ r.value.toFixed(1) }}</td>
            <td class="num mono">{{ r.max }}</td>
          </tr>
        </tbody>
      </table>
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
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  import type { ScoreSnapshot } from './useWorkspaceFrame'

  const MAX = 18
  const TICKS = [1, 7, 12]
  // ClinGen SOP v11 point thresholds; the classification itself comes from the scorer.
  const BANDS = [
    { at: 0.1, label: 'Limited' },
    { at: 7, label: 'Moderate' },
    { at: 12, label: 'Strong' }
  ]

  const props = withDefaults(
    defineProps<{
      score: ScoreSnapshot
      canSubmit: boolean
      readonly: boolean
      blockers?: string[]
    }>(),
    { blockers: () => [] }
  )

  const next = computed(() => {
    const band = BANDS.find(b => b.at > props.score.total)
    return band ? { label: band.label, points: band.at - props.score.total } : null
  })

  const rows = computed(() => {
    const g = props.score.geneticBreakdown
    const e = props.score.experimentalBreakdown
    return [
      { label: 'Case-level', value: g?.caseLevel ?? 0, max: 12 },
      { label: 'Segregation', value: g?.segregation ?? 0, max: 3 },
      { label: 'Case-control', value: g?.caseControl ?? 0, max: 6 },
      { label: 'Genetic', value: props.score.genetic, max: 12, sum: true },
      { label: 'Function', value: e?.function ?? 0, max: 2 },
      { label: 'Functional alteration', value: e?.functionalAlteration ?? 0, max: 2 },
      { label: 'Models & rescue', value: e?.modelsAndRescue ?? 0, max: 4 },
      { label: 'Experimental', value: props.score.experimental, max: 6, sum: true }
    ]
  })

  const checks = computed(() => [
    ...props.blockers.map(text => ({ text, warn: true })),
    ...(props.blockers.length
      ? []
      : [
          props.canSubmit
            ? { text: 'Ready to submit', warn: false }
            : { text: 'Add at least one scored genetic evidence item', warn: true }
        ]),
    ...(props.score.hasContradictory
      ? [
          {
            text: 'Contradictory evidence is recorded and classes this gene as Disputed',
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

  .panel__total {
    font-size: 24px;
    font-weight: 600;
  }

  .panel__total small {
    font-size: 13px;
    font-weight: 400;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .mono {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
    font-variant-numeric: tabular-nums;
  }

  .band {
    position: relative;
    height: 8px;
    border-radius: 4px;
    background: rgba(var(--v-theme-on-surface), 0.1);
    overflow: hidden;
  }

  .band__fill {
    height: 100%;
    background: rgb(var(--v-theme-primary));
  }

  .band__tick {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: rgb(var(--v-theme-surface));
  }

  .band__labels {
    position: relative;
    height: 16px;
    margin-top: 4px;
    font-size: 12px;
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
  }

  .band__labels span {
    position: absolute;
    transform: translateX(-50%);
  }

  .band__labels span:last-child {
    transform: translateX(-100%);
  }

  .breakdown {
    width: 100%;
    margin-top: 12px;
    border-collapse: collapse;
    font-size: 13px;
  }

  .breakdown th,
  .breakdown td {
    padding: 6px 0;
    border-top: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
    text-align: left;
    font-weight: 400;
  }

  .breakdown th {
    color: rgb(var(--v-theme-on-surface-variant, var(--v-theme-on-surface)));
    border-top: 0;
  }

  .breakdown .num {
    text-align: right;
  }

  .breakdown__sum td {
    font-weight: 700;
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
