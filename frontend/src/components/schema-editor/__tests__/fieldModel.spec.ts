import { describe, it, expect } from 'vitest'
import {
  fieldIds,
  formatValues,
  move,
  parseValues,
  readLayout,
  renumber,
  writeLayout
} from '../fieldModel'

describe('fieldModel', () => {
  it('reads the sections shape as is and writes it back with other keys kept', () => {
    const defs = {
      sections: [{ id: 's', label: 'S', fields: [{ id: 'a', type: 'text' }] }],
      note: 'kept'
    }
    const layout = readLayout(defs)
    expect(layout.sectioned).toBe(true)
    expect(fieldIds(layout)).toEqual(['a'])
    layout.sections[0]!.fields.push({ id: 'b', type: 'url' })
    expect(writeLayout(layout, defs)).toEqual({
      sections: [
        {
          id: 's',
          label: 'S',
          fields: [
            { id: 'a', type: 'text' },
            { id: 'b', type: 'url' }
          ]
        }
      ],
      note: 'kept'
    })
    expect(defs.sections[0]!.fields).toHaveLength(1) // the input is not mutated
  })

  it('starts an empty schema as sections', () => {
    expect(readLayout({})).toEqual({ sectioned: true, sections: [] })
    expect(readLayout(null)).toEqual({ sectioned: true, sections: [] })
  })

  it('reads a flat map as one section sorted by order and writes it back flat', () => {
    const defs = {
      b: { type: 'text', order: 2 },
      a: { type: 'number', order: 1 },
      c: { type: 'x' }
    }
    const layout = readLayout(defs)
    expect(layout.sectioned).toBe(false)
    expect(fieldIds(layout)).toEqual(['a', 'b', 'c'])
    expect(writeLayout(layout, defs)).toEqual(defs)
    move(layout.sections[0]!.fields, 2, -2)
    renumber(layout)
    expect(writeLayout(layout, defs)).toEqual({
      c: { type: 'x', order: 1 },
      a: { type: 'number', order: 2 },
      b: { type: 'text', order: 3 }
    })
  })

  it('keeps non-field entries of a flat map', () => {
    const defs = { a: { type: 'text' }, version_note: 'v1' }
    expect(writeLayout(readLayout(defs), defs)).toEqual(defs)
  })

  it('moves within bounds only and renumbers flat maps only', () => {
    const list = [1, 2, 3]
    move(list, 0, -1)
    move(list, 2, 1)
    expect(list).toEqual([1, 2, 3])
    move(list, 0, 1)
    expect(list).toEqual([2, 1, 3])
    const sectioned = readLayout({ sections: [{ id: 's', fields: [{ id: 'a' }] }] })
    renumber(sectioned)
    expect(sectioned.sections[0]!.fields[0]).toEqual({ id: 'a' })
  })

  it('parses condition values as JSON scalars, else text; one value stays scalar', () => {
    expect(parseValues('AD')).toBe('AD')
    expect(parseValues('true')).toBe(true)
    expect(parseValues('AD, AR, 3')).toEqual(['AD', 'AR', 3])
    expect(parseValues('{"a":1}, [1]')).toEqual(['{"a":1}', '[1]'])
    expect(parseValues(' , ')).toEqual([])
    expect(formatValues(['AD', true])).toBe('AD, true')
    expect(formatValues('x')).toBe('x')
  })
})
