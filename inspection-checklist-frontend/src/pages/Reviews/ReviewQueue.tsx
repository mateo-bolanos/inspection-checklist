import { useMemo } from 'react'
import { Link } from 'react-router-dom'

import { useApproveInspectionMutation, useInspectionsQuery, useRejectInspectionMutation, useTemplatesQuery } from '@/api/hooks'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/feedback/EmptyState'
import { LoadingState } from '@/components/feedback/LoadingState'
import { formatDateTime, formatInspectionName } from '@/lib/formatters'
import { useToast } from '@/components/ui/toastContext'

export const ReviewQueuePage = () => {
  const inspections = useInspectionsQuery()
  const templates = useTemplatesQuery()
  const approve = useApproveInspectionMutation()
  const reject = useRejectInspectionMutation()
  const { push } = useToast()

  const queue = useMemo(() => {
    return inspections.data?.filter((inspection) => inspection.status === 'submitted') ?? []
  }, [inspections.data])
  const templateNameMap = useMemo(() => {
    const map = new Map<string, string>()
    templates.data?.forEach((template) => map.set(template.id, template.name))
    return map
  }, [templates.data])

  const handleApprove = async (inspectionId: number | string) => {
    try {
      await approve.mutateAsync(inspectionId)
      push({ title: 'Inspection approved', variant: 'success' })
    } catch (error) {
      push({ title: 'Approve failed', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleReject = async (inspectionId: number | string) => {
    try {
      await reject.mutateAsync(inspectionId)
      push({ title: 'Inspection rejected', variant: 'success' })
    } catch (error) {
      push({ title: 'Reject failed', description: String((error as Error).message), variant: 'error' })
    }
  }

  if (inspections.isLoading) {
    return <LoadingState label="Loading review queue..." />
  }

  return (
    <Card title="Review queue" subtitle="Submitted inspections awaiting review">
      {queue.length === 0 ? (
        <EmptyState title="All caught up" description="No inspections need review." />
      ) : (
        <div className="space-y-3">
          {queue.map((inspection) => (
            <div key={inspection.id} className="rounded-xl border border-slate-200 p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-slate-900">
                    {formatInspectionName(
                      templateNameMap.get(inspection.template_id) || 'Inspection',
                      inspection.started_at,
                      inspection.id,
                    )}
                  </p>
                  <p className="text-xs text-slate-500">
                    Template • {templateNameMap.get(inspection.template_id) || '—'} &nbsp;•&nbsp; Origin •{' '}
                    {inspection.inspection_origin === 'assignment' ? 'Assignment' : 'Independent'} &nbsp;•&nbsp; Started{' '}
                    {formatDateTime(inspection.started_at?.toString())}
                  </p>
                </div>
                <div className="flex flex-wrap items-center justify-end gap-3">
                  <Link className="text-sm font-semibold text-brand-600 hover:underline" to={`/inspections/${inspection.id}`}>
                    Review inspection
                  </Link>
                  <div className="flex gap-2">
                    <Button variant="secondary" onClick={() => handleApprove(inspection.id)} disabled={approve.isPending}>
                      Approve
                    </Button>
                    <Button variant="ghost" onClick={() => handleReject(inspection.id)} disabled={reject.isPending}>
                      Reject
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  )
}
