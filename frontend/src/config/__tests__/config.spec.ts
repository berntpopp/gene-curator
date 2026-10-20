import { describe, it, expect } from 'vitest'
import terminologyDefault, { TERMINOLOGY, getTermLabel, isDeprecated } from '../terminology'
import navigationDefault, {
  NAVIGATION_CONFIG,
  FEATURE_FLAGS,
  MENU_DIVIDERS,
  isFeatureEnabled
} from '../navigation'

describe('terminology', () => {
  it('returns the display label for a known key', () => {
    expect(getTermLabel('ASSIGNMENT')).toBe(TERMINOLOGY.ASSIGNMENT)
    expect(getTermLabel('COMPLETED')).toBe('Completed')
  })

  it('falls back to the key itself for unknown terms', () => {
    expect(getTermLabel('NOT_A_TERM')).toBe('NOT_A_TERM')
  })

  it('flags deprecated terminology keys only', () => {
    expect(isDeprecated('GENE_ASSIGNMENT')).toBe(true)
    expect(isDeprecated('BROWSE')).toBe(true)
    expect(isDeprecated('ASSIGNMENT')).toBe(false)
  })

  it('default export is the terminology table', () => {
    expect(terminologyDefault).toBe(TERMINOLOGY)
  })
})

describe('navigation config', () => {
  it('defines the menu limits and breakpoints', () => {
    expect(NAVIGATION_CONFIG.MAX_MAIN_MENU_ITEMS).toBe(6)
    expect(NAVIGATION_CONFIG.MOBILE_BREAKPOINT).toBeLessThan(NAVIGATION_CONFIG.TABLET_BREAKPOINT)
    expect(NAVIGATION_CONFIG.MIN_TOUCH_TARGET_SIZE).toBe(44)
  })

  it('lists the divider positions for the user menu', () => {
    expect(MENU_DIVIDERS.userMenu.map(d => d.after)).toEqual([
      'profile',
      'validation',
      'curation-setup'
    ])
  })

  it('reads feature flags from the environment with the documented defaults', () => {
    expect(FEATURE_FLAGS.NEW_NAVIGATION).toBe(
      import.meta.env.VITE_FEATURE_NEW_NAVIGATION !== 'false'
    )
    expect(FEATURE_FLAGS.INTERACTIVE_TOUR).toBe(
      import.meta.env.VITE_FEATURE_INTERACTIVE_TOUR === 'true'
    )
  })

  it('isFeatureEnabled reports the flag value and treats unknown flags as disabled', () => {
    expect(isFeatureEnabled('NOTIFICATIONS')).toBe(FEATURE_FLAGS.NOTIFICATIONS)
    expect(isFeatureEnabled('UNKNOWN_FLAG' as never)).toBe(false)
  })

  it('default export bundles every named export', () => {
    expect(navigationDefault.NAVIGATION_CONFIG).toBe(NAVIGATION_CONFIG)
    expect(navigationDefault.FEATURE_FLAGS).toBe(FEATURE_FLAGS)
    expect(navigationDefault.isFeatureEnabled).toBe(isFeatureEnabled)
  })
})
