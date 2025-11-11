import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { useActionsQuery, useDashboardActionsQuery } from '@/api/hooks'
import type { components } from '@/api/gen/schema'
import { ACTION_SEVERITIES } from '@/lib/constants'
import { formatDate, formatRelative } from '@/lib/formatters'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { LoadingState } from '@/components/feedback/LoadingState'
import { ActionDetailsModal } from '@/pages/Actions/ActionDetailsModal'
import { getActionDisplayStatus } from '@/pages/Actions/utils'

type ActionRecord = components['schemas']['CorrectiveActionRead']

export const ActionsListPage = () => {
  const { data, isLoading } = useActionsQuery()
  const dashboard = useDashboardActionsQuery()
  const [severity, setSeverity] = useState<'all' | (typeof ACTION_SEVERITIES)[number]>('all')
  const [selectedActionId, setSelectedActionId] = useState<number | null>(null)

  const resolveActionDate = (value?: string | null, fallback?: string | null): string =>
    value ?? fallback ?? new Date().toISOString()

  const activeActions = useMemo(() => {
    if (!data) return []
    return data.filter((action) => {
      if (action.status === 'closed') return false
      const severityMatch = severity === 'all' || action.severity === severity
      const isOpen = getActionDisplayStatus(action.status) === 'open'
      return severityMatch && isOpen
    })
  }, [data, severity])

  const closedActions = useMemo(() => {
    if (!data) return []
    return data
      .filter((action) => action.status === 'closed')
      .sort((a, b) => {
        const dateA = new Date(resolveActionDate(a.closed_at, a.created_at)).getTime()
        const dateB = new Date(resolveActionDate(b.closed_at, b.created_at)).getTime()
        return dateB - dateA
      })
  }, [data])

  const selectedAction = useMemo(() => {
    if (!data || selectedActionId === null) return null
    return data.find((action) => action.id === selectedActionId) ?? null
  }, [data, selectedActionId])

  const handleActionClick = (action: ActionRecord) => {
    setSelectedActionId(action.id)
  }

  if (isLoading) {
    return <LoadingState label="Loading actions..." />
  }

  return (
    <div className="space-y-6">
      <Card
        title="Action overview"
        actions={
          <Link to="/actions/search" className="text-sm font-semibold text-indigo-600 hover:underline">
            Search actions
          </Link>
        }
      >
        {dashboard.isLoading ? (
          <p className="text-sm text-slate-500">Loading action metrics...</p>
        ) : dashboard.isError ? (
          <ErrorState
            message="Could not load action metrics"
            action={
              <Button variant="ghost" onClick={() => dashboard.refetch()}>
                Retry
              </Button>
            }
          />
        ) : dashboard.data ? (
          <div className="grid gap-4 md:grid-cols-4">
            {Object.entries(dashboard.data.open_by_severity).map(([key, value]) => (
              <div key={key} className="rounded-xl bg-slate-50 p-4 text-center">
                <p className="text-xs uppercase tracking-wide text-slate-500">{key}</p>
                <p className="text-3xl font-semibold text-slate-900">{value}</p>
              </div>
            ))}
            <div className="rounded-xl bg-red-50 p-4 text-center text-red-700">
              <p className="text-xs uppercase tracking-wide">Overdue</p>
              <p className="text-3xl font-semibold">{dashboard.data.overdue_actions}</p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">No metrics available yet.</p>
        )}
      </Card>

      <Card
        title="Active corrective actions"
        subtitle="Monitor everything that is still open"
        actions={
          <div className="flex gap-2">
            <Select value={severity} onChange={(event) => setSeverity(event.target.value as typeof severity)}>
              <option value="all">All severities</option>
              {ACTION_SEVERITIES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </Select>
          </div>
        }
      >
        {activeActions.length === 0 ? (
          <EmptyState title="No active actions" description="Update filters to see more." />
        ) : (
          <div className="space-y-3">
            {activeActions.map((action) => (
              <div key={action.id} className="rounded-xl border border-slate-200 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-slate-900">
                      <button
                        type="button"
                        className="inline-flex items-center gap-1 rounded px-0 py-0 text-indigo-600 underline-offset-4 hover:underline focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                        onClick={() => handleActionClick(action)}
                      >
                        Action #{action.id}
                      </button>{' '}
                      • {action.title}
                    </p>
                    <p className="text-xs text-slate-500">Severity • {action.severity}</p>
                  </div>
                  <span className="text-xs uppercase text-slate-500">{getActionDisplayStatus(action.status)}</span>
                </div>
                {action.description && <p className="mt-2 text-sm text-slate-600">{action.description}</p>}
                <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                  <span>Started by {action.started_by?.full_name ?? 'Unknown'}</span>
                  <Link
                    to={`/inspections/${action.inspection_id}`}
                    className="font-semibold text-indigo-600 hover:underline"
                  >
                    View inspection
                  </Link>
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  Due {action.due_date ? `${formatDate(action.due_date)} (${formatRelative(action.due_date)})` : 'unspecified'}
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title="Closed / resolved actions" subtitle="Recently completed follow-ups">
        {closedActions.length === 0 ? (
          <EmptyState title="No closed actions yet" description="Completed corrective actions will appear here." />
        ) : (
          <div className="space-y-3">
            {closedActions.slice(0, 10).map((action) => {
              const closedAt = resolveActionDate(action.closed_at, action.created_at)
              return (
                <div key={action.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">
                        <button
                          type="button"
                          className="inline-flex items-center gap-1 rounded px-0 py-0 text-indigo-600 underline-offset-4 hover:underline focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
                          onClick={() => handleActionClick(action)}
                        >
                          Action #{action.id}
                        </button>{' '}
                        • {action.title}
                      </p>
                      <p className="text-xs text-slate-500">Severity • {action.severity}</p>
                    </div>
                    <span className="text-xs uppercase text-emerald-600">Closed</span>
                  </div>
                  {action.description && <p className="mt-2 text-sm text-slate-600">{action.description}</p>}
                  {action.resolution_notes && (
                    <p className="mt-2 text-sm text-slate-700">Resolution: {action.resolution_notes}</p>
                  )}
                  <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                    <span>Started by {action.started_by?.full_name ?? 'Unknown'}</span>
                    <Link
                      to={`/inspections/${action.inspection_id}`}
                      className="font-semibold text-indigo-600 hover:underline"
                    >
                      View inspection
                    </Link>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    Closed by {action.closed_by?.full_name ?? 'Unknown'} on{' '}
                    {`${formatDate(closedAt)} (${formatRelative(closedAt)})`}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      {selectedAction && (
        <ActionDetailsModal action={selectedAction} onClose={() => setSelectedActionId(null)} />
      )}
    </div>
  )
}
