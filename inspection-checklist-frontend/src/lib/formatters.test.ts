import { describe, expect, test } from 'vitest'

import { capitalize, formatDate, formatScore } from './formatters'

describe('formatters', () => {
  test('formatDate returns placeholder when value missing', () => {
    expect(formatDate(null)).toBe('—')
  })

  test('formatScore prints percentage', () => {
    expect(formatScore(0.756, 2)).toBe('0.76%')
  })

  test('capitalize capitalizes first letter', () => {
    expect(capitalize('status')).toBe('Status')
  })
})
