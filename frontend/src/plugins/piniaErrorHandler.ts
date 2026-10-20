/**
 * Pinia plugin: logs failed store actions and warns about slow ones (> 2s).
 * Never swallows errors; stores turn them into messages with `errorMessage` (stores/apiError).
 */

import type { PiniaPluginContext } from 'pinia'
import { logService } from '@/services/logService'
import { toApiError } from '@/stores/apiError'

const SLOW_ACTION_MS = 2000

export function piniaErrorHandlerPlugin({ store }: PiniaPluginContext): void {
  store.$onAction(({ name, store: actionStore, args, after, onError }) => {
    const startTime = Date.now()

    after(() => {
      const duration = Date.now() - startTime
      if (duration > SLOW_ACTION_MS) {
        logService.warn(`Slow action: ${actionStore.$id}.${name}`, {
          store: actionStore.$id,
          action: name,
          duration_ms: duration
        })
      }
    })

    onError(err => {
      const error = toApiError(err)
      logService.error(`Store action failed: ${actionStore.$id}.${name}`, {
        store: actionStore.$id,
        action: name,
        error_message: error.message,
        status: error.response?.status,
        duration_ms: Date.now() - startTime,
        args_count: args.length
      })
    })
  })
}

export default piniaErrorHandlerPlugin
