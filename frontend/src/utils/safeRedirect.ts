/** Return `value` if it is a same-origin path, else undefined (blocks open redirects). */
export function safeRedirect(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined
  let decoded: string
  try {
    decoded = decodeURIComponent(value)
    // a second decode catches double-encoded slashes (%252F)
    decoded = decodeURIComponent(decoded)
  } catch {
    return undefined
  }
  const ok = (s: string) => /^\/(?![/\\])/.test(s) && !/[\t\n\r]/.test(s)
  return ok(value) && ok(decoded) ? value : undefined
}
