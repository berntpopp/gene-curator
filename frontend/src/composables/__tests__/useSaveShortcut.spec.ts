import { describe, it, expect, vi, afterEach } from 'vitest'
import { createApp, defineComponent, h } from 'vue'
import { useSaveShortcut } from '../useSaveShortcut'

function mountShortcut(save: () => unknown, enabled = () => true) {
  const app = createApp(
    defineComponent({
      setup() {
        useSaveShortcut(save, enabled)
        return () => h('div')
      }
    })
  )
  app.mount(document.createElement('div'))
  return app
}

function press(target: Element | Document, init: KeyboardEventInit = {}) {
  const event = new KeyboardEvent('keydown', {
    key: 's',
    ctrlKey: true,
    bubbles: true,
    cancelable: true,
    ...init
  })
  target.dispatchEvent(event)
  return event
}

afterEach(() => (document.body.innerHTML = ''))

describe('useSaveShortcut', () => {
  // #469: a focused cell commits its typed text on blur; the save must include it
  it('blurs the focused field before saving', () => {
    const input = document.body.appendChild(document.createElement('input'))
    let committed = false
    input.addEventListener('blur', () => (committed = true))
    input.focus()
    let committedAtSave = false
    const app = mountShortcut(() => (committedAtSave = committed))
    press(input)
    app.unmount()
    expect(committedAtSave).toBe(true)
  })

  it('saves on Ctrl+S and Cmd+S and stops the browser save-page dialog', () => {
    const save = vi.fn()
    mountShortcut(save)
    expect(press(document.body).defaultPrevented).toBe(true)
    press(document.body, { ctrlKey: false, metaKey: true })
    expect(save).toHaveBeenCalledTimes(2)
  })

  it('works while typing in an input', () => {
    const save = vi.fn()
    mountShortcut(save)
    const input = document.createElement('input')
    document.body.append(input)
    input.focus()
    press(input)
    expect(save).toHaveBeenCalledTimes(1)
  })

  it('does nothing inside a dialog', () => {
    const save = vi.fn()
    mountShortcut(save)
    const dialog = document.createElement('div')
    dialog.setAttribute('role', 'dialog')
    const input = document.createElement('input')
    dialog.append(input)
    document.body.append(dialog)
    const event = press(input)
    expect(save).not.toHaveBeenCalled()
    // the browser's save-page dialog is still suppressed
    expect(event.defaultPrevented).toBe(true)
  })

  it('ignores other keys and modifiers without touching them', () => {
    const save = vi.fn()
    mountShortcut(save)
    for (const init of [{ key: 'a' }, { shiftKey: true }, { altKey: true }, { ctrlKey: false }]) {
      expect(press(document.body, init).defaultPrevented).toBe(false)
    }
    expect(save).not.toHaveBeenCalled()
  })

  it('does not save on key repeat but still suppresses the browser dialog', () => {
    const save = vi.fn()
    mountShortcut(save)
    expect(press(document.body, { repeat: true }).defaultPrevented).toBe(true)
    expect(save).not.toHaveBeenCalled()
  })

  it('suppresses the browser dialog while disabled too', () => {
    const save = vi.fn()
    mountShortcut(save, () => false)
    expect(press(document.body).defaultPrevented).toBe(true)
    expect(save).not.toHaveBeenCalled()
  })

  it('is inert while disabled and detaches on unmount', () => {
    const save = vi.fn()
    let on = false
    const app = mountShortcut(save, () => on)
    press(document.body)
    expect(save).not.toHaveBeenCalled()
    on = true
    press(document.body)
    expect(save).toHaveBeenCalledTimes(1)
    app.unmount()
    press(document.body)
    expect(save).toHaveBeenCalledTimes(1)
  })
})
