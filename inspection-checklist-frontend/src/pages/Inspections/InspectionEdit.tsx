import { zodResolver } from '@hookform/resolvers/zod'
import { AlertTriangle, ImagePlus, Loader2 } from 'lucide-react'
import type { JSX } from 'react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { z } from 'zod'

import {
  useActionAssigneesQuery,
  useActionsQuery,
  useApproveInspectionMutation,
  useCreateActionMutation,
  useInspectionQuery,
  useOpenActionsByItemQuery,
  useSubmitInspectionMutation,
  useTemplateQuery,
  useUpdateInspectionMutation,
  useUpdateActionMutation,
  useUploadMediaMutation,
  useUpsertResponseMutation,
} from '@/api/hooks'
import { getErrorMessage } from '@/api/client'
import { ACTION_SEVERITIES, INSPECTION_RESULTS } from '@/lib/constants'
import { formatDateTime } from '@/lib/formatters'
import { downloadFileWithAuth } from '@/lib/download'
import { useAuth } from '@/auth/useAuth'
import { FormField } from '@/components/forms/FormField'
import { LocationSelect } from '@/components/forms/LocationSelect'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { Badge } from '@/components/ui/Badge'
import { useToast } from '@/components/ui/toastContext'
import { EmptyState } from '@/components/feedback/EmptyState'
import { LoadingState } from '@/components/feedback/LoadingState'
import { evaluateInspectionSubmitState } from './inspectionSubmitState'
import type { InspectionResponse, SubmitGuardResult } from './inspectionSubmitState'

const PROMPT_SEPARATORS = [' – ', ' - ', ' — ']

const parsePromptParts = (prompt: string): { title: string; guidance: string[] } => {
  const lines = prompt
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  if (lines.length === 0) {
    return { title: prompt, guidance: [] }
  }
  let [firstLine, ...rest] = lines
  let title = firstLine
  let subtitle = ''
  for (const separator of PROMPT_SEPARATORS) {
    if (firstLine.includes(separator)) {
      const [maybeTitle, maybeSubtitle] = firstLine.split(separator)
      title = maybeTitle.trim()
      subtitle = maybeSubtitle?.trim() ?? ''
      break
    }
  }
  const guidance: string[] = []
  if (subtitle) {
    guidance.push(subtitle)
  }
  guidance.push(...rest)
  return { title, guidance }
}

const renderGuidanceLines = (lines: string[], keyPrefix: string) => {
  if (lines.length === 0) return null
  const elements: JSX.Element[] = []
  let bulletBuffer: string[] = []
  let keyIndex = 0
  const flushBullets = () => {
    if (bulletBuffer.length === 0) return
    const bullets = bulletBuffer.map((text, index) => (
      <li key={`${keyPrefix}-bullet-${keyIndex}-${index}`}>{text}</li>
    ))
    elements.push(
      <ul key={`${keyPrefix}-bullets-${keyIndex++}`} className="list-inside list-disc space-y-0.5">
        {bullets}
      </ul>,
    )
    bulletBuffer = []
  }

  lines.forEach((line) => {
    if (line.startsWith('- ')) {
      bulletBuffer.push(line.replace(/^-+\s*/, '').trim())
      return
    }
    flushBullets()
    elements.push(
      <p key={`${keyPrefix}-text-${keyIndex++}`} className="whitespace-pre-line">
        {line}
      </p>,
    )
  })
  flushBullets()

  return (
    <div className="mt-1 space-y-1 text-xs text-slate-600" data-testid={`${keyPrefix}-guidance`}>
      {elements}
    </div>
  )
}

const deriveRiskLevel = (occurrence: string, injury: string) => {
  const occ = occurrence?.toLowerCase()
  const inj = injury?.toLowerCase()
  const score = (value: string) => {
    if (value === 'high') return 3
    if (value === 'medium') return 2
    if (value === 'low') return 1
    return 0
  }
  const scores = [score(occ), score(inj)].filter((s) => s > 0)
  if (scores.length === 0) return 'medium'
  const avg = scores.reduce((a, b) => a + b, 0) / scores.length
  if (avg >= 2.5) return 'high'
  if (avg >= 1.5) return 'medium'
  return 'low'
}

type OpenActionsPanelProps = {
  templateItemId: string
  enabled: boolean
  drafts: Record<number, string>
  onDraftChange: (actionId: number, value: string) => void
  onAddNote: (actionId: number) => Promise<void>
  isSaving: boolean
}

