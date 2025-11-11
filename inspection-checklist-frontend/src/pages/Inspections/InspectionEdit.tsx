import { zodResolver } from '@hookform/resolvers/zod'
import { ImagePlus, Save } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useParams } from 'react-router-dom'
import { z } from 'zod'

import {
  useActionsQuery,
  useApproveInspectionMutation,
  useCreateActionMutation,
  useInspectionQuery,
  useSubmitInspectionMutation,
  useTemplateQuery,
  useUpdateInspectionMutation,
  useUploadMediaMutation,
  useUpsertResponseMutation,
} from '@/api/hooks'
import type { components } from '@/api/gen/schema'
import { ACTION_SEVERITIES, INSPECTION_RESULTS } from '@/lib/constants'
import { formatDateTime } from '@/lib/formatters'
import { useAuth } from '@/auth/useAuth'
import { FormField } from '@/components/forms/FormField'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { Badge } from '@/components/ui/Badge'
import { useToast } from '@/components/ui/Toast'
import { EmptyState } from '@/components/feedback/EmptyState'
import { LoadingState } from '@/components/feedback/LoadingState'

const actionSchema = z.object({
  title: z.string().min(3),
  description: z.string().optional(),
  severity: z.enum(ACTION_SEVERITIES),
  due_date: z.string().optional(),
})

type ActionFormValues = z.infer<typeof actionSchema>

type ResponseDraft = {
  result?: string
  note?: string
}

