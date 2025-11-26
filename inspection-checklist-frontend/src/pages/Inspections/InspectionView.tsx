import { useMemo } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'

import { useActionsQuery, useInspectionQuery, useTemplateQuery } from '@/api/hooks'
import { getErrorMessage } from '@/api/client'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingState } from '@/components/feedback/LoadingState'
import { formatDateTime, formatInspectionName } from '@/lib/formatters'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/auth/useAuth'
import { useToast } from '@/components/ui/toastContext'
import { downloadFileWithAuth } from '@/lib/download'

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
  const actionsQuery = useActionsQuery()
  const resolvedInspectionId = inspection?.id ?? numericInspectionId
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
              View actions
            </Button>
            {canEditInspection && (
              <Button variant="secondary" onClick={() => navigate(`/inspections/${inspection.id}/edit`)}>
                Edit inspection
              </Button>
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
                            <p className="font-semibold text-slate-900">{action.title}</p>
                            <div className="flex items-center gap-3">
                              <Badge variant="warning">{action.severity}</Badge>
                              <Link
                                to={`/actions/search?actionId=${action.id}`}
                                className="text-xs font-semibold text-indigo-600 hover:underline"
                              >
                                Open action
                              </Link>
                            </div>
                          </div>
                          {action.description && <p className="text-xs text-slate-500">{action.description}</p>}
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
