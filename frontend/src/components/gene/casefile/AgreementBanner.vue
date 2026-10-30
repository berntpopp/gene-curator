<template>
  <div
    v-if="scopeCount > 1 && (hasConflicts || consensus)"
    class="agreement"
    :class="hasConflicts ? 'agreement--conflict' : 'agreement--agree'"
    :role="hasConflicts ? 'alert' : 'status'"
  >
    <v-icon size="18" aria-hidden="true">{{ hasConflicts ? 'mdi-alert' : 'mdi-check' }}</v-icon>
    <span v-if="hasConflicts">
      Scopes disagree:
      <span v-for="(count, key) in classifications" :key="key" class="agreement__item">
        <ClassificationMark :classification="String(key)" />
        <span class="tabular">×{{ count }}</span>
      </span>
    </span>
    <span v-else>
      {{ scopeCount === 2 ? 'Both scopes' : `All ${scopeCount} scopes` }} agree:
      <strong>{{ getClassification(consensus).label }}</strong>
    </span>
  </div>
</template>

<script setup lang="ts">
  import ClassificationMark from '@/components/common/ClassificationMark.vue'
  import { getClassification } from '@/config/classification'

  defineProps<{
    scopeCount: number
    hasConflicts: boolean
    consensus?: string | null
    classifications: Record<string, number>
  }>()
</script>

<style scoped>
  .agreement {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    border-radius: 6px;
    border: 1px solid;
    font-size: 13px;
    line-height: 18px;
  }

  .agreement--agree {
    color: rgb(var(--v-theme-success));
    border-color: rgb(var(--v-theme-success));
    background: rgba(var(--v-theme-success), 0.08);
  }

  .agreement--conflict {
    color: rgb(var(--v-theme-warning));
    border-color: rgb(var(--v-theme-warning));
    background: rgba(var(--v-theme-warning), 0.1);
  }

  .agreement > span:not(.v-icon) {
    color: rgb(var(--v-theme-on-surface));
  }

  .agreement__item {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-left: 12px;
  }
</style>
