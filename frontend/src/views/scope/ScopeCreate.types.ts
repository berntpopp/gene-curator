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

export type ErrorLike = {
  message?: string
  stack?: string
  response?: { data?: { detail?: string; message?: string } }
}
