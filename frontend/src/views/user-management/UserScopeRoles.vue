<template>
  <div data-testid="scope-roles">
    <div class="text-title-small mb-1">Scope roles</div>
    <p class="text-body-small text-medium-emphasis mb-3">
      {{
        disabled
          ? 'You cannot change your own scope roles.'
          : 'Takes effect immediately; no invitation to accept.'
      }}
    </p>
    <div v-for="r in roles" :key="r.scope_id" class="d-flex align-center ga-2 mb-2">
      <span class="flex-grow-1">{{ r.scope_name }}</span>
      <v-select
        :model-value="r.role"
        :items="SCOPE_ROLES"
        :aria-label="`Role in ${r.scope_name}`"
        :disabled="disabled || busy"
        :data-testid="`role-${r.scope_id}`"
        density="compact"
        variant="outlined"
        hide-details
        style="max-width: 160px"
        @update:model-value="
          run(
            () => scopes.updateMemberRole(r.scope_id, userId, $event),
            `Role in ${r.scope_name} set to ${$event}`
          )
        "
      />
      <v-btn
        icon="mdi-close"
        size="small"
        variant="text"
        :aria-label="`Remove from ${r.scope_name}`"
        :disabled="disabled || busy"
        :data-testid="`remove-${r.scope_id}`"
        @click="run(() => scopes.removeMember(r.scope_id, userId), `Removed from ${r.scope_name}`)"
      />
    </div>
    <div class="d-flex align-center ga-2">
      <v-select
        v-model="scopeId"
        :items="freeScopes"
        item-value="id"
        item-title="name"
        label="Add to scope"
        :disabled="disabled || busy"
        density="compact"
        variant="outlined"
        hide-details
        data-testid="grant-scope"
      />
      <v-select
        v-model="role"
        :items="SCOPE_ROLES"
        label="Role"
        :disabled="disabled || busy"
        density="compact"
        variant="outlined"
        hide-details
        style="max-width: 160px"
        data-testid="grant-role"
      />
      <v-btn
        color="primary"
        variant="tonal"
        :disabled="disabled || busy || !scopeId"
        data-testid="grant"
        @click="grant"
      >
        Add
      </v-btn>
    </div>
  </div>
</template>

<script setup lang="ts">
  /**
   * Scope memberships of one user in the Edit User dialog. Grants are direct adds
   * (POST /scopes/{id}/members): accepted at once, audited, and the user is notified.
   */
  import { computed, ref } from 'vue'
  import { useScopesStore, type ScopeRecord, type ScopeRole } from '@/stores/scopes'
  import { showSnackbar } from '@/composables/useNotifications'
  import { readableApiError } from '@/utils/apiErrorText'
  import type { UserScopeRole } from './useUserScopeRoles'

  const props = defineProps<{
    userId: string
    roles: UserScopeRole[]
    allScopes: ScopeRecord[]
    disabled?: boolean
  }>()
  const emit = defineEmits<{ changed: [] }>()

  const SCOPE_ROLES: ScopeRole[] = ['admin', 'curator', 'reviewer', 'viewer']
  const scopes = useScopesStore()
  const busy = ref(false)
  const scopeId = ref<string | null>(null)
  const role = ref<ScopeRole>('curator')

  const freeScopes = computed(() =>
    props.allScopes.filter(s => !props.roles.some(r => r.scope_id === s.id))
  )

  async function run(action: () => Promise<unknown>, done: string): Promise<boolean> {
    busy.value = true
    try {
      await action()
      showSnackbar(done, 'success')
      emit('changed')
      return true
    } catch (e) {
      showSnackbar(readableApiError(e, 'Could not change the scope role'), 'error')
      return false
    } finally {
      busy.value = false
    }
  }

  async function grant() {
    const scope = props.allScopes.find(s => s.id === scopeId.value)
    if (!scope) return
    const ok = await run(
      () => scopes.inviteMember(scope.id, { user_id: props.userId, role: role.value }, true),
      `Added to ${scope.name} as ${role.value}`
    )
    if (ok) scopeId.value = null
  }
</script>
