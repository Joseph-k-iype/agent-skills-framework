import { describe, it, expect } from 'vitest'
import { shortHash, formatDate, pluralize, classNames } from '../lib/utils'

describe('shortHash', () => {
  it('returns first 12 chars of hash segment', () => {
    const id = 'skill://sha256/23102ae16082e7abd7ed3cc087a654b18b581e64bf9015a97b11985b7f80ec0c/data-discovery@0.1.0'
    expect(shortHash(id)).toBe('23102ae16082')
  })

  it('returns full id if no hash segment', () => {
    expect(shortHash('no-slashes')).toBe('no-slashes')
  })
})

describe('formatDate', () => {
  it('formats a timestamp', () => {
    const result = formatDate('2024-01-15T00:00:00Z')
    expect(result).toContain('2024')
  })
})

describe('pluralize', () => {
  it('returns singular for 1', () => {
    expect(pluralize(1, 'skill')).toBe('1 skill')
  })

  it('returns plural for 0', () => {
    expect(pluralize(0, 'skill')).toBe('0 skills')
  })

  it('returns plural for >1', () => {
    expect(pluralize(3, 'skill')).toBe('3 skills')
  })

  it('uses custom plural', () => {
    expect(pluralize(2, 'version', 'versions')).toBe('2 versions')
  })
})

describe('classNames', () => {
  it('joins truthy classes', () => {
    expect(classNames('a', 'b', false, null, undefined, 'c')).toBe('a b c')
  })
})