const OpenActionsPanel = ({
  templateItemId,
  enabled,
  drafts,
  onDraftChange,
  onAddNote,
  isSaving,
}: OpenActionsPanelProps) => {
  const openActionsQuery = useOpenActionsByItemQuery(templateItemId, enabled)
  const openActions = openActionsQuery.data ?? []

  if (!enabled) return null

  if (openActionsQuery.isLoading) {
    return (
      <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-slate-50 px-3 py-1 text-xs text-slate-600">
        <Loader2 className="h-4 w-4 animate-spin text-slate-500" />
        Checking for existing issues...
      </div>
    )
  }

  if (openActionsQuery.isError) {
    return (
      <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-red-50 px-3 py-1 text-xs text-red-700">
        <AlertTriangle className="h-4 w-4" />
        Unable to load open issues right now.
      </div>
    )
  }

  if (openActions.length === 0) {
    return null
  }

  return (
    <div className="mt-3 space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3">
      <div className="flex items-center gap-2 text-amber-800">
        <AlertTriangle className="h-4 w-4" />
        <p className="text-sm font-semibold">
          Existing open issues for this item — add a note or continue to create a new issue.
        </p>
      </div>
      <div className="space-y-3">
        {openActions.map((action) => (
          <div key={action.id} className="rounded border border-amber-100 bg-white p-3 shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-slate-900">
                  Issue #{action.id} • {action.title}
                </p>
                <p className="text-xs text-slate-500">
                  Assigned to {action.assignee?.full_name || action.assignee?.email || 'Unassigned'} • Due{' '}
                  {action.due_date ? formatDateTime(action.due_date.toString()) : 'unspecified'}
                </p>
                {action.inspection_location && (
                  <p className="text-xs text-slate-500">Department • {action.inspection_location}</p>
                )}
              </div>
              <Badge variant="warning">{action.severity}</Badge>
            </div>
            <Textarea
              className="mt-2"
              rows={2}
              placeholder="Add note to existing issue"
              value={drafts[action.id] ?? ''}
              onChange={(event) => onDraftChange(action.id, event.target.value)}
            />
            <div className="flex justify-end">
              <Button
                type="button"
                variant="secondary"
                onClick={() => void onAddNote(action.id)}
                disabled={(drafts[action.id] ?? '').trim().length === 0 || isSaving}
              >
                Add note to issue
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export const actionSchema = z.object({
  title: z.string().min(3),
  description: z.string().optional(),
  severity: z.enum(ACTION_SEVERITIES),
  occurrence_severity: z.enum(ACTION_SEVERITIES),
  injury_severity: z.enum(ACTION_SEVERITIES),
  due_date: z.string().optional(),
  assigned_to_id: z.string().optional(),
  work_order_required: z.boolean(),
  work_order_number: z.string().optional(),
})

type ActionFormValues = z.infer<typeof actionSchema>

type ResponseDraft = {
  result?: string
  note?: string
}

export const InspectionEditPage = () => {
  const { inspectionId: inspectionIdParam } = useParams<{ inspectionId: string }>()
  const navigate = useNavigate()
  const parsedInspectionId = inspectionIdParam ? Number(inspectionIdParam) : undefined
  const numericInspectionId = Number.isFinite(parsedInspectionId) ? parsedInspectionId : undefined
  const inspectionResourceId = numericInspectionId ?? inspectionIdParam
  const inspectionQuery = useInspectionQuery(inspectionResourceId)
  const inspection = inspectionQuery.data
  const inspectionResponses = useMemo(() => inspection?.responses ?? [], [inspection?.responses])
  const templateQuery = useTemplateQuery(inspection?.template_id)
  const template = templateQuery.data
  const itemPromptMap = useMemo(() => {
    const map = new Map<string, string>()
    template?.sections?.forEach((section) =>
      section.items?.forEach((item) => {
        if (item.id) map.set(item.id, parsePromptParts(item.prompt || '').title || item.prompt || item.id)
      }),
    )
    return map
  }, [template])
  const rejectedItems = useMemo(() => {
    if (inspection?.status !== 'rejected') return new Set<string>()
    const entries = inspection.rejection_entries ?? []
    return new Set(entries.filter((entry) => !entry.resolved_at).map((entry) => entry.template_item_id).filter(Boolean) as string[])
  }, [inspection?.rejection_entries, inspection?.status])
  const isRework = inspection?.status === 'rejected' && rejectedItems.size > 0
  const actionsQuery = useActionsQuery()
  const assigneesQuery = useActionAssigneesQuery()
  const resolvedInspectionId = inspection?.id ?? numericInspectionId
  const inspectionActions = useMemo(() => {
    if (resolvedInspectionId === undefined) return []
    return actionsQuery.data?.filter((action) => action.inspection_id === resolvedInspectionId) ?? []
  }, [actionsQuery.data, resolvedInspectionId])
  const assigneeOptions = useMemo(() => assigneesQuery.data ?? [], [assigneesQuery.data])
  const inspectionNotes = useMemo(() => {
    const entries = inspection?.note_entries ?? []
    return [...entries].sort(
      (a, b) => new Date(b.created_at ?? '').getTime() - new Date(a.created_at ?? '').getTime(),
    )
  }, [inspection?.note_entries])

  const upsertResponse = useUpsertResponseMutation(inspectionResourceId ?? '')
  const uploadMedia = useUploadMediaMutation()
  const updateInspection = useUpdateInspectionMutation(inspectionResourceId)
  const submitInspection = useSubmitInspectionMutation()
  const approveInspection = useApproveInspectionMutation()
  const createAction = useCreateActionMutation()
  const updateAction = useUpdateActionMutation()
  const { push } = useToast()
  const { hasRole } = useAuth()
  const canApprove = hasRole(['admin', 'reviewer'])
  const isManager = hasRole(['admin', 'reviewer'])

  const [drafts, setDrafts] = useState<Record<string, ResponseDraft>>({})
  const [activeActionItem, setActiveActionItem] = useState<string | null>(null)
  const [selectedLocationId, setSelectedLocationId] = useState('')
  const [noteDraft, setNoteDraft] = useState('')
  const [actionNoteDrafts, setActionNoteDrafts] = useState<Record<number, string>>({})

  const actionForm = useForm<ActionFormValues>({
    resolver: zodResolver(actionSchema),
    defaultValues: {
      title: '',
      description: '',
      severity: 'medium',
      occurrence_severity: 'medium',
      injury_severity: 'medium',
      due_date: '',
      assigned_to_id: '',
      work_order_required: false,
      work_order_number: '',
    },
  })
  const watchOccurrence = actionForm.watch('occurrence_severity')
  const watchInjury = actionForm.watch('injury_severity')

  useEffect(() => {
    const risk = deriveRiskLevel(watchOccurrence, watchInjury)
    if (risk && actionForm.getValues('severity') !== risk) {
      actionForm.setValue('severity', risk)
    }
  }, [actionForm, watchOccurrence, watchInjury])

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

  useEffect(() => {
    if (!inspection) {
      setSelectedLocationId('')
      return
    }
    if (inspection.location_id) {
      setSelectedLocationId(String(inspection.location_id))
    } else {
      setSelectedLocationId('')
    }
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
    (inspection?.status === 'draft' || inspection?.status === 'rejected') &&
    submitState.missingRequiredItems.length === 0 &&
    submitState.failingResponses.length === 0

  const legacyLocationLabel = inspection?.location_id ? null : inspection?.location ?? null

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
    draftOverride?: ResponseDraft,
  ): Promise<InspectionResponse | undefined> => {
    if (resolvedInspectionId === undefined) return
    const draft = draftOverride ?? drafts[itemId]
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

  const handleResultSelect = (itemId: string, result: string, fallbackNote?: string) => {
    const currentDraft = drafts[itemId] ?? {}
    const nextDraft: ResponseDraft = { ...currentDraft, result }
    if (nextDraft.note === undefined) {
      nextDraft.note = fallbackNote
    }
    setDrafts((current) => ({ ...current, [itemId]: nextDraft }))
    void handleSaveResponse(itemId, { suppressToast: true }, nextDraft)
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

  const handleDownloadMedia = async (url: string) => {
    const fallbackName = url.split('/').pop()
    try {
      await downloadFileWithAuth(url, fallbackName)
    } catch (error) {
      push({ title: 'Unable to download file', description: getErrorMessage(error), variant: 'error' })
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

  const canUpdateInspection = inspectionResourceId !== undefined && inspectionResourceId !== null

  const handleInspectionNoteSubmit = async () => {
    if (!canUpdateInspection) return
    const content = noteDraft.trim()
    if (!content) {
      push({ title: 'Add a note first', variant: 'warning' })
      return
    }
    try {
      await updateInspection.mutateAsync({ notes: content })
      push({ title: 'Note saved', variant: 'success' })
      setNoteDraft('')
      inspectionQuery.refetch()
    } catch (error) {
      push({ title: 'Unable to update inspection', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleLocationSelectChange = async (value: string) => {
    setSelectedLocationId(value)
    if (!canUpdateInspection || !value) return
    try {
      await updateInspection.mutateAsync({ location_id: Number(value) })
      push({ title: 'Location updated', variant: 'success' })
    } catch (error) {
      push({ title: 'Unable to update location', description: String((error as Error).message), variant: 'error' })
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

  const handleOpenActionNoteChange = (actionId: number, value: string) => {
    setActionNoteDrafts((current) => ({ ...current, [actionId]: value }))
  }

  const handleAddNoteToExistingAction = async (actionId: number) => {
    const note = (actionNoteDrafts[actionId] ?? '').trim()
    if (!note) {
      push({ title: 'Add a note before saving', variant: 'warning' })
      return
    }
    try {
      await updateAction.mutateAsync({ actionId, data: { resolution_notes: note } })
      push({ title: 'Note added to issue', variant: 'success' })
      setActionNoteDrafts((current) => ({ ...current, [actionId]: '' }))
    } catch (error) {
      push({ title: 'Unable to add note', description: getErrorMessage(error), variant: 'error' })
    }
  }

  const handleAddActionClick = async (itemId: string) => {
    const response = await ensureResponse(itemId)
    if (!response) return
    actionForm.reset({
      title: '',
      description: '',
      severity: 'medium',
      occurrence_severity: 'medium',
      injury_severity: 'medium',
      due_date: '',
      assigned_to_id: '',
      work_order_required: false,
      work_order_number: '',
    })
    setActiveActionItem(itemId)
  }

  const handleCreateAction = async (itemId: string) => {
    if (!inspection?.id) return
    const response = await ensureResponse(itemId)
    if (!response) return
    const payload = actionForm.getValues()
    if (!payload.title) {
      push({ title: 'Issue name required', variant: 'warning' })
      return
    }
    const assignedToId = payload.assigned_to_id?.trim()
    if (isManager && !assignedToId) {
      push({ title: 'Assign this issue to an owner', variant: 'warning' })
      return
    }
    try {
      await createAction.mutateAsync({
        inspection_id: inspection.id,
        response_id: response.id,
        title: payload.title,
        description: payload.description,
      occurrence_severity: payload.occurrence_severity,
      injury_severity: payload.injury_severity,
      severity: payload.severity,
      due_date: payload.due_date ? new Date(payload.due_date).toISOString() : undefined,
      work_order_required: payload.work_order_required,
      work_order_number: payload.work_order_number,
      assigned_to_id: isManager ? assignedToId : undefined,
      status: 'open',
    })
      push({ title: 'Issue created', variant: 'success' })
      actionForm.reset({
        title: '',
        description: '',
        severity: 'medium',
        occurrence_severity: 'medium',
        injury_severity: 'medium',
        due_date: '',
        assigned_to_id: '',
        work_order_required: false,
        work_order_number: '',
      })
      setActiveActionItem(null)
      actionsQuery.refetch()
    } catch (error) {
      push({ title: 'Unable to create issue', description: String((error as Error).message), variant: 'error' })
    }
  }

  return (
    <div className="space-y-6">
      <Card
        title={`Inspection • ${inspection.id}`}
        subtitle={`Status • ${inspection.status}`}
        actions={
          <Button
            type="button"
            variant="ghost"
            onClick={() => navigate(`/actions/search?inspectionId=${inspection.id}`)}
          >
            View issues
          </Button>
        }
      >
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <p className="text-xs uppercase text-slate-500">Started</p>
            <p className="text-sm font-semibold text-slate-900">{formatDateTime(inspection.started_at?.toString())}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">Template</p>
            <p className="text-sm font-semibold text-slate-900">{template.name || 'Inspection'}</p>
            <p className="text-xs text-slate-500">
              {inspection.inspection_origin === 'assignment' ? 'Assignment' : 'Independent'}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">Location</p>
            <LocationSelect
              value={selectedLocationId}
              onChange={handleLocationSelectChange}
              disabled={!canUpdateInspection || updateInspection.isPending}
              legacyLabel={legacyLocationLabel}
            />
          </div>
        </div>
      </Card>

      <Card title="Inspection Notes">
        <div className="space-y-3">
          <Textarea
            rows={3}
            value={noteDraft}
            onChange={(event) => setNoteDraft(event.target.value)}
            disabled={!canUpdateInspection || updateInspection.isPending}
            placeholder="Add a note"
          />
          <Button
            type="button"
            onClick={handleInspectionNoteSubmit}
            disabled={!canUpdateInspection || updateInspection.isPending}
          >
            Save note
          </Button>
          <div className="max-h-60 space-y-2 overflow-y-auto rounded-xl border border-slate-100 p-3">
            {inspectionNotes.length === 0 ? (
              <p className="text-xs text-slate-500">No notes captured yet.</p>
            ) : (
              inspectionNotes.map((entry) => (
                <div key={entry.id} className="rounded-lg border border-slate-100 bg-white p-2">
                  <p className="text-xs font-medium text-slate-500">
                    {entry.author?.full_name || entry.author?.email || entry.author_id || 'Unknown user'} •{' '}
                    {formatDateTime(entry.created_at)}
                  </p>
                  <p className="text-sm text-slate-900 whitespace-pre-line">{entry.body}</p>
                </div>
              ))
            )}
          </div>
        </div>
      </Card>

      {isRework && rejectedItems.size > 0 && (
        <Card title="Returned items" subtitle="Only these items can be updated before resubmitting">
          <ul className="list-inside list-disc text-sm text-amber-700">
            {Array.from(rejectedItems).map((itemId) => (
              <li key={itemId}>{itemPromptMap.get(itemId) || `Item ${itemId}`}</li>
            ))}
          </ul>
        </Card>
      )}

      {submitState.missingRequiredItems.length > 0 && (
        <Card title="Missing responses" subtitle="Required items need responses before submission">
          <ul className="list-inside list-disc text-sm text-red-700">
            {submitState.missingRequiredItems.map((item) => {
              const parts = parsePromptParts(item.prompt ?? '')
              return <li key={item.id}>{parts.title || item.prompt}</li>
            })}
          </ul>
        </Card>
      )}

      {submitState.failingResponses.length > 0 && (
        <Card title="Issues needed" subtitle="Each failed item needs at least one issue and corrective action">
          <ul className="list-inside list-disc text-sm text-amber-700">
            {submitState.failingResponses.map((response) => (
              <li key={response.id}>Item {response.template_item_id} is failed with no issues</li>
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
              const currentResult = draft.result ?? response?.result ?? ''
              const isFailSelected = currentResult === 'fail'
              const noteValue = draft.note ?? response?.note ?? ''
              const promptParts = parsePromptParts(item.prompt ?? '')
              const guidanceContent = renderGuidanceLines(promptParts.guidance, item.id)
              const isEditable = !isRework || rejectedItems.has(item.id)
              return (
                <div key={item.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        {promptParts.title || itemPromptMap.get(item.id) || item.prompt}
                      </p>
                      {guidanceContent}
                      <p className="mt-1 text-xs text-slate-500">{item.is_required ? 'Required' : 'Optional'}</p>
                      {!isEditable && (
                        <p className="text-xs text-amber-600">Locked — not part of the returned items.</p>
                      )}
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
                          checked={currentResult === result}
                          disabled={!isEditable}
                          onChange={(event) => handleResultSelect(item.id, event.target.value, noteValue)}
                        />
                        {result.toUpperCase()}
                      </label>
                    ))}
                  </div>
                  {isFailSelected && (
                    <Textarea
                      className="mt-3"
                      rows={3}
                      placeholder="Add notes"
                      value={noteValue}
                      onChange={(event) => handleDraftChange(item.id, { note: event.target.value })}
                      disabled={!isEditable}
                    />
                  )}
                  <div className="mt-3 flex flex-wrap items-center gap-3">
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
                        disabled={!isEditable}
                      />
                      Upload image
                    </label>
                  </div>
                  {response && response.media_urls?.length ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {response.media_urls.map((url) => (
                        <div key={url} className="flex items-center gap-2 rounded-full border border-slate-200 px-3 py-1 text-xs">
                          <button
                            type="button"
                            className="text-brand-600 underline"
                            onClick={() => handleDownloadMedia(url)}
                          >
                            {url.split('/').pop() ?? 'Attachment'}
                          </button>
                          <button
                            type="button"
                            className="text-red-600"
                            onClick={() => handleRemoveAttachment(item.id, url)}
                            disabled={!isEditable}
                          >
                            Remove
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : null}

                  {isFailSelected && (
                    <OpenActionsPanel
                      templateItemId={item.id}
                      enabled={isFailSelected}
                      drafts={actionNoteDrafts}
                      isSaving={updateAction.isPending}
                      onDraftChange={handleOpenActionNoteChange}
                      onAddNote={handleAddNoteToExistingAction}
                    />
                  )}

                  {isFailSelected && (
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-slate-900">Issues</p>
                        <Button
                          type="button"
                          variant="ghost"
                          onClick={() => void handleAddActionClick(item.id)}
                          disabled={!isEditable}
                        >
                          Add issue
                        </Button>
                      </div>
                      {actionsForResponse.length === 0 && (
                        <EmptyState title="No issues" description="Log an issue with a corrective action for failed items." />
                      )}
                      {actionsForResponse.map((action) => (
                        <div key={action.id} className="rounded-lg border border-slate-100 p-3 text-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <div>
                              <p className="font-semibold text-slate-900">
                                Issue #{action.id} • {action.title}
                              </p>
                              <p className="text-xs text-slate-500">Status • {action.status.replace('_', ' ')}</p>
                            </div>
                            <div className="flex items-center gap-3">
                              <Badge variant="warning">{action.severity}</Badge>
                              <Link
                                to={`/actions/search?actionId=${action.id}`}
                                className="text-xs font-semibold text-indigo-600 hover:underline"
                              >
                                Open issue
                              </Link>
                            </div>
                          </div>
                          <p className="text-xs text-slate-500">
                            Due {action.due_date ? formatDateTime(action.due_date.toString()) : 'unspecified'}
                          </p>
                          <p className="text-xs text-slate-500">
                            Assigned to {action.assignee?.full_name || action.assignee?.email || 'Unassigned'}
                          </p>
                          {action.resolution_notes && (
                            <p className="mt-1 text-xs text-emerald-700">Resolution • {action.resolution_notes}</p>
                          )}
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
                        <FormField label="Issue name" error={actionForm.formState.errors.title?.message}>
                          <Input {...actionForm.register('title')} />
                        </FormField>
                        <FormField label="Severity of occurrence">
                          <Select {...actionForm.register('occurrence_severity')}>
                            {ACTION_SEVERITIES.map((severity) => (
                              <option key={severity} value={severity}>
                                {severity}
                              </option>
                            ))}
                          </Select>
                        </FormField>
                        <FormField label="Severity of injury">
                          <Select {...actionForm.register('injury_severity')}>
                            {ACTION_SEVERITIES.map((severity) => (
                              <option key={severity} value={severity}>
                                {severity}
                              </option>
                            ))}
                          </Select>
                        </FormField>
                        <FormField label="Risk level (auto)">
                          <Input value={actionForm.watch('severity')} disabled readOnly />
                        </FormField>
                        <FormField label="Due date">
                          <Input type="date" {...actionForm.register('due_date')} />
                        </FormField>
                        <FormField label="Work order required?">
                          <div className="flex items-center gap-2">
                            <input type="checkbox" {...actionForm.register('work_order_required')} />
                            <span className="text-sm text-slate-700">Block closure until a number is provided</span>
                          </div>
                        </FormField>
                        <FormField label="Work order number">
                          <Input {...actionForm.register('work_order_number')} placeholder="WO-1234" />
                        </FormField>
                        {isManager ? (
                          <FormField label="Assign to">
                            <Select {...actionForm.register('assigned_to_id')} disabled={assigneesQuery.isLoading}>
                              <option value="">Unassigned</option>
                              {assigneeOptions.map((user) => (
                                <option key={user.id} value={user.id}>
                                  {user.full_name || user.email}
                                </option>
                              ))}
                            </Select>
                          </FormField>
                        ) : null}
                        <FormField label="Corrective action">
                          <Textarea rows={2} {...actionForm.register('description')} />
                        </FormField>
                            {assigneesQuery.isError && (
                              <p className="text-xs text-red-600 md:col-span-2">Unable to load suggested assignees.</p>
                            )}
                            <div className="md:col-span-2 flex justify-end gap-2">
                              <Button type="button" variant="ghost" onClick={() => setActiveActionItem(null)}>
                                Cancel
                              </Button>
                              <Button type="submit">Save issue</Button>
                            </div>
                          </form>
                        </div>
                      )}
                    </div>
                  )}
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
