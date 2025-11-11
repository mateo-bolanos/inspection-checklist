import { useMemo } from 'react'
import { Link } from 'react-router-dom'

import { useDashboardOverviewQuery, useInspectionsQuery, useTemplatesQuery } from '@/api/hooks'
import { useAuth } from '@/auth/useAuth'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { Card } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { formatInspectionName, formatScore } from '@/lib/formatters'

export const OverviewPage = () => {
  const { data, isLoading, isError, refetch } = useDashboardOverviewQuery()
  const inspectionsQuery = useInspectionsQuery()
  const templatesQuery = useTemplatesQuery()
  const { hasRole } = useAuth()
  const templateNameMap = useMemo(() => {
    const map = new Map<string, string>()
    templatesQuery.data?.forEach((template) => {
      map.set(template.id, template.name)
    })
    return map
  }, [templatesQuery.data])
  const canViewInspections = hasRole(['admin', 'inspector', 'reviewer'])
  const canEditInspections = hasRole(['admin', 'inspector'])

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        {[...Array(3)].map((_, index) => (
          <Card key={index}>
            <Skeleton className="h-20 w-full" />
          </Card>
        ))}
      </div>
    )
  }

  if (isError || !data) {
    return (
      <ErrorState
        message="Unable to load dashboard metrics"
        action={
          <button className="text-sm font-semibold text-brand-600" onClick={() => refetch()}>
            Try again
          </button>
        }
      />
    )
  }

  const recentInspections = inspectionsQuery.data?.slice(0, 4) ?? []

  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-4">
        <Card title="Total inspections">
          <p className="text-3xl font-semibold text-slate-900">{data.total_inspections}</p>
        </Card>
        <Card title="Submitted">
          <p className="text-3xl font-semibold text-slate-900">{data.submitted_inspections}</p>
        </Card>
        <Card title="Approval rate">
          <p className="text-3xl font-semibold text-slate-900">{formatScore(data.approval_rate)}</p>
        </Card>
        <Card title="Average score">
          <p className="text-3xl font-semibold text-slate-900">{formatScore(data.average_score)}</p>
        </Card>
      </div>

      <Card title="Recent inspections">
        {recentInspections.length === 0 ? (
          <EmptyState title="No inspections yet" description="Start a new inspection to see data here" />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2">Inspection</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Location</th>
                  <th className="px-4 py-2">Score</th>
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {recentInspections.map((inspection) => (
                  <tr key={inspection.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {formatInspectionName(
                        templateNameMap.get(inspection.template_id),
                        inspection.started_at,
                        inspection.id,
                      )}
                    </td>
                    <td className="px-4 py-3 capitalize text-slate-600">{inspection.status}</td>
                    <td className="px-4 py-3 text-slate-600">{inspection.location || 'Unassigned'}</td>
                    <td className="px-4 py-3 text-slate-900">{formatScore(inspection.overall_score)}</td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-3 text-sm font-semibold">
                        {canViewInspections && (
                          <Link className="text-brand-600 hover:underline" to={`/inspections/${inspection.id}`}>
                            View
                          </Link>
                        )}
                        {canEditInspections && inspection.status === 'draft' && (
                          <Link className="text-slate-600 hover:text-brand-600" to={`/inspections/${inspection.id}/edit`}>
                            Edit
                          </Link>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
