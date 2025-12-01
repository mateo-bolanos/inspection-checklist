import { useMemo } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { useActionsQuery, useDeleteInspectionMutation, useInspectionQuery, useTemplateQuery } from '@/api/hooks'
import { getErrorMessage } from '@/api/client'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingState } from '@/components/feedback/LoadingState'
import { formatDateTime, formatInspectionName } from '@/lib/formatters'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/auth/useAuth'
import { useToast } from '@/components/ui/toastContext'
import { downloadFileWithAuth } from '@/lib/download'

const PROMPT_SEPARATORS = [' – ', ' - ', ' — ']

const parsePrompt = (prompt: string) => {
  const lines = (prompt || '').split('\n').map((line) => line.trim()).filter(Boolean)
  if (lines.length === 0) {
    return { title: prompt, guidance: [] as string[] }
  }
  let [firstLine, ...rest] = lines
  let title = firstLine
  let subtitle = ''
  for (const separator of PROMPT_SEPARATORS) {
    if (firstLine.includes(separator)) {
      const [maybeTitle, maybeSubtitle] = firstLine.split(separator)
      title = maybeTitle.trim()
      subtitle = (maybeSubtitle || '').trim()
      break
    }
  }
  const guidance: string[] = []
  if (subtitle) guidance.push(subtitle)
  guidance.push(...rest)
  return { title, guidance }
}

