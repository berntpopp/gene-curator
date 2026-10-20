/**
 * ConflictResolutionDialog Component Tests
 *
 * @see src/components/ConflictResolutionDialog.vue
 */

import { describe, it, expect, afterEach } from 'vitest'
import { mount, type VueWrapper } from '@vue/test-utils'
import ConflictResolutionDialog from '../ConflictResolutionDialog.vue'
import { installVisualViewport } from './overlay-env'

installVisualViewport()

let wrapper: VueWrapper | undefined

function mountDialog(props: Record<string, unknown>) {
  wrapper = mount(ConflictResolutionDialog, {
    props: { modelValue: true, ...props },
    attachTo: document.body
  })
  return wrapper
}

function clickButton(text: string) {
  const button = Array.from(document.querySelectorAll('button')).find(b =>
    b.textContent?.includes(text)
  )
  button?.click()
}

describe('ConflictResolutionDialog', () => {
  afterEach(() => {
    wrapper?.unmount()
    wrapper = undefined
    document.body.innerHTML = ''
  })

  it('shows both sides of the conflict as JSON without metadata fields', () => {
    mountDialog({
      yourChanges: { name: 'Mine', lock_version: 3, updated_at: 'x' },
      theirChanges: { name: 'Theirs', updated_by: 'someone' }
    })

    const text = document.body.textContent ?? ''
    expect(text).toContain('"name": "Mine"')
    expect(text).toContain('"name": "Theirs"')
    expect(text).not.toContain('lock_version')
    expect(text).not.toContain('updated_by')
  })

  it('shows "No data" when a side is missing', () => {
    mountDialog({ yourChanges: null, theirChanges: { name: 'Theirs' } })

    expect(document.body.textContent).toContain('No data')
  })

  it('lists conflicted fields only when there are some', () => {
    mountDialog({ conflictedFields: ['symbol', 'location'] })

    expect(document.body.textContent).toContain('symbol, location')
  })

  it('omits the conflicted-fields notice when the list is empty', () => {
    mountDialog({ conflictedFields: [] })

    expect(document.body.textContent).not.toContain('Conflicted fields')
  })

  it('emits the chosen resolution', () => {
    const w = mountDialog({})

    clickButton('Discard My Changes')
    clickButton('Overwrite Their Changes')
    clickButton('Merge Manually')
    clickButton('Cancel')

    expect(w.emitted('resolve')).toEqual([['discard-mine'], ['overwrite-theirs'], ['merge']])
    expect(w.emitted('cancel')).toHaveLength(1)
  })
})
