import { describe, it, expect } from 'vitest'
import { useConfirm, confirmState } from '../useConfirm'

describe('useConfirm', () => {
  it('opens the dialog with the options and resolves true on accept', async () => {
    const { confirm } = useConfirm()
    const result = confirm({ title: 'Delete?', destructive: true })

    expect(confirmState.open).toBe(true)
    expect(confirmState.title).toBe('Delete?')
    expect(confirmState.destructive).toBe(true)
    confirmState.settle(true)

    expect(await result).toBe(true)
    expect(confirmState.open).toBe(false)
  })

  it('resolves false on cancel (also what Escape does)', async () => {
    const result = useConfirm().confirm({ title: 'Discard?' })
    confirmState.settle(false)
    expect(await result).toBe(false)
  })

  it('resolves a still-pending confirmation as false when another opens', async () => {
    const { confirm } = useConfirm()
    const first = confirm({ title: 'A' })
    const second = confirm({ title: 'B' })
    expect(await first).toBe(false)
    confirmState.settle(true)
    expect(await second).toBe(true)
  })
})
