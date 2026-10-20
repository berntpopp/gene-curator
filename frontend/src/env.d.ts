/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  readonly VITE_APP_TITLE?: string
  readonly VITE_ENVIRONMENT?: string
  readonly VITE_ENABLE_DEV_LOGIN?: string
  readonly VITE_FEATURE_BREADCRUMBS?: string
  readonly VITE_FEATURE_INTERACTIVE_TOUR?: string
  readonly VITE_FEATURE_MOBILE_BOTTOM_NAV?: string
  readonly VITE_FEATURE_NEW_NAVIGATION?: string
  readonly VITE_FEATURE_NOTIFICATIONS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
