import { reactive } from 'vue'

export interface SnackbarState {
  show: boolean
  message: string
  color: string
  timeout: number
}

export interface UseNotificationsReturn {
  snackbarState: SnackbarState
  showSnackbar: (message: string, color?: string, timeout?: number) => void
  showSuccess: (message: string, timeout?: number) => void
  showError: (message: string, timeout?: number) => void
  showWarning: (message: string, timeout?: number) => void
  showInfo: (message: string, timeout?: number) => void
}

// Global snackbar state management
export const snackbarState: SnackbarState = reactive({
  show: false,
  message: '',
  color: 'info',
  timeout: 5000
})

export const showSnackbar = (message: string, color = 'info', timeout = 5000): void => {
  snackbarState.message = message
  snackbarState.color = color
  snackbarState.timeout = timeout
  snackbarState.show = true
}

export const showSuccess = (message: string, timeout = 5000): void => {
  showSnackbar(message, 'success', timeout)
}

export const showError = (message: string, timeout = 8000): void => {
  showSnackbar(message, 'error', timeout)
}

export const showWarning = (message: string, timeout = 6000): void => {
  showSnackbar(message, 'warning', timeout)
}

export const showInfo = (message: string, timeout = 5000): void => {
  showSnackbar(message, 'info', timeout)
}

export const useNotifications = (): UseNotificationsReturn => {
  return {
    snackbarState,
    showSnackbar,
    showSuccess,
    showError,
    showWarning,
    showInfo
  }
}
