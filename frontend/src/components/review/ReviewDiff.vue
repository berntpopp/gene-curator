<template>
  <section v-if="shown" aria-labelledby="review-diff-title" class="review-diff">
    <h2 id="review-diff-title" class="text-title-medium mb-1">Evidence changes</h2>
    <p class="text-body-medium text-medium-emphasis mb-3" data-testid="baseline">
      {{ baselineText }}
    </p>
    <v-alert
      v-if="review.error"
      type="error"
      variant="tonal"
      class="mb-3"
      data-testid="review-error"
    >
      {{ review.error }}
    </v-alert>
    <p v-if="loaded && !groups.length" class="text-medium-emphasis">No changes to review.</p>

    <ol class="review-diff__items">
      <li v-for="g in groups" :key="g.key" class="item" data-testid="item">
        <div class="item__head">
          <div class="item__title">
            <span class="item__label">{{ g.label }}</span>
            <v-chip v-if="g.change !== 'changed'" size="x-small" variant="tonal">
              {{ g.change === 'added' ? 'Added' : 'Removed' }}
            </v-chip>
          </div>
          <div v-if="reviewer" class="item__check" role="group" :aria-label="`Check ${g.label}`">
            <v-btn
              size="small"
              variant="outlined"
              :color="state(g.key).status === 'accepted' ? 'success' : undefined"
              :aria-pressed="state(g.key).status === 'accepted'"
              :disabled="busy"
              :data-testid="`accept-${g.key}`"
              @click="toggleAccept(g.key)"
            >
              Accept
            </v-btn>
            <v-btn
              size="small"
              variant="outlined"
              :color="state(g.key).status === 'queried' ? 'warning' : undefined"
              :aria-pressed="querying.has(g.key) || state(g.key).status === 'queried'"
              :data-testid="`query-${g.key}`"
              @click="toggleQuery(g.key)"
            >
              Query
            </v-btn>
          </div>
          <v-chip v-else-if="state(g.key).status === 'queried'" size="x-small" color="warning">
            Queried
          </v-chip>
        </div>

        <dl class="item__fields">
          <template v-for="f in g.fields" :key="f.name">
            <dt v-if="f.name" class="mono">{{ f.name }}</dt>
            <dd>
              <del v-if="f.change !== 'added'" class="del">{{ formatValue(f.before) }}</del>
              <ins v-if="f.change !== 'removed'" class="ins">{{ formatValue(f.after) }}</ins>
            </dd>
          </template>
        </dl>

        <ReviewItemThread
          v-if="state(g.key).queries.length || querying.has(g.key)"
          :queries="state(g.key).queries"
          :me="me"
          :creator-id="creatorId"
          :can-reply="canReply"
          :busy="busy"
          @send="send(g.key, $event)"
          @resolve="run(() => review.resolveThread(g.key))"
        />
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
  /**
   * The evidence diff of a submitted curation: changes grouped by item with before/after, and for
   * reviewers Accept/Query per item. Curators see the queries and can reply and resolve; only
   * `reviewer` shows Accept/Query (the curation's creator never gets them).
   */
  import { computed, onMounted, ref } from 'vue'
  import { formatDate } from '@/utils/format'
  import { useReviewStore } from '@/stores/review'
  import { errorMessage } from '@/stores/apiError'
  import ReviewItemThread from './ReviewItemThread.vue'
  import { formatValue, groupDiff, itemState } from './reviewModel'

  const props = defineProps<{
    curationId: string
    me: string
    creatorId: string
    reviewer: boolean
    canReply: boolean
    /** Outside review (e.g. after changes were requested) show only when there are comments. */
    onlyWithComments?: boolean
  }>()

  const review = useReviewStore()
  const busy = ref(false)
  const loaded = ref(false)
  const querying = ref(new Set<string>())

  const shown = computed(
    () => !props.onlyWithComments || !loaded.value || review.comments.length > 0
  )
  const groups = computed(() => groupDiff(review.diff?.items ?? []))
  const state = (key: string) => itemState(review.comments, key, props.me)

  const baselineText = computed(() => {
    const b = review.diff?.baseline
    if (!loaded.value) return ''
    if (!b) return 'First review: all items new.'
    const what = b.source === 'review' ? 'your last review' : 'the previous submission'
    return `Showing changes since ${what} on ${formatDate(b.as_of)}.`
  })

  /** Run a store action, surfacing the API detail (e.g. a refused write) instead of failing silently. */
  async function run(action: () => Promise<void>) {
    busy.value = true
    review.error = null
    try {
      await action()
    } catch (e) {
      review.error = errorMessage(e, 'Request failed')
    } finally {
      busy.value = false
    }
  }

  function toggleAccept(key: string) {
    const accepted = state(key).accepted
    return run(() => (accepted ? review.withdraw(accepted.id) : review.accept(key)))
  }

  function toggleQuery(key: string) {
    const next = new Set(querying.value)
    if (!next.delete(key)) next.add(key)
    querying.value = next
  }

  const send = (key: string, body: string) => run(() => review.query(key, body))

  onMounted(async () => {
    await review.load(props.curationId)
    loaded.value = true
  })
</script>

<style scoped>
  .review-diff__items {
    list-style: none;
    padding: 0;
    margin: 0;
    border: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
    border-radius: 6px;
    background: rgb(var(--v-theme-surface));
  }

  .item {
    padding: 12px 16px;
  }

  .item + .item {
    border-top: 1px solid rgb(var(--v-theme-outline, var(--v-border-color)));
  }

  .item__head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .item__label {
    font-weight: 500;
    margin-right: 8px;
  }

  .item__check {
    display: flex;
    gap: 6px;
  }

  .item__fields {
    display: grid;
    grid-template-columns: max-content 1fr;
    gap: 2px 16px;
    margin: 6px 0 0;
    font-size: 13px;
  }

  .item__fields dd {
    margin: 0;
    font-family: 'IBM Plex Mono', monospace;
    overflow-wrap: anywhere;
  }

  .item__fields dd:has(:only-child),
  .item__fields dt:first-child:empty {
    grid-column: 1 / -1;
  }

  .del {
    color: rgb(var(--v-theme-error));
    margin-right: 8px;
  }

  .ins {
    color: rgb(var(--v-theme-success));
    text-decoration: none;
  }
</style>
