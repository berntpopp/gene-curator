/**
 * UUID Generation Polyfill for Browser Compatibility
 *
 * FIX #6: crypto.randomUUID() not available in Safari < 15.4 and older Chrome
 *
 * Provides a fallback implementation for generating RFC 4122 v4 UUIDs
 * in browsers that don't support the native crypto.randomUUID() API.
 */

/**
 * Generate a v4 UUID with fallback for older browsers
 *
 * Uses native crypto.randomUUID() if available, otherwise falls back
 * to a Math.random()-based implementation following RFC 4122.
 *
 * @returns {string} UUID v4 string (format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx)
 *
 * @example
 * const id = generateUUID()
 * // => '550e8400-e29b-41d4-a716-446655440000'
 */
export function generateUUID() {
  // Use native crypto.randomUUID() if available (modern browsers)
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  // Fallback implementation for older browsers
  // RFC 4122 v4 UUID: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
  // where y is one of [8, 9, A, B]
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0
    const v = c === 'x' ? r : (r & 0x3) | 0x8
    return v.toString(16)
  })
}

/**
 * Check if native UUID generation is available
 *
 * @returns {boolean} True if crypto.randomUUID() is available
 */
export function isNativeUUIDAvailable() {
  return typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
}
