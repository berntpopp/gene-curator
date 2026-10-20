/**
 * Log Sanitization Utility for Gene Curator
 *
 * FIX #12: Added quick pre-check for performance optimization
 *
 * Provides privacy protection for sensitive genetic and medical data in logs.
 * Automatically redacts tokens, credentials, emails, phone numbers, genetic variants,
 * and other sensitive information before logging.
 *
 * Performance optimized with quick pre-checks before expensive regex operations.
 */

/**
 * Sensitive keys, compared against the lowercased key with `_`/`-` removed.
 * Suffix match catches `accessToken`/`user_email`; exact-only keys are too common as word
 * endings (`sortKey`, `monkey`, `userInput`) to match by suffix.
 */
const SENSITIVE_KEY_SUFFIXES: readonly string[] = [
  'token',
  'jwt',
  'password',
  'passwd',
  'apikey',
  'secretkey',
  'privatekey',
  'secret',
  'authorization',
  'credential',
  'credentials',
  'cookie',
  'session',
  'sessionid',
  'csrf',
  'email',
  'emailaddress',
  'phone',
  'phonenumber',
  'variant',
  'variants',
  'mutation',
  'mutations',
  'hgvs',
  'hgvsnotation'
]
const SENSITIVE_KEYS_EXACT: ReadonlySet<string> = new Set(['key', 'pwd', 'bearer', 'input', 'otp'])

function isSensitiveKey(key: string): boolean {
  const k = key.toLowerCase().replace(/[_-]/g, '')
  return SENSITIVE_KEYS_EXACT.has(k) || SENSITIVE_KEY_SUFFIXES.some(suffix => k.endsWith(suffix))
}

/**
 * Regex patterns for sensitive values
 * Each pattern includes a replacement string for redaction
 */
// Order matters: specific genetic patterns must run before the broad phone pattern, which would
// otherwise redact their digits (e.g. `chr7:100-200`, `c.123A>G`) as a phone number.
const SENSITIVE_VALUE_PATTERNS: readonly { pattern: RegExp; replacement: string }[] = [
  // Email patterns
  {
    pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    replacement: '[REDACTED_EMAIL]'
  },

  // HGVS notation for genetic variants (DNA level)
  { pattern: /\bc\.\d+[ACGT]>[ACGT]\b/g, replacement: '[REDACTED_VARIANT]' },
  { pattern: /\bc\.\d+_\d+del[ACGT]*\b/g, replacement: '[REDACTED_VARIANT]' },
  { pattern: /\bc\.\d+_\d+ins[ACGT]+\b/g, replacement: '[REDACTED_VARIANT]' },
  { pattern: /\bc\.\d+_\d+dup[ACGT]*\b/g, replacement: '[REDACTED_VARIANT]' },

  // HGVS notation for genetic variants (Protein level)
  { pattern: /\bp\.[A-Z][a-z]{2}\d+[A-Z][a-z]{2}\b/g, replacement: '[REDACTED_VARIANT]' },
  { pattern: /\bp\.[A-Z][a-z]{2}\d+\*/g, replacement: '[REDACTED_VARIANT]' },
  { pattern: /\bp\.[A-Z][a-z]{2}\d+fs/g, replacement: '[REDACTED_VARIANT]' },

  // Genomic coordinates (chr notation)
  { pattern: /\bchr\d{1,2}:\d+-\d+\b/g, replacement: '[REDACTED_COORDINATE]' },
  { pattern: /\bchrX:\d+-\d+\b/g, replacement: '[REDACTED_COORDINATE]' },
  { pattern: /\bchrY:\d+-\d+\b/g, replacement: '[REDACTED_COORDINATE]' },

  // Authorization header values
  { pattern: /\bBearer\s+\S+/gi, replacement: '[REDACTED_TOKEN]' },

  // JWT token patterns (three base64url segments, header always starts with eyJ)
  {
    pattern: /\beyJ[A-Za-z0-9-_]*\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]*/g,
    replacement: '[REDACTED_TOKEN]'
  },

  // API key patterns (common formats - long alphanumeric strings)
  {
    pattern: /\b[A-Za-z0-9]{32,}\b/g,
    replacement: '[REDACTED_KEY]'
  },

  // Phone patterns: a standalone run of 10+ digits/separators (not inside UUIDs or ids)
  {
    pattern: /(?<![\w-])\+?\d[\d\s().-]{8,}\d(?![\w-])/g,
    replacement: '[REDACTED_PHONE]'
  }
]

