import { describe, it, expect } from 'vitest'
import { useRoleColors } from '../useRoleColors'

describe('useRoleColors', () => {
  it.each([
    ['admin', 'red', 'mdi-shield-crown'],
    ['curator', 'blue', 'mdi-pencil'],
    ['reviewer', 'green', 'mdi-check-circle'],
    ['viewer', 'grey', 'mdi-eye']
  ])('maps %s to colour %s and icon %s', (role, color, icon) => {
    const { getRoleColor, getRoleIcon } = useRoleColors()

    expect(getRoleColor(role)).toBe(color)
    expect(getRoleIcon(role)).toBe(icon)
  })

  it('falls back to grey colour and account icon for unknown roles', () => {
    const { getRoleColor, getRoleIcon } = useRoleColors()

    expect(getRoleColor('unknown')).toBe('grey')
    expect(getRoleIcon('unknown')).toBe('mdi-account')
  })

  it('exposes frozen colour and icon maps', () => {
    const { roleColors, roleIcons } = useRoleColors()

    expect(Object.isFrozen(roleColors)).toBe(true)
    expect(Object.isFrozen(roleIcons)).toBe(true)
    expect(roleColors.admin).toBe('red')
    expect(roleIcons.viewer).toBe('mdi-eye')
  })
})
