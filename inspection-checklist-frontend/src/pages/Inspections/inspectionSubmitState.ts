import type { components } from '@/api/gen/schema'

type TemplateRead = components['schemas']['ChecklistTemplateRead']
type TemplateItem = components['schemas']['TemplateItemRead']
export type InspectionResponse = components['schemas']['InspectionResponseRead']
type CorrectiveAction = components['schemas']['CorrectiveActionRead']

export type SubmitGuardResult = {
  missingRequiredItems: TemplateItem[]
  failingResponses: InspectionResponse[]
}

export const evaluateInspectionSubmitState = (
  template: TemplateRead,
  responses: InspectionResponse[],
  actions: CorrectiveAction[],
): SubmitGuardResult => {
  const templateItems = template.sections?.flatMap((section) => section.items ?? []) ?? []
  const requiredItems = templateItems.filter((item) => item.is_required)
  const templateItemsById = new Map(templateItems.map((item) => [item.id, item]))
  const responseMap = new Map(responses.map((response) => [response.template_item_id, response]))
  const missingRequiredItems = requiredItems.filter((item) => {
    const response = responseMap.get(item.id)
    return !response?.result
  })
  const failingResponses = responses.filter((response) => {
    if (response.result !== 'fail') return false
    const templateItem = templateItemsById.get(response.template_item_id)
    const requiresEvidence = templateItem?.requires_evidence_on_fail !== false
    if (!requiresEvidence) return false
    const relatedActions = actions.filter((action) => action.response_id === response.id)
    if (relatedActions.length === 0) return true
    const responseHasMedia = (response.media_urls?.length ?? 0) > 0
    const actionHasMedia = relatedActions.some((action) => (action.media_urls?.length ?? 0) > 0)
    return !(responseHasMedia || actionHasMedia)
  })
  return { missingRequiredItems, failingResponses }
}
