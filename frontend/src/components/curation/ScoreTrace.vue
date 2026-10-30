<template>
  <div class="score-trace">
    <template v-if="summary">
      <ClassificationMark :classification="classification" />
      <p class="score-trace__total">
        {{ formatScore(scores.total)
        }}<span v-if="trace?.total_cap != null"> / {{ trace.total_cap }}</span> points
      </p>
    </template>
    <template v-if="trace">
      <div class="score-trace__scroll">
        <table>
          <caption>
            Evidence score breakdown
          </caption>
          <thead>
            <tr>
              <th scope="col">Evidence</th>
              <th scope="col">Items</th>
              <th scope="col">Raw</th>
              <th scope="col">Counted</th>
              <th scope="col">Cap</th>
            </tr>
          </thead>
          <tbody v-for="section in trace.sections" :key="section.key">
            <tr class="score-trace__section">
              <th scope="row">{{ traceLabel(section.key) }}</th>
              <td>—</td>
              <td>{{ formatScore(section.raw) }}</td>
              <td>{{ formatScore(section.score) }}</td>
              <td>{{ capText(section.raw, section.cap) }}</td>
            </tr>
            <template v-for="category in section.categories" :key="category.key">
              <tr>
                <th scope="row">{{ traceLabel(category.key) }}</th>
                <td>—</td>
                <td>{{ formatScore(category.raw) }}</td>
                <td>{{ formatScore(category.score) }}</td>
                <td>{{ capText(category.raw, category.cap) }}</td>
              </tr>
              <tr v-for="type in category.types" :key="type.path" class="score-trace__type">
                <th scope="row">{{ traceLabel(type.path) }}</th>
                <td>{{ type.items ?? '—' }}</td>
                <td>{{ formatScore(type.score) }}</td>
                <td>—</td>
                <td>—</td>
              </tr>
            </template>
          </tbody>
          <tfoot>
            <tr>
              <th scope="row">Total</th>
              <td>—</td>
              <td>{{ formatScore(trace.raw_total) }}</td>
              <td>{{ formatScore(trace.total) }}</td>
              <td>{{ capText(trace.raw_total, trace.total_cap) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p class="text-body-small text-medium-emphasis mt-2">
        Raw values are before the cap at that level. Type rows show entered item points; category
        and section rows show what counted.
      </p>
      <div v-if="rule" class="mt-3" data-testid="classification-rule">
        <h3 class="text-body-large">Selected classification rule</h3>
        <p>
          {{ traceLabel(String(rule.class ?? trace.class))
          }}<template v-if="typeof rule.min === 'number'">
            ·
            <!-- A tiny band floor (0.1) reads as a real threshold; it means any points -->
            {{
              rule.min > 0 && rule.min < 1 ? 'More than 0 points' : `Minimum ${rule.min} points`
            }}</template
          >
        </p>
        <p v-if="typeof rule.requires === 'string'">Requires {{ traceLabel(rule.requires) }}</p>
        <p v-if="typeof rule.when === 'string'">
          Override: {{ traceLabel(rule.when)
          }}<template v-if="typeof rule.field === 'string'">
            · {{ traceLabel(rule.field) }}:
            {{ Array.isArray(rule.in) ? rule.in.join(', ') : '' }}</template
          >
        </p>
        <p v-if="typeof rule.description === 'string'">{{ rule.description }}</p>
        <p v-for="(s, i) in skipped" :key="i">
          Skipped {{ traceLabel(String(s.class)) }}: needs {{ traceLabel(String(s.section)) }} ≥
          {{ s.min }} points, has {{ formatScore(Number(s.score)) }}
        </p>
      </div>
      <p v-else class="text-body-small mt-3">
        Classification rule details were not stored with this score.
      </p>
      <div v-if="trace.capped_groups.length" class="mt-3" data-testid="capped-groups">
        <h3 class="text-body-large">Capped groups</h3>
        <p v-for="(g, i) in trace.capped_groups" :key="i">
          {{ traceLabel(String(g.path)) }} · {{ g.value }}: {{ formatScore(Number(g.raw)) }} →
          {{ formatScore(Number(g.capped)) }} points
        </p>
      </div>
    </template>
    <p v-else class="text-body-small mt-2">Score breakdown unavailable for this record.</p>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue'
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  import { formatScore, traceLabel, type EvidenceScores } from '@/views/curation/curationScores'
  const props = withDefaults(
    defineProps<{ scores: EvidenceScores; classification?: string; summary?: boolean }>(),
    { classification: '', summary: true }
  )
  const trace = computed(() => props.scores.trace)
  const rule = computed(() => trace.value?.classification_rule)
  const skipped = computed(() =>
    Array.isArray(rule.value?.skipped) ? (rule.value.skipped as Record<string, unknown>[]) : []
  )
  const capText = (raw: number | null, cap: number | null) =>
    cap == null ? '—' : `${cap}${raw != null && raw > cap ? ' · capped' : ''}`
</script>

<style scoped>
  .score-trace__total {
    margin: 8px 0 16px;
    font-size: 1.25rem;
    font-variant-numeric: tabular-nums;
  }
  .score-trace__scroll {
    overflow-x: auto;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8125rem;
  }
  caption {
    text-align: left;
    font-weight: 600;
    margin-bottom: 8px;
  }
  th,
  td {
    padding: 8px;
    text-align: right;
    border-bottom: thin solid rgba(var(--v-border-color), var(--v-border-opacity));
    font-variant-numeric: tabular-nums;
  }
  th:first-child {
    text-align: left;
  }
  tbody th {
    font-weight: 400;
  }
  .score-trace__section th,
  .score-trace__section td,
  tfoot {
    font-weight: 600;
  }
  .score-trace__type th {
    padding-left: 20px;
  }
  .score-trace__type {
    color: rgb(var(--v-theme-on-surface-variant));
  }
</style>
