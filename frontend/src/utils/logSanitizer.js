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
 * Sensitive keys that should be redacted from logs
 * These patterns are checked against object keys (case-insensitive)
 */
const SENSITIVE_KEYS = [
  // Authentication and security
  'token',
  'accesstoken',
  'authtoken',
  'jwt',
  'password',
  'passwd',
  'pwd',
  'key',
  'apikey',
  'api_key',
  'secretkey',
  'secret_key',
  'privatekey',
  'private_key',
  'secret',
  'apisecret',
  'api_secret',
  'authorization',
  'bearer',
  'credential',
  'credentials',

  // User identifiers (privacy protection)
  'email',
  'emailaddress',
  'phone',
  'phonenumber',

  // Genetic data (privacy protection)
  'variant',
  'variants',
  'mutation',
  'mutations',
  'hgvs',
  'hgvs_notation'
]

/**
 * Regex patterns for sensitive values
 * Each pattern includes a replacement string for redaction
 */
const SENSITIVE_VALUE_PATTERNS = [
  // Email patterns
  {
    pattern: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/g,
    replacement: '[REDACTED_EMAIL]'
  },

  // Phone patterns (international formats)
  {
    pattern: /\b(?:\+?[1-9]\d{0,2}[\s.-]?)?\(?\d{1,4}\)?[\s.-]?\d{1,4}[\s.-]?\d{1,9}\b/g,
    replacement: '[REDACTED_PHONE]'
  },

  // JWT token patterns (three base64 segments separated by dots)
  {
    pattern: /\b[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\b/g,
    replacement: '[REDACTED_TOKEN]'
  },

  // API key patterns (common formats - long alphanumeric strings)
  {
    pattern: /\b[A-Za-z0-9]{32,}\b/g,
    replacement: '[REDACTED_KEY]'
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
  { pattern: /\bchrY:\d+-\d+\b/g, replacement: '[REDACTED_COORDINATE]' }
]

/**
 * FIX #12: Quick pre-check to skip expensive regex tests
 * Tests if value contains any characters that could indicate sensitive data
 * This dramatically improves performance for clean strings
 */
const QUICK_CHECK_PATTERN = /[@.:+-]/g

/**
 * Sanitizes an object for logging by redacting sensitive information
 *
 * Recursively processes objects and arrays, checking both keys and values
 * for sensitive information. Limits recursion depth to prevent stack overflow.
 *
 * @param {any} obj - The object to sanitize
 * @param {number} maxDepth - Maximum recursion depth (default: 5)
 * @returns {any} Sanitized copy of the object
 *
 * @example
 * const data = { email: 'user@example.com', name: 'John' }
 * const sanitized = sanitizeForLogging(data)
 * // => { email: '[REDACTED_EMAIL]', name: 'John' }
 */
export function sanitizeForLogging(obj, maxDepth = 5) {
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

  // Handle arrays
  if (Array.isArray(obj)) {
    // Limit array size for performance (process max 100 items)
    return obj.slice(0, 100).map(item => sanitizeForLogging(item, maxDepth - 1))
  }

  // Handle objects
  const sanitized = {}

  for (const [key, value] of Object.entries(obj)) {
    const lowerKey = key.toLowerCase().replace(/[_-]/g, '')

    // Check if key matches any sensitive key pattern
    const isSensitiveKey = SENSITIVE_KEYS.some(sensitiveKey =>
      lowerKey.includes(sensitiveKey.toLowerCase().replace(/[_-]/g, ''))
    )

    if (isSensitiveKey) {
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
 * @param {any} value - The value to sanitize
 * @returns {any} Sanitized value
 *
 * @example
 * sanitizeValue('user@example.com') // => '[REDACTED_EMAIL]'
 * sanitizeValue('normal text') // => 'normal text'
 */
function sanitizeValue(value) {
  if (typeof value !== 'string') {
    return value
  }

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
 * @param {string} message - Log message
 * @param {any} data - Optional data object
 * @returns {Object} Object with sanitized message and data
 *
 * @example
 * const { message, data } = sanitizeLogEntry('User login', { email: 'user@example.com' })
 * // => { message: 'User login', data: { email: '[REDACTED_EMAIL]' } }
 */
export function sanitizeLogEntry(message, data = null) {
  return {
    message: sanitizeValue(message || ''),
    data: data ? sanitizeForLogging(data) : null
  }
}

/**
 * Quick check to determine if a value contains potentially sensitive data
 *
 * Used for performance optimization - can skip sanitization if false.
 *
 * @param {any} value - Value to check
 * @returns {boolean} True if value might contain sensitive data
 *
 * @example
 * containsSensitiveData({ password: 'secret' }) // => true
 * containsSensitiveData({ name: 'John' }) // => false
 */
export function containsSensitiveData(value) {
  if (!value) return false

  const str = typeof value === 'string' ? value : JSON.stringify(value)
  const lowerStr = str.toLowerCase()

  // Quick check for common sensitive patterns
  const quickPatterns = ['password', 'token', 'email', 'phone', 'variant', 'mutation', 'hgvs']

  return quickPatterns.some(pattern => lowerStr.includes(pattern))
}

/**
 * Test if sanitization is working correctly
 * This function is exported for testing purposes
 *
 * @returns {boolean} True if all tests pass
 */
export function testSanitization() {
  const tests = [
    {
      input: 'user@example.com',
      expected: '[REDACTED_EMAIL]',
      description: 'Email sanitization'
    },
    {
      input: { token: 'secret123', name: 'John' },
      expected: { token: '[REDACTED_SENSITIVE]', name: 'John' },
      description: 'Object key sanitization'
    },
    {
      input: 'normal text without sensitive data',
      expected: 'normal text without sensitive data',
      description: 'Clean string (quick check optimization)'
    }
  ]

  let allPassed = true

  for (const test of tests) {
    const result =
      typeof test.input === 'string' ? sanitizeValue(test.input) : sanitizeForLogging(test.input)

    const passed = JSON.stringify(result) === JSON.stringify(test.expected)

    if (!passed) {
      console.error(`Test failed: ${test.description}`)
      console.error('Expected:', test.expected)
      console.error('Got:', result)
      allPassed = false
    }
  }

  return allPassed
}
