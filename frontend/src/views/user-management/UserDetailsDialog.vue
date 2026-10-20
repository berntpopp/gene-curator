<template>
  <v-dialog v-model="open" max-width="800">
    <v-card v-if="user">
      <v-card-title class="text-h5"> User Details: {{ user.name }} </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <v-list>
              <v-list-item>
                <template #prepend>
                  <v-icon>mdi-email</v-icon>
                </template>
                <v-list-item-title>{{ user.email }}</v-list-item-title>
                <v-list-item-subtitle>Email</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template #prepend>
                  <v-icon>mdi-shield-account</v-icon>
                </template>
                <v-list-item-title>
                  <v-chip :color="getRoleColor(user.role)" size="small">
                    {{ user.role }}
                  </v-chip>
                </v-list-item-title>
                <v-list-item-subtitle>Role</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template #prepend>
                  <v-icon>mdi-clock</v-icon>
                </template>
                <v-list-item-title>{{ formatDate(user.created_at) }}</v-list-item-title>
                <v-list-item-subtitle>Created</v-list-item-subtitle>
              </v-list-item>
              <v-list-item>
                <template #prepend>
                  <v-icon>mdi-login</v-icon>
                </template>
                <v-list-item-title>
                  {{ user.last_login ? formatDate(user.last_login) : 'Never' }}
                </v-list-item-title>
                <v-list-item-subtitle>Last Login</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-col>
          <v-col v-if="activity" cols="12" md="6">
            <h3 class="mb-3">Activity Summary</h3>
            <v-list>
              <v-list-item>
                <v-list-item-title>{{ activity.scope_count ?? 0 }}</v-list-item-title>
                <v-list-item-subtitle>Scopes</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-col>
        </v-row>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="open = false"> Close </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup lang="ts">
  import {
    formatDate,
    getRoleColor,
    type UserRecord
  } from '@/views/user-management/userManagementHelpers'

  defineProps<{
    user: UserRecord | null
    activity: Record<string, unknown> | null
  }>()

  const open = defineModel<boolean>({ required: true })
</script>
