import { describe, expect, test } from 'vitest'

import { actionSchema } from './InspectionEdit'

describe('actionSchema', () => {
  test('requires assignee selection', () => {
    const result = actionSchema.safeParse({
      title: 'Fix ladder',
      description: 'Replace damaged rung',
      severity: 'medium',
      due_date: '',
      assigned_to_id: '',
    })

    expect(result.success).toBe(false)
  })

  test('keeps the selected assignee id', () => {
    const result = actionSchema.parse({
      title: 'Fix ladder',
      description: undefined,
      severity: 'high',
      due_date: '',
      assigned_to_id: 'user-1',
    })

    expect(result.assigned_to_id).toBe('user-1')
  })
})