/**
 * FIX #12: Quick pre-check to skip expensive regex tests
 * Tests if value contains any characters that could indicate sensitive data
 * This dramatically improves performance for clean strings
 */
// No `g` flag: with `g`, .test() keeps lastIndex between calls and skips redaction on later strings
const QUICK_CHECK_PATTERN = /[@.:+-]|bearer/i

/**
 * Sanitizes an object for logging by redacting sensitive information
 *
 * Recursively processes objects and arrays, checking both keys and values
 * for sensitive information. Limits recursion depth to prevent stack overflow.
 *
 * @param obj - The object to sanitize
 * @param maxDepth - Maximum recursion depth (default: 5)
 * @returns Sanitized copy of the object
 *
 * @example
 * const data = { email: 'user@example.com', name: 'John' }
 * const sanitized = sanitizeForLogging(data)
 * // => { email: '[REDACTED_EMAIL]', name: 'John' }
 */
export function sanitizeForLogging(obj: unknown, maxDepth = 5): unknown {
  // Handle max depth to prevent infinite recursion
  if (maxDepth <= 0) {
    return '[MAX_DEPTH_EXCEEDED]'
  }

  // Handle null/undefined
  if (obj === null || obj === undefined) {
    return obj
  }

  // Handle primitives
  if (typeof obj !== 'object') {
    return sanitizeValue(obj)
  }

  // Error fields are non-enumerable and stacks leak paths: keep only name and message
  if (obj instanceof Error) {
    return { name: obj.name, message: sanitizeString(obj.message) }
  }

  // Handle arrays
  if (Array.isArray(obj)) {
    // Limit array size for performance (process max 100 items)
    return obj.slice(0, 100).map(item => sanitizeForLogging(item, maxDepth - 1))
  }

  // Handle objects
  const sanitized: Record<string, unknown> = {}

  for (const [key, value] of Object.entries(obj)) {
    if (isSensitiveKey(key)) {
      // Redact entire value if key is sensitive
      sanitized[key] = '[REDACTED_SENSITIVE]'
    } else if (typeof value === 'object' && value !== null) {
      // Recursively sanitize nested objects
      sanitized[key] = sanitizeForLogging(value, maxDepth - 1)
    } else {
      // Sanitize primitive values
      sanitized[key] = sanitizeValue(value)
    }
  }

  return sanitized
}

/**
 * Sanitizes primitive values by checking against sensitive patterns
 *
 * FIX #12: Added quick pre-check to avoid expensive regex tests on clean strings
 *
 * @param value - The value to sanitize
 * @returns Sanitized value
 *
 * @example
 * sanitizeValue('user@example.com') // => '[REDACTED_EMAIL]'
 * sanitizeValue('normal text') // => 'normal text'
 */
function sanitizeValue(value: unknown): unknown {
  if (typeof value !== 'string') {
    return value
  }
  return sanitizeString(value)
}

function sanitizeString(value: string): string {
  // FIX #12: Quick check - does string contain ANY special chars that could be sensitive?
  // This pre-check dramatically improves performance by skipping expensive regex tests
  // for strings that don't contain @, :, ., +, or - characters
  if (!QUICK_CHECK_PATTERN.test(value)) {
    // No special chars - skip expensive regex tests
    return value
  }

  let sanitized = value

  // Only run expensive regexes if quick check passed
  for (const { pattern, replacement } of SENSITIVE_VALUE_PATTERNS) {
    sanitized = sanitized.replace(pattern, replacement)
  }

  return sanitized
}

/**
 * Sanitizes log entry message and data
 *
 * Convenience function for sanitizing both message and data in one call.
 *
 * @param message - Log message
 * @param data - Optional data object
 * @returns Object with sanitized message and data
 *
 * @example
 * const { message, data } = sanitizeLogEntry('User login', { email: 'user@example.com' })
 * // => { message: 'User login', data: { email: '[REDACTED_EMAIL]' } }
 */
export function sanitizeLogEntry(
  message: string | null | undefined,
  data: unknown = null
): { message: string; data: unknown } {
  return {
    message: sanitizeString(message || ''),
    data: data ? sanitizeForLogging(data) : null
  }
}
