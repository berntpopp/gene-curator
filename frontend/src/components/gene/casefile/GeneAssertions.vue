<template>
  <section aria-labelledby="assertions-title" class="assertions">
    <h2 id="assertions-title" class="assertions__title">Gene-disease assertions</h2>
    <div class="assertions__scroll">
      <table class="assertions__table">
        <thead>
          <tr>
            <th scope="col">Scope</th>
            <th scope="col">Disease</th>
            <th scope="col">MOI</th>
            <th scope="col">Stage</th>
            <th scope="col">Classification</th>
            <th scope="col" class="num">Score</th>
            <th scope="col">Updated</th>
            <th scope="col"><span class="sr-only">Curation</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in scopes" :key="s.curation_id ?? s.scope_id">
            <td data-label="Scope" class="scope">
              <router-link
                v-if="linked"
                :to="{ name: 'scope-dashboard', params: { scopeId: s.scope_id } }"
              >
                {{ s.scope_display_name }}
              </router-link>
              <template v-else>{{ s.scope_display_name }}</template>
            </td>
            <td data-label="Disease" class="wide">
              {{ s.disease_name || EMPTY }}
              <span v-if="s.mondo_id" class="mono assertions__mondo">{{ s.mondo_id }}</span>
            </td>
            <td data-label="MOI">
              {{ s.mode_of_inheritance ? formatInheritance(s.mode_of_inheritance) : EMPTY }}
              <span v-if="s.relationship_type === 'susceptibility'">(susceptibility)</span>
            </td>
            <td data-label="Stage">
              {{ stageLabel(s.stage) }}
              <span v-if="s.in_progress" class="assertions__progress">in progress</span>
            </td>
            <td data-label="Classification">
              <ClassificationMark :classification="s.classification" />
            </td>
            <td data-label="Score" class="num mono tabular">{{ s.total_score.toFixed(1) }}</td>
            <td data-label="Updated" class="mono tabular">{{ formatDate(s.last_updated) }}</td>
            <td class="open">
              <router-link
                v-if="linked && s.curation_id"
                :to="{
                  name: 'curation-detail',
                  params: { scopeId: s.scope_id, curationId: s.curation_id }
                }"
                :aria-label="`Open curation in ${s.scope_display_name}`"
              >
                Open
              </router-link>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup lang="ts">
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  import { curationStatusLabel } from '@/config/status'
  import { EMPTY, formatDate } from '@/utils/format'
  import { formatInheritance } from '@/utils/inheritance'
  import type { Schema } from '@/types/api'

  defineProps<{
    scopes: Schema<'ScopeSummary'>[]
    /** Signed-in viewers get links; the public view is read-only text. */
    linked: boolean
  }>()

  const STAGES: Record<string, string> = {
    precuration: 'Precuration',
    curation: 'In curation',
    review: 'In review'
  }
  const stageLabel = (stage: string | null | undefined) =>
    stage ? (STAGES[stage] ?? curationStatusLabel(stage)) : EMPTY
</script>

<style scoped>
  .assertions {
    background: rgb(var(--v-theme-surface));
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-radius: 8px;
  }

  .assertions__title {
    margin: 0;
    padding: 14px 16px;
    font-size: 15px;
    font-weight: 600;
    line-height: 20px;
  }

  .assertions__scroll {
    overflow-x: auto;
  }

  .assertions__table {
    width: 100%;
    min-width: 720px;
    border-collapse: collapse;
    font-size: 13px;
    line-height: 18px;
  }

  th {
    text-align: left;
    font-weight: 600;
    color: rgb(var(--v-theme-on-surface-variant));
    padding: 8px 16px;
    border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }

  td {
    padding: 10px 16px;
    border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  }

  .num {
    text-align: right;
  }

  a {
    color: rgb(var(--v-theme-info));
    text-decoration: underline;
    text-underline-offset: 2px;
  }

  .assertions__mondo {
    margin-left: 6px;
    color: rgb(var(--v-theme-on-surface-variant));
  }

  .assertions__progress {
    margin-left: 6px;
    color: rgb(var(--v-theme-warning));
  }

  /* Phone: one block per scope instead of a table that scrolls the classification off-screen */
  @media (max-width: 600px) {
    .assertions__table {
      min-width: 0;
    }

    thead {
      position: absolute;
      width: 1px;
      height: 1px;
      overflow: hidden;
      clip-path: inset(50%);
    }

    tr {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px 16px;
      padding: 12px 16px;
      border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    }

    td {
      display: block;
      padding: 0;
      border: 0;
      text-align: left;
    }

    td[data-label]::before {
      content: attr(data-label);
      font-family: var(--font-sans);
      display: block;
      font-size: 12px;
      color: rgb(var(--v-theme-on-surface-variant));
    }

    td.num {
      text-align: left;
    }

    .scope,
    .wide {
      grid-column: 1 / -1;
    }

    .open:empty {
      display: none;
    }
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip-path: inset(50%);
  }
</style>
