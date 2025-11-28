import { describe, expect, test } from 'vitest'

import type { components } from '@/api/gen/schema'
import { evaluateInspectionSubmitState } from './inspectionSubmitState'

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
        { id: 'item-1', prompt: 'A', is_required: true, requires_evidence_on_fail: true, order_index: 0 },
        { id: 'item-2', prompt: 'B', is_required: false, requires_evidence_on_fail: true, order_index: 1 },
      ],
    },
  ],
}

const buildUser = (): components['schemas']['UserRead'] => ({
  id: 'user-1',
  email: 'user@example.com',
  full_name: 'Test User',
  role: 'inspector',
})

const buildAction = (
  overrides: Partial<components['schemas']['CorrectiveActionRead']> = {},
): components['schemas']['CorrectiveActionRead'] => ({
  id: 1,
  inspection_id: 1,
  response_id: 'resp-1',
  title: 'Action',
  description: null,
  severity: 'high',
  due_date: null,
  assigned_to_id: null,
  status: 'open',
  work_order_required: false,
  work_order_number: null,
  assignee: null,
  created_at: new Date().toISOString(),
  closed_at: null,
  resolution_notes: null,
  started_by: buildUser(),
  closed_by: null,
  media_urls: [],
  ...overrides,
})

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

  test('requires attachments for failed responses even when an action exists', () => {
    const responses: components['schemas']['InspectionResponseRead'][] = [
      { id: 'resp-1', inspection_id: 1, template_item_id: 'item-1', result: 'fail', note: null, media_urls: [] },
    ]
    const actions = [buildAction()]

    const result = evaluateInspectionSubmitState(template, responses, actions)

    expect(result.failingResponses.map((response) => response.id)).toEqual(['resp-1'])
  })

  test('passes when evidence is attached to the response or action', () => {
    const responseWithMedia: components['schemas']['InspectionResponseRead'] = {
      id: 'resp-1',
      inspection_id: 1,
      template_item_id: 'item-1',
      result: 'fail',
      note: null,
      media_urls: ['file.png'],
    }
    const responseWithoutMedia: components['schemas']['InspectionResponseRead'] = {
      id: 'resp-2',
      inspection_id: 1,
      template_item_id: 'item-2',
      result: 'fail',
      note: null,
      media_urls: [],
    }
    const actions = [
      buildAction({ response_id: 'resp-1' }),
      buildAction({ id: 2, response_id: 'resp-2', media_urls: ['action-file.png'] }),
    ]

    const result = evaluateInspectionSubmitState(template, [responseWithMedia, responseWithoutMedia], actions)

    expect(result.failingResponses).toHaveLength(0)
  })

  test('skips evidence requirement when template item disables it', () => {
    const [firstSection] = template.sections ?? []
    if (!firstSection) {
      throw new Error('Test template is missing sections')
    }
    const relaxedTemplate: components['schemas']['ChecklistTemplateRead'] = {
      ...template,
      sections: [
        {
          ...firstSection,
          items: [
            { ...(firstSection.items?.[0] ?? template.sections?.[0].items?.[0]), requires_evidence_on_fail: false },
            ...(firstSection.items?.[1] ? [firstSection.items[1]] : []),
          ].filter(Boolean) as components['schemas']['TemplateItemRead'][],
        },
      ],
    }
    const responses: components['schemas']['InspectionResponseRead'][] = [
      { id: 'resp-1', inspection_id: 1, template_item_id: 'item-1', result: 'fail', note: null, media_urls: [] },
    ]

    const result = evaluateInspectionSubmitState(relaxedTemplate, responses, [])

    expect(result.failingResponses).toHaveLength(0)
  })
})
