<template>
  <div class="thread" data-testid="thread">
    <ul v-if="queries.length" class="thread__list">
      <li v-for="q in queries" :key="q.id" :class="{ thread__resolved: q.status === 'resolved' }">
        <strong class="thread__author">{{ author(q.author_id) }}</strong>
        <span class="text-medium-emphasis">
          {{ formatDateTime(q.created_at) }}{{ q.status === 'resolved' ? ' · resolved' : '' }}
        </span>
        <div>{{ q.body }}</div>
      </li>
    </ul>
    <template v-if="canReply">
      <v-textarea
        v-model="text"
        data-testid="thread-input"
        :label="queries.length ? 'Reply' : 'Your query'"
        rows="2"
        auto-grow
        variant="outlined"
        density="compact"
        hide-details
      />
      <div class="thread__actions">
        <v-btn
          size="small"
          color="primary"
          variant="flat"
          :disabled="!text.trim() || busy"
          data-testid="thread-send"
          @click="send"
        >
          {{ queries.length ? 'Reply' : 'Send query' }}
        </v-btn>
        <v-btn
          v-if="hasOpen"
          size="small"
          variant="text"
          :disabled="busy"
          data-testid="thread-resolve"
          @click="emit('resolve')"
        >
          Resolve
        </v-btn>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
  /** Queries and replies on one evidence item. Replies are further queries; resolving closes all open ones. */
  import { computed, ref } from 'vue'
  import { formatDateTime } from '@/utils/format'
  import type { Schema } from '@/types/api'

  const props = defineProps<{
    queries: Schema<'ReviewComment'>[]
    me: string
    creatorId: string
    canReply: boolean
    busy?: boolean
  }>()
  const emit = defineEmits<{ send: [string]; resolve: [] }>()

  const text = ref('')
  const hasOpen = computed(() => props.queries.some(q => q.status === 'open'))
  const author = (id: string) =>
    id === props.me ? 'You' : id === props.creatorId ? 'Curator' : 'Reviewer'

  function send() {
    emit('send', text.value.trim())
    text.value = ''
  }
</script>

<style scoped>
  .thread {
    margin-top: 8px;
    padding: 8px 12px;
    border-left: 2px solid rgb(var(--v-theme-secondary));
    font-size: 13px;
  }

  .thread__list {
    list-style: none;
    padding: 0;
    margin: 0 0 8px;
  }

  .thread__list li + li {
    margin-top: 8px;
  }

  .thread__author {
    margin-right: 8px;
  }

  .thread__resolved {
    opacity: 0.7;
  }

  .thread__actions {
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }
</style>
