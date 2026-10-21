<template>
  <BaseDialog
    :model-value="confirmState.open"
    :title="confirmState.title"
    size="sm"
    persistent
    @cancel="confirmState.settle(false)"
  >
    <span v-if="confirmState.text">{{ confirmState.text }}</span>
    <template #actions>
      <v-btn variant="text" @click="confirmState.settle(false)">Cancel</v-btn>
      <v-btn
        variant="flat"
        :color="confirmState.destructive ? 'error' : 'primary'"
        @click="confirmState.settle(true)"
      >
        {{ confirmState.confirmText }}
      </v-btn>
    </template>
  </BaseDialog>
</template>

<script setup lang="ts">
  import BaseDialog from '@/components/BaseDialog.vue'
  import { confirmState } from '@/composables/useConfirm'
</script>