export const InspectionEditPage = () => {
  const { inspectionId: inspectionIdParam } = useParams<{ inspectionId: string }>()
  const parsedInspectionId = inspectionIdParam ? Number(inspectionIdParam) : undefined
  const numericInspectionId = Number.isFinite(parsedInspectionId) ? parsedInspectionId : undefined
  const inspectionResourceId = numericInspectionId ?? inspectionIdParam
  const inspectionQuery = useInspectionQuery(inspectionResourceId)
  const inspection = inspectionQuery.data
  const inspectionResponses = inspection?.responses ?? []
  const templateQuery = useTemplateQuery(inspection?.template_id)
  const template = templateQuery.data
  const actionsQuery = useActionsQuery()
  const resolvedInspectionId = inspection?.id ?? numericInspectionId
  const inspectionActions = useMemo(() => {
    if (resolvedInspectionId === undefined) return []
    return actionsQuery.data?.filter((action) => action.inspection_id === resolvedInspectionId) ?? []
  }, [actionsQuery.data, resolvedInspectionId])

  const upsertResponse = useUpsertResponseMutation(inspectionResourceId ?? '')
  const uploadMedia = useUploadMediaMutation()
  const updateInspection = inspectionResourceId ? useUpdateInspectionMutation(inspectionResourceId) : null
  const submitInspection = useSubmitInspectionMutation()
  const approveInspection = useApproveInspectionMutation()
  const createAction = useCreateActionMutation()
  const { push } = useToast()
  const { hasRole } = useAuth()
  const canApprove = hasRole(['admin', 'reviewer'])

  const [drafts, setDrafts] = useState<Record<string, ResponseDraft>>({})
  const [activeActionItem, setActiveActionItem] = useState<string | null>(null)

  const actionForm = useForm<ActionFormValues>({
    resolver: zodResolver(actionSchema),
    defaultValues: { title: '', description: '', severity: 'medium', due_date: '' },
  })

  const [localResponses, setLocalResponses] = useState<Record<string, InspectionResponse>>({})

  const previousInspectionId = useRef<number | null>(null)

  useEffect(() => {
    if (!inspection) return

    const responses = inspection.responses ?? []
    setDrafts((currentDrafts) => {
      const isSameInspection = previousInspectionId.current === inspection.id
      const mergedDrafts: Record<string, ResponseDraft> = isSameInspection ? { ...currentDrafts } : {}

      responses.forEach((response) => {
        const serverDraft = { result: response.result, note: response.note ?? '' }
        const existingDraft = currentDrafts[response.template_item_id]
        const hasUnsavedChanges =
          isSameInspection &&
          existingDraft &&
          (existingDraft.result !== serverDraft.result || (existingDraft.note ?? '') !== (serverDraft.note ?? ''))

        if (!hasUnsavedChanges) {
          mergedDrafts[response.template_item_id] = serverDraft
        }
      })

      return mergedDrafts
    })
    setLocalResponses({})
    previousInspectionId.current = inspection.id ?? null
  }, [inspection])

  const responseMap = useMemo(() => {
    const map = new Map<string, InspectionResponse>()
    inspectionResponses.forEach((response) => {
      map.set(response.template_item_id, response)
    })
    return map
  }, [inspectionResponses])

  const submitState = useMemo<SubmitGuardResult>(() => {
    if (!template) {
      return { missingRequiredItems: [], failingResponses: [] }
    }
    return evaluateInspectionSubmitState(template, inspectionResponses, inspectionActions)
  }, [template, inspectionResponses, inspectionActions])

  const getResponseForItem = (itemId: string) => localResponses[itemId] ?? responseMap.get(itemId)

  const canSubmit =
    inspection?.status === 'draft' &&
    submitState.missingRequiredItems.length === 0 &&
    submitState.failingResponses.length === 0

  if (inspectionQuery.isLoading || !inspection) {
    return <LoadingState label="Loading inspection..." />
  }

  if (templateQuery.isLoading || !template) {
    return <LoadingState label="Loading template structure..." />
  }

  const handleDraftChange = (itemId: string, partial: ResponseDraft) => {
    setDrafts((current) => ({ ...current, [itemId]: { ...current[itemId], ...partial } }))
  }

  const handleSaveResponse = async (
    itemId: string,
    options: { suppressToast?: boolean; skipRefetch?: boolean } = {},
  ): Promise<InspectionResponse | undefined> => {
    if (resolvedInspectionId === undefined) return
    const draft = drafts[itemId]
    if (!draft?.result) {
      push({ title: 'Select a result first', variant: 'warning' })
      return
    }
    const existing = getResponseForItem(itemId)
    try {
      let saved: InspectionResponse
      if (existing) {
        saved = await upsertResponse.mutateAsync({
          responseId: existing.id,
          result: draft.result,
          note: draft.note,
        })
      } else {
        saved = await upsertResponse.mutateAsync({
          template_item_id: itemId,
          result: draft.result,
          note: draft.note,
          media_urls: [],
        })
      }
      if (!options.suppressToast) {
        push({ title: 'Response saved', variant: 'success' })
      }
      if (!options.skipRefetch) {
        inspectionQuery.refetch()
      }
      setLocalResponses((current) => ({ ...current, [itemId]: saved }))
      return saved
    } catch (error) {
      push({ title: 'Unable to save response', description: String((error as Error).message), variant: 'error' })
    }
  }

  const ensureResponse = async (
    itemId: string,
    options: { suppressToast?: boolean; skipRefetch?: boolean } = {},
  ): Promise<InspectionResponse | undefined> => {
    const existing = getResponseForItem(itemId)
    const draft = drafts[itemId] ?? { result: '', note: '' }
    const hasUnsavedChanges =
      !existing || existing.result !== draft.result || (existing.note ?? '') !== (draft.note ?? '')
    if (hasUnsavedChanges) {
      return handleSaveResponse(itemId, options)
    }
    return existing
  }

  const handleUpload = async (itemId: string, file?: File) => {
    if (!file) return
    try {
      const response = await ensureResponse(itemId, { suppressToast: true, skipRefetch: true })
      if (!response) return
      await uploadMedia.mutateAsync({ file, responseId: response.id })
      push({ title: 'File uploaded', variant: 'success' })
      inspectionQuery.refetch()
    } catch (error) {
      push({ title: 'Upload failed', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleRemoveAttachment = async (itemId: string, url: string) => {
    const response = getResponseForItem(itemId)
    if (!response) return
    try {
      const remaining = (response.media_urls ?? []).filter((mediaUrl) => mediaUrl !== url)
      const updated = await upsertResponse.mutateAsync({ responseId: response.id, media_urls: remaining })
      push({ title: 'Attachment removed', variant: 'success' })
      setLocalResponses((current) => ({ ...current, [itemId]: updated }))
      inspectionQuery.refetch()
    } catch (error) {
      push({ title: 'Unable to remove attachment', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleInspectionDetailsUpdate = async (field: 'location' | 'notes', value: string) => {
    if (!updateInspection) return
    try {
      await updateInspection.mutateAsync({ [field]: value })
      push({ title: 'Inspection updated', variant: 'success' })
    } catch (error) {
      push({ title: 'Unable to update inspection', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleSubmitInspection = async () => {
    if (!inspection?.id) return
    try {
      await submitInspection.mutateAsync(inspection.id)
      push({ title: 'Inspection submitted', variant: 'success' })
      inspectionQuery.refetch()
    } catch (error) {
      push({ title: 'Submission failed', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleAddActionClick = async (itemId: string) => {
    const response = await ensureResponse(itemId)
    if (!response) return
    actionForm.reset({ title: '', description: '', severity: 'medium', due_date: '' })
    setActiveActionItem(itemId)
  }

  const handleCreateAction = async (itemId: string) => {
    if (!inspection?.id) return
    const response = await ensureResponse(itemId)
    if (!response) return
    const payload = actionForm.getValues()
    if (!payload.title) {
      push({ title: 'Action title required', variant: 'warning' })
      return
    }
    try {
      await createAction.mutateAsync({
        inspection_id: inspection.id,
        response_id: response.id,
        title: payload.title,
        description: payload.description,
        severity: payload.severity,
        due_date: payload.due_date ? new Date(payload.due_date).toISOString() : undefined,
      })
      push({ title: 'Action created', variant: 'success' })
      actionForm.reset({ title: '', description: '', severity: 'medium', due_date: '' })
      setActiveActionItem(null)
      actionsQuery.refetch()
    } catch (error) {
      push({ title: 'Unable to create action', description: String((error as Error).message), variant: 'error' })
    }
  }

  return (
    <div className="space-y-6">
      <Card title={`Inspection • ${inspection.id}`} subtitle={`Status • ${inspection.status}`}>
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <p className="text-xs uppercase text-slate-500">Started</p>
            <p className="text-sm font-semibold text-slate-900">{formatDateTime(inspection.started_at?.toString())}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">Location</p>
            <Input defaultValue={inspection.location ?? ''} onBlur={(event) => handleInspectionDetailsUpdate('location', event.target.value)} placeholder="Enter location" />
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">Notes</p>
            <Textarea rows={2} defaultValue={inspection.notes ?? ''} onBlur={(event) => handleInspectionDetailsUpdate('notes', event.target.value)} placeholder="Notes" />
          </div>
        </div>
      </Card>

      {submitState.missingRequiredItems.length > 0 && (
        <Card title="Missing responses" subtitle="Required items need responses before submission">
          <ul className="list-inside list-disc text-sm text-red-700">
            {submitState.missingRequiredItems.map((item) => (
              <li key={item.id}>{item.prompt}</li>
            ))}
          </ul>
        </Card>
      )}

      {submitState.failingResponses.length > 0 && (
        <Card title="Corrective actions needed" subtitle="Each failed item needs at least one action">
          <ul className="list-inside list-disc text-sm text-amber-700">
            {submitState.failingResponses.map((response) => (
              <li key={response.id}>Item {response.template_item_id} is failed with no actions</li>
            ))}
          </ul>
        </Card>
      )}

      {template.sections?.map((section) => (
        <Card key={section.id} title={section.title}>
          <div className="space-y-4">
            {section.items?.map((item) => {
              const response = getResponseForItem(item.id)
              const draft = drafts[item.id] ?? { result: '', note: '' }
              const actionsForResponse = inspectionActions.filter((action) => action.response_id === response?.id)
              const disableSave = upsertResponse.isPending
              return (
                <div key={item.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{item.prompt}</p>
                      <p className="text-xs text-slate-500">{item.is_required ? 'Required' : 'Optional'}</p>
                    </div>
                    {response?.result && <Badge variant={response.result === 'fail' ? 'danger' : 'info'}>{response.result}</Badge>}
                  </div>
                  <div className="mt-3 flex flex-wrap gap-4 text-sm">
                    {INSPECTION_RESULTS.map((result) => (
                      <label key={result} className="flex items-center gap-2 text-slate-700">
                        <input
                          type="radio"
                          name={`result-${item.id}`}
                          value={result}
                          checked={draft.result === result}
                          onChange={(event) => handleDraftChange(item.id, { result: event.target.value })}
                        />
                        {result.toUpperCase()}
                      </label>
                    ))}
                  </div>
                  <Textarea
                    className="mt-3"
                    rows={3}
                    placeholder="Add notes"
                    value={draft.note ?? ''}
                    onChange={(event) => handleDraftChange(item.id, { note: event.target.value })}
                  />
                  <div className="mt-3 flex flex-wrap items-center gap-3">
                    <Button type="button" variant="secondary" onClick={() => handleSaveResponse(item.id)} disabled={disableSave}>
                      <Save className="mr-2 h-4 w-4" /> Save response
                    </Button>
                    <label className="flex cursor-pointer items-center gap-2 text-sm text-brand-700">
                      <ImagePlus className="h-4 w-4" />
                      <input
                        type="file"
                        className="hidden"
                        accept="image/*"
                        onChange={(event) => {
                          const file = event.target.files?.[0]
                          if (file) handleUpload(item.id, file)
                        }}
                      />
                      Upload image
                    </label>
                  </div>
                  {response && response.media_urls?.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {response.media_urls.map((url) => (
                        <div key={url} className="flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1 text-xs">
                          <a href={url} className="text-brand-600 underline" target="_blank" rel="noreferrer">
                            {url.split('/').pop() ?? 'Attachment'}
                          </a>
                          <button
                            type="button"
                            className="text-red-600"
                            onClick={() => handleRemoveAttachment(item.id, url)}
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : null}

                  <div className="mt-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-semibold text-slate-900">Corrective actions</p>
                        <Button type="button" variant="ghost" onClick={() => void handleAddActionClick(item.id)}>
                          Add action
                        </Button>
                    </div>
                    {actionsForResponse.length === 0 && (
                      <EmptyState title="No actions" description="Create an action for failed items." />
                    )}
                    {actionsForResponse.map((action) => (
                      <div key={action.id} className="rounded-lg border border-slate-100 p-3 text-sm">
                        <div className="flex items-center justify-between">
                          <p className="font-semibold text-slate-900">{action.title}</p>
                          <Badge variant="warning">{action.severity}</Badge>
                        </div>
                        <p className="text-xs text-slate-500">Due {action.due_date ? formatDateTime(action.due_date.toString()) : 'unspecified'}</p>
                      </div>
                    ))}
                    {activeActionItem === item.id && (
                      <div className="rounded-xl border border-dashed border-slate-200 p-4">
                        <form
                          className="grid gap-3 md:grid-cols-2"
                          onSubmit={(event) => {
                            event.preventDefault()
                            void handleCreateAction(item.id)
                          }}
                        >
                          <FormField label="Title" error={actionForm.formState.errors.title?.message}>
                            <Input {...actionForm.register('title')} />
                          </FormField>
                          <FormField label="Severity">
                            <Select {...actionForm.register('severity')}>
                              {ACTION_SEVERITIES.map((severity) => (
                                <option key={severity} value={severity}>
                                  {severity}
                                </option>
                              ))}
                            </Select>
                          </FormField>
                          <FormField label="Due date">
                            <Input type="date" {...actionForm.register('due_date')} />
                          </FormField>
                          <FormField label="Description">
                            <Textarea rows={2} {...actionForm.register('description')} />
                          </FormField>
                          <div className="md:col-span-2 flex justify-end gap-2">
                            <Button type="button" variant="ghost" onClick={() => setActiveActionItem(null)}>
                              Cancel
                            </Button>
                            <Button type="submit">Save action</Button>
                          </div>
                        </form>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </Card>
      ))}

      <div className="flex flex-wrap items-center gap-4">
        <Button type="button" disabled={!canSubmit || submitInspection.isPending} onClick={handleSubmitInspection}>
          Submit inspection
        </Button>
        {canApprove && inspection.status === 'submitted' && inspection.id && (
          <Button
            type="button"
            variant="secondary"
            disabled={approveInspection.isPending}
            onClick={() => approveInspection.mutateAsync(inspection.id)}
          >
            Approve
          </Button>
        )}
      </div>
    </div>
  )
}

type TemplateRead = components['schemas']['ChecklistTemplateRead']
type TemplateItem = components['schemas']['TemplateItemRead']
type InspectionResponse = components['schemas']['InspectionResponseRead']
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
  const requiredItems = template.sections?.flatMap((section) => section.items ?? []).filter((item) => item.is_required) ?? []
  const responseMap = new Map(responses.map((response) => [response.template_item_id, response]))
  const missingRequiredItems = requiredItems.filter((item) => {
    const response = responseMap.get(item.id)
    return !response?.result
  })
  const failingResponses = responses.filter((response) => {
    if (response.result !== 'fail') return false
    return !actions.some((action) => action.response_id === response.id)
  })
  return { missingRequiredItems, failingResponses }
}
