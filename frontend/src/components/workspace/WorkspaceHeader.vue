<template>
  <header class="ws-header">
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
        <span v-if="moi" class="text-medium-emphasis">{{ moi }}</span>
        <StageLine :stage="stage" :archived="archived" />
      </div>

      <div class="ws-actions">
        <SaveState v-if="state" :state="state" :saved-at="savedAt" @retry="emit('retry')" />
        <template v-if="!readonly">
          <v-btn
            data-testid="ws-save"
            variant="outlined"
            :loading="saving"
            :disabled="saveBlocked"
            @click="emit('save')"
          >
            Save draft
          </v-btn>
          <v-btn
            v-if="showSubmit"
            data-testid="ws-submit"
            color="primary"
            variant="flat"
            :disabled="!canSubmit"
            @click="emit('submit')"
          >
            Submit for review
          </v-btn>
        </template>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
  import StageLine from './StageLine.vue'
  import SaveState from './SaveState.vue'
  import type { SaveState as SaveStateName } from './useWorkspaceFrame'

  defineProps<{
    crumbs: { text: string; to?: string }[]
    title: string
    subtitle?: string
    moi?: string
    stage?: string | null
    archived?: boolean
    /** Omitted where the page has no draft to save (precuration shell). */
    state?: SaveStateName
    savedAt: number | null
    readonly: boolean
    showSubmit: boolean
    canSubmit: boolean
    saving: boolean
    saveBlocked?: boolean
  }>()
  const emit = defineEmits<{ save: []; submit: []; retry: [] }>()
</script>

<style scoped>
  .ws-header {
    margin-bottom: 16px;
  }

  .ws-crumbs {
    display: flex;
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

  .mono {
    font-family: 'IBM Plex Mono', ui-monospace, monospace;
  }
</style>
