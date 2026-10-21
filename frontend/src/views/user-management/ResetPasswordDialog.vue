<template>
  <BaseDialog v-if="user" v-model="open" size="sm">
    <template #title>Reset password for {{ user.name }}</template>
    <v-form ref="form" @submit.prevent="submit">
      <v-text-field
        v-model="password"
        label="New password"
        type="password"
        autocomplete="new-password"
        :rules="passwordRules"
        variant="outlined"
        :hint="`${PASSWORD_MIN_LENGTH}-${PASSWORD_MAX_LENGTH} characters`"
      />
      <v-text-field
        v-model="confirm"
        label="Confirm password"
        type="password"
        autocomplete="new-password"
        :rules="[matches]"
        variant="outlined"
      />
    </v-form>
    <template #actions>
      <v-btn variant="text" @click="open = false"> Cancel </v-btn>
      <v-btn color="primary" @click="submit"> Reset </v-btn>
    </template></BaseDialog
  >
</template>

<script setup lang="ts">
  import { ref, watch } from 'vue'
  import { passwordRules, PASSWORD_MIN_LENGTH, PASSWORD_MAX_LENGTH } from '@/config/password'
  import type { UserRecord } from '@/views/user-management/userManagementHelpers'
  import BaseDialog from '@/components/BaseDialog.vue'

  defineProps<{ user: UserRecord | null }>()
  const emit = defineEmits<{ submit: [password: string] }>()
  const open = defineModel<boolean>({ required: true })

  const form = ref<{ validate: () => Promise<{ valid: boolean }> } | null>(null)
  const password = ref('')
  const confirm = ref('')

  const matches = (v: string) => v === password.value || 'Passwords do not match'

  // Never keep a typed password around after the dialog closes
  watch(open, () => {
    password.value = ''
    confirm.value = ''
  })

  async function submit() {
    const result = await form.value?.validate()
    if (result?.valid) emit('submit', password.value)
  }
</script>