export const InspectionViewPage = () => {
  const { inspectionId: inspectionIdParam } = useParams<{ inspectionId: string }>()
  const parsedInspectionId = inspectionIdParam ? Number(inspectionIdParam) : undefined
  const numericInspectionId = Number.isFinite(parsedInspectionId) ? parsedInspectionId : undefined
  const inspectionResourceId = numericInspectionId ?? inspectionIdParam
  const navigate = useNavigate()
  const { hasRole } = useAuth()
  const { push } = useToast()
  const inspectionQuery = useInspectionQuery(inspectionResourceId)
  const inspection = inspectionQuery.data
  const templateQuery = useTemplateQuery(inspection?.template_id)
  const template = templateQuery.data
  const itemPromptMap = useMemo(() => {
    const map = new Map<string, string>()
    template?.sections?.forEach((section) =>
      section.items?.forEach((item) => {
        if (item.id) {
          const parsed = parsePrompt(item.prompt || item.id)
          map.set(item.id, parsed.title || item.prompt || item.id)
        }
      }),
    )
    return map
  }, [template])
  const actionsQuery = useActionsQuery()
  const resolvedInspectionId = inspection?.id ?? numericInspectionId
  const deleteMutation = useDeleteInspectionMutation()
  const inspectionActions = useMemo(
    () =>
      resolvedInspectionId === undefined
        ? []
        : actionsQuery.data?.filter((action) => action.inspection_id === resolvedInspectionId) ?? [],
    [actionsQuery.data, resolvedInspectionId],
  )

  const handleDownloadMedia = async (url: string) => {
    const fallbackName = url.split('/').pop()
    try {
      await downloadFileWithAuth(url, fallbackName)
    } catch (error) {
      push({ title: 'Unable to download file', description: getErrorMessage(error), variant: 'error' })
    }
  }

  const handleDelete = async () => {
    if (!inspection?.id) return
    if (!window.confirm('Delete this draft inspection? This cannot be undone.')) return
    try {
      await deleteMutation.mutateAsync(inspection.id)
      push({ title: 'Inspection deleted', variant: 'success' })
      navigate('/inspections')
    } catch (error) {
      push({ title: 'Unable to delete inspection', description: getErrorMessage(error), variant: 'error' })
    }
  }

  if (!inspection || inspectionQuery.isLoading || templateQuery.isLoading || !template) {
    return <LoadingState label="Loading inspection..." />
  }

  const responseMap = new Map(
    (inspection.responses ?? []).map((response) => [response.template_item_id, response]),
  )
  const inspectionLabel = template.name || 'Inspection'
  const inspectionName = formatInspectionName(inspectionLabel, inspection.started_at, inspection.id)
  const canEditInspection = hasRole(['admin', 'inspector']) && inspection.status === 'draft'

  return (
    <div className="space-y-6">
      <Card
        title={inspectionName}
        subtitle={`Status • ${inspection.status}`}
        actions={
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="ghost"
              onClick={() => navigate(`/actions/search?inspectionId=${inspection.id}`)}
            >
              View issues
            </Button>
            {canEditInspection && (
              <>
                <Button variant="secondary" onClick={() => navigate(`/inspections/${inspection.id}/edit`)}>
                  Edit inspection
                </Button>
                <Button variant="danger" onClick={handleDelete} loading={deleteMutation.isPending}>
                  Delete draft
                </Button>
              </>
            )}
          </div>
        }
      >
        <div className="grid gap-4 md:grid-cols-5">
          <div>
            <p className="text-xs uppercase text-slate-500">Template</p>
            <p className="text-sm font-semibold text-slate-900">{template.name}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">Origin</p>
            <p className="text-sm font-semibold text-slate-900">
              {inspection.inspection_origin === 'assignment' ? 'Assignment' : 'Independent'}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">Location</p>
            <p className="text-sm font-semibold text-slate-900">{inspection.location ?? '—'}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">Started</p>
            <p className="text-sm font-semibold text-slate-900">{formatDateTime(inspection.started_at?.toString())}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-slate-500">Created by</p>
            <p className="text-sm font-semibold text-slate-900">{inspection.created_by?.full_name ?? '—'}</p>
          </div>
        </div>
        {inspection.status === 'rejected' && (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="danger">Denied</Badge>
              <p className="text-sm font-semibold text-red-800">Returned for corrections</p>
              {inspection.rejected_at && (
                <span className="text-xs text-red-700">on {formatDateTime(inspection.rejected_at?.toString())}</span>
              )}
            </div>
            {inspection.rejection_reason && (
              <p className="mt-2 text-sm font-medium text-red-900 whitespace-pre-line">{inspection.rejection_reason}</p>
            )}
            {inspection.rejected_by && (
              <p className="mt-1 text-xs text-red-700">
                Reviewer: {inspection.rejected_by.full_name || inspection.rejected_by.email}
              </p>
            )}
            {inspection.rejection_entries && inspection.rejection_entries.length > 0 && (
              <div className="mt-3 space-y-2">
                {inspection.rejection_entries.map((entry) => (
                  <div key={entry.id} className="rounded-lg border border-red-100 bg-white p-2 text-xs text-slate-700">
                    <p className="font-semibold text-red-800">
                      {itemPromptMap.get(entry.template_item_id || '') || `Item ${entry.template_item_id || 'Unknown'}`} •{' '}
                      {entry.reason}
                    </p>
                    {entry.follow_up_instructions && <p className="text-slate-700">Follow-up: {entry.follow_up_instructions}</p>}
                    <p className="text-slate-500">
                      Logged {formatDateTime(entry.created_at?.toString())} by {entry.created_by?.full_name || entry.created_by?.email}
                      {entry.resolved_at && ` • Resolved ${formatDateTime(entry.resolved_at.toString())}`}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </Card>

      <Card title="Notes" subtitle="Latest inspection updates">
        {inspection.note_entries && inspection.note_entries.length > 0 ? (
          <div className="space-y-2">
            {[...inspection.note_entries]
              .sort((a, b) => new Date(b.created_at ?? '').getTime() - new Date(a.created_at ?? '').getTime())
              .map((entry) => (
                <div key={entry.id} className="rounded-lg border border-slate-200 p-3">
                  <p className="text-xs font-medium text-slate-500">
                    {entry.author?.full_name || entry.author?.email || entry.author_id || 'Unknown user'} •{' '}
                    {formatDateTime(entry.created_at)}
                  </p>
                  <p className="text-sm text-slate-900 whitespace-pre-line">{entry.body}</p>
                </div>
              ))}
          </div>
        ) : (
          <p className="text-sm text-slate-500">No notes have been recorded for this inspection.</p>
        )}
      </Card>

      {template.sections?.map((section) => (
        <Card key={section.id} title={section.title}>
          <div className="space-y-3">
            {section.items?.map((item) => {
              const response = responseMap.get(item.id)
              const actionsForResponse = inspectionActions.filter((action) => action.response_id === response?.id)
              return (
                <div key={item.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{item.prompt}</p>
                      <p className="text-xs text-slate-500">{item.is_required ? 'Required' : 'Optional'}</p>
                    </div>
                    {response?.result && <Badge variant={response.result === 'fail' ? 'danger' : 'info'}>{response.result}</Badge>}
                  </div>
                  {response?.note && <p className="mt-2 text-sm text-slate-600">{response.note}</p>}
                  {response?.media_urls?.length ? (
                    <div className="mt-2 flex flex-wrap gap-3 text-xs text-brand-600">
                      {response.media_urls.map((url) => (
                        <button
                          key={url}
                          type="button"
                          className="underline hover:text-brand-700"
                          onClick={() => handleDownloadMedia(url)}
                        >
                          Attachment
                        </button>
                      ))}
                    </div>
                  ) : null}
                  {actionsForResponse.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {actionsForResponse.map((action) => (
                        <div key={action.id} className="rounded-lg border border-slate-100 p-2 text-sm">
                          <div className="flex flex-wrap items-center justify-between gap-2">
                            <p className="font-semibold text-slate-900">
                              Issue #{action.id} • {action.title}
                            </p>
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
                          {action.description && (
                            <p className="text-xs text-slate-500">Corrective action: {action.description}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </Card>
      ))}
    </div>
  )
}
