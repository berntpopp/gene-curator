import type { ScopeRole } from '@/stores/scopes'

// Types for ScopeCreate.vue (JS stores and composables are untyped; narrowed here)
export interface ScopeRecord {
  id: string
  name: string
}

export interface ScopeFormData {
  name: string
  display_name: string
  description: string
  institution: string
  is_public: boolean
  default_workflow_pair_id: string | null
}

export interface UserRecord {
  id: string
  name?: string | null
  email?: string
}

// Search result as shown in the autocomplete (item-title is displayName)
export type SearchUser = UserRecord & { displayName?: string | null }

export interface PendingMember {
  user: UserRecord
  role: ScopeRole
}

export type ErrorLike = {
  message?: string
  stack?: string
  response?: { data?: { detail?: string; message?: string } }
}
