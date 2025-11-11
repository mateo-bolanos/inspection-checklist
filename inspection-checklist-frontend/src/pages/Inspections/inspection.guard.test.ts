import { describe, expect, test } from 'vitest'

import type { components } from '@/api/gen/schema'
import { evaluateInspectionSubmitState } from './InspectionEdit'

const template: components['schemas']['ChecklistTemplateRead'] = {
  id: 'tpl-1',
  name: 'Test',
  description: null,
  sections: [
    {
      id: 'sec-1',
      title: 'Section',
      order_index: 0,
      items: [
        { id: 'item-1', prompt: 'A', is_required: true, order_index: 0 },
        { id: 'item-2', prompt: 'B', is_required: false, order_index: 1 },
      ],
    },
  ],
}

describe('evaluateInspectionSubmitState', () => {
  test('detects missing required responses and failing items without actions', () => {
    const responses: components['schemas']['InspectionResponseRead'][] = [
      { id: 'resp-1', inspection_id: 1, template_item_id: 'item-2', result: 'fail', note: null, media_urls: [] },
    ]
    const actions: components['schemas']['CorrectiveActionRead'][] = []

    const result = evaluateInspectionSubmitState(template, responses, actions)

    expect(result.missingRequiredItems.map((item) => item.id)).toEqual(['item-1'])
    expect(result.failingResponses.map((response) => response.id)).toEqual(['resp-1'])
  })
})
