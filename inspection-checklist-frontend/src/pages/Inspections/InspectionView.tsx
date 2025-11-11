import { useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { useActionsQuery, useInspectionQuery, useTemplateQuery } from '@/api/hooks'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { LoadingState } from '@/components/feedback/LoadingState'
import { formatDateTime, formatInspectionName } from '@/lib/formatters'
import { Button } from '@/components/ui/Button'
import { useAuth } from '@/auth/useAuth'

export const InspectionViewPage = () => {
  const { inspectionId: inspectionIdParam } = useParams<{ inspectionId: string }>()
  const parsedInspectionId = inspectionIdParam ? Number(inspectionIdParam) : undefined
  const numericInspectionId = Number.isFinite(parsedInspectionId) ? parsedInspectionId : undefined
  const inspectionResourceId = numericInspectionId ?? inspectionIdParam
  const navigate = useNavigate()
  const { hasRole } = useAuth()
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

  if (!inspection || inspectionQuery.isLoading || templateQuery.isLoading || !template) {
    return <LoadingState label="Loading inspection..." />
  }

  const responseMap = new Map(inspection.responses.map((response) => [response.template_item_id, response]))
  const inspectionName = formatInspectionName(template.name, inspection.started_at, inspection.id)
  const canEditInspection = hasRole(['admin', 'inspector']) && inspection.status === 'draft'

  return (
    <div className="space-y-6">
      <Card
        title={inspectionName}
        subtitle={`Status • ${inspection.status}`}
        actions={
          canEditInspection ? (
            <Button variant="secondary" onClick={() => navigate(`/inspections/${inspection.id}/edit`)}>
              Edit inspection
            </Button>
          ) : undefined
        }
      >
        <div className="grid gap-4 md:grid-cols-4">
          <div>
            <p className="text-xs uppercase text-slate-500">Template</p>
            <p className="text-sm font-semibold text-slate-900">{template.name}</p>
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
                        <a key={url} href={url} target="_blank" rel="noreferrer" className="underline">
                          Attachment
                        </a>
                      ))}
                    </div>
                  ) : null}
                  {actionsForResponse.length > 0 && (
                    <div className="mt-3 space-y-2">
                      {actionsForResponse.map((action) => (
                        <div key={action.id} className="rounded-lg border border-slate-100 p-2 text-sm">
                          <div className="flex items-center justify-between">
                            <p className="font-semibold text-slate-900">{action.title}</p>
                            <Badge variant="warning">{action.severity}</Badge>
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
