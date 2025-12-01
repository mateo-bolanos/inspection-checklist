import { useMemo } from 'react'
import { Link } from 'react-router-dom'

import {
  useDashboardOverviewQuery,
  useDashboardWeeklyOverviewQuery,
  useDashboardWeeklyPendingQuery,
  useInspectionsQuery,
  useTemplatesQuery,
} from '@/api/hooks'
import { useAuth } from '@/auth/useAuth'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { Card } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { formatDateTime, formatInspectionName, formatScore } from '@/lib/formatters'

export const OverviewPage = () => {
  const { data, isLoading, isError, refetch } = useDashboardOverviewQuery()
  const inspectionsQuery = useInspectionsQuery({ pageSize: 4 })
  const templatesQuery = useTemplatesQuery()
  const { hasRole } = useAuth()
  const canSeeWeeklyInsights = hasRole(['admin', 'reviewer'])
  const weeklyOverviewQuery = useDashboardWeeklyOverviewQuery({ enabled: canSeeWeeklyInsights })
  const weeklyPendingQuery = useDashboardWeeklyPendingQuery({ enabled: canSeeWeeklyInsights })
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

  const recentInspections = inspectionsQuery.data?.items ?? []
  const weeklyMetricLabels = ['Total expected', 'Submitted', 'Approved', 'Pending', 'Overdue']
  const weeklyMetricValues = weeklyOverviewQuery.data
    ? [
        weeklyOverviewQuery.data.total_expected,
        weeklyOverviewQuery.data.submitted,
        weeklyOverviewQuery.data.approved,
        weeklyOverviewQuery.data.pending,
        weeklyOverviewQuery.data.overdue,
      ]
    : []

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

      {canSeeWeeklyInsights && (
        <Card title="Weekly scheduled inspections" subtitle="Current calendar week (Mon–Sun)">
          {weeklyOverviewQuery.isError ? (
            <ErrorState
              message="Unable to load weekly KPIs"
              action={
                <button
                  className="text-sm font-semibold text-brand-600"
                  onClick={() => weeklyOverviewQuery.refetch()}
                >
                  Retry
                </button>
              }
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              {weeklyMetricLabels.map((label, index) => (
                <div key={label} className="rounded-lg border border-slate-100 bg-slate-50 p-4">
                  <p className="text-sm font-medium text-slate-600">{label}</p>
                  {weeklyOverviewQuery.isLoading ? (
                    <Skeleton className="mt-3 h-8 w-24" />
                  ) : (
                    <p className="mt-1 text-2xl font-semibold text-slate-900">
                      {weeklyMetricValues[index] ?? '—'}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>
      )}

      {canSeeWeeklyInsights && (
        <Card title="Who's pending" subtitle="Assignees with outstanding weekly inspections">
          {weeklyPendingQuery.isError ? (
            <ErrorState
              message="Unable to load pending users"
              action={
                <button
                  className="text-sm font-semibold text-brand-600"
                  onClick={() => weeklyPendingQuery.refetch()}
                >
                  Retry
                </button>
              }
            />
          ) : weeklyPendingQuery.isLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, index) => (
                <div key={index} className="flex items-center gap-4">
                  <Skeleton className="h-5 w-1/4" />
                  <Skeleton className="h-5 w-16" />
                  <Skeleton className="h-5 w-16" />
                  <Skeleton className="h-5 w-32" />
                </div>
              ))}
            </div>
          ) : (weeklyPendingQuery.data?.length ?? 0) === 0 ? (
            <EmptyState
              title="Everyone is up to date"
              description="No pending or overdue scheduled inspections this week."
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="px-4 py-2">User</th>
                    <th className="px-4 py-2">Pending</th>
                    <th className="px-4 py-2">Overdue</th>
                    <th className="px-4 py-2">Last submission</th>
                  </tr>
                </thead>
                <tbody>
                  {weeklyPendingQuery.data?.map((entry) => (
                    <tr key={entry.user_id} className="border-t border-slate-100">
                      <td className="px-4 py-3 font-medium text-slate-900">{entry.user_name}</td>
                      <td className="px-4 py-3 text-slate-600">{entry.pending_count}</td>
                      <td className="px-4 py-3 text-slate-600">{entry.overdue_count}</td>
                      <td className="px-4 py-3 text-slate-600">
                        {entry.last_submission_at ? formatDateTime(entry.last_submission_at) : 'Never'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      <Card title="Recent inspections">
        {recentInspections.length === 0 ? (
          <EmptyState title="No inspections yet" description="Start a new inspection to see data here" />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2">Inspection</th>
                  <th className="px-4 py-2">Template</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Location</th>
                  <th className="px-4 py-2">Score</th>
                  <th className="px-4 py-2 text-right">Options</th>
                </tr>
              </thead>
              <tbody>
                {recentInspections.map((inspection) => (
                  <tr key={inspection.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-medium text-slate-900">
                      {formatInspectionName(
                        templateNameMap.get(inspection.template_id) || 'Inspection',
                        inspection.started_at,
                        inspection.id,
                      )}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      <div>{templateNameMap.get(inspection.template_id) || '—'}</div>
                      <p className="text-xs text-slate-500">
                        {inspection.inspection_origin === 'assignment' ? 'Assignment' : 'Independent'}
                      </p>
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
