import { reactive } from 'vue'

export interface ConfirmOptions {
  title: string
  text?: string
  confirmText?: string
  destructive?: boolean
}

let resolver: ((value: boolean) => void) | null = null

// Single shared dialog state; ConfirmDialog (mounted once in App.vue) renders it.
export const confirmState = reactive({
  open: false,
  title: '',
  text: '',
  confirmText: 'Confirm',
  destructive: false,
  settle(value: boolean) {
    this.open = false
    resolver?.(value)
    resolver = null
  }
})

export function useConfirm() {
  const confirm = (options: ConfirmOptions): Promise<boolean> => {
    confirmState.settle(false) // a still-pending confirmation counts as cancelled
    Object.assign(confirmState, {
      open: true,
      text: '',
      confirmText: 'Confirm',
      destructive: false,
      ...options
    })
    return new Promise<boolean>(resolve => {
      resolver = resolve
    })
  }
  return { confirm }
}
