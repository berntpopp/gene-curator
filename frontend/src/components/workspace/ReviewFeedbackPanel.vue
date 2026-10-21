<template>
  <aside v-if="feedback?.any" class="feedback" aria-labelledby="feedback-title">
    <h2 id="feedback-title" class="text-title-medium mb-2">Review feedback</h2>
    <p v-if="feedback.note" class="feedback__note" data-testid="feedback-note">
      {{ feedback.note }}
    </p>
    <ul v-if="feedback.queries.length" class="feedback__queries">
      <li v-for="q in feedback.queries" :key="q.id" data-testid="feedback-query">
        <span class="text-body-small text-medium-emphasis">{{ itemLabel(q.item_path) }}</span>
        <div>{{ q.body }}</div>
      </li>
    </ul>
    <router-link :to="`/scopes/${scopeId}/curations/${curationId}`" class="text-body-small">
      Reply on the curation page
    </router-link>
  </aside>
</template>

<script setup lang="ts">
  /** What the reviewer asked for when sending the curation back: their note and open item queries. */
  import { onMounted, ref } from 'vue'
  import { itemLabel } from '@/components/review/reviewModel'
  import { useReviewFeedbackStore, type ReviewFeedback } from '@/stores/reviewFeedback'

  const props = defineProps<{ curationId: string; scopeId: string; me: string }>()

  const feedback = ref<ReviewFeedback | null>(null)
  onMounted(async () => {
    // The page works without the panel, so a failed lookup just hides it
    feedback.value = await useReviewFeedbackStore()
      .fetch(props.curationId, props.me)
      .catch(() => null)
  })
</script>

<style scoped>
  .feedback {
    padding: 12px 16px;
    margin-bottom: 16px;
    background: rgb(var(--v-theme-surface));
    border: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
    border-left: 3px solid rgb(var(--v-theme-warning));
    border-radius: 6px;
    /* Long unbroken text (URLs, IDs) wraps instead of widening the page */
    overflow-wrap: anywhere;
    min-width: 0;
  }

  .feedback__note {
    white-space: pre-line;
    margin-bottom: 8px;
  }

  .feedback__queries {
    list-style: none;
    padding: 0;
    margin: 0 0 8px;
  }

  .feedback__queries li + li {
    margin-top: 8px;
  }
</style>
