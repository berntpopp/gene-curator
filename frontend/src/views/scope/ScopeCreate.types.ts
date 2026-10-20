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
  is_active: boolean
  due_date: string | null
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
  role: string
}

// useLogger() and the composables are JS with JSDoc @returns {Object}; narrow locally
export interface LoggerApi {
  debug: (message: string, data?: Record<string, unknown>) => void
  info: (message: string, data?: Record<string, unknown>) => void
  warn: (message: string, data?: Record<string, unknown>) => void
  error: (message: string, data?: Record<string, unknown>) => void
}

// The scopes store is JS, so its state and actions are typed never / missing; narrow here
export interface ScopesStoreView {
  scopes: ScopeRecord[]
  fetchUserScopes: () => Promise<unknown>
  createScope: (data: ScopeFormData) => Promise<ScopeRecord>
  inviteMember: (scopeId: string, data: { user_id: string; role: string }) => Promise<unknown>
}

export type ErrorLike = {
  message?: string
  stack?: string
  response?: { data?: { detail?: string; message?: string } }
}
