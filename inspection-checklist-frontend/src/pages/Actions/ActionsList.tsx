import { useMemo, useState } from 'react'

import { useActionsQuery } from '@/api/hooks'
import { ACTION_SEVERITIES } from '@/lib/constants'
import { formatDate, formatRelative } from '@/lib/formatters'
import { Card } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { EmptyState } from '@/components/feedback/EmptyState'
import { LoadingState } from '@/components/feedback/LoadingState'

export const ActionsListPage = () => {
  const { data, isLoading } = useActionsQuery()
  const ACTIVE_STATUSES = ['open', 'in_progress'] as const
  const [severity, setSeverity] = useState<'all' | (typeof ACTION_SEVERITIES)[number]>('all')
  const [status, setStatus] = useState<'all' | (typeof ACTIVE_STATUSES)[number]>('all')

  const activeActions = useMemo(() => {
    if (!data) return []
    return data.filter((action) => {
      if (action.status === 'closed') return false
      const severityMatch = severity === 'all' || action.severity === severity
      const statusMatch = status === 'all' || action.status === status
      return severityMatch && statusMatch
    })
  }, [data, severity, status])

  const closedActions = useMemo(() => {
    if (!data) return []
    return data
      .filter((action) => action.status === 'closed')
      .sort((a, b) => {
        const dateA = new Date(a.closed_at ?? a.created_at).getTime()
        const dateB = new Date(b.closed_at ?? b.created_at).getTime()
        return dateB - dateA
      })
  }, [data])

  if (isLoading) {
    return <LoadingState label="Loading actions..." />
  }

  return (
    <div className="space-y-6">
      <Card
        title="Active corrective actions"
        subtitle="Monitor open and in-progress items"
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
            <Select value={status} onChange={(event) => setStatus(event.target.value as typeof status)}>
              <option value="all">All statuses</option>
              {ACTIVE_STATUSES.map((option) => (
                <option key={option} value={option}>
                  {option.replace('_', ' ')}
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
                    <p className="text-sm font-semibold text-slate-900">{action.title}</p>
                    <p className="text-xs text-slate-500">Severity • {action.severity}</p>
                  </div>
                  <span className="text-xs uppercase text-slate-500">{action.status.replace('_', ' ')}</span>
                </div>
                {action.description && <p className="mt-2 text-sm text-slate-600">{action.description}</p>}
                <div className="mt-3 text-xs text-slate-500">
                  Created by {action.created_by?.full_name ?? 'Unknown'}
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
              const closedAt = action.closed_at ?? action.created_at
              return (
                <div key={action.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{action.title}</p>
                      <p className="text-xs text-slate-500">Severity • {action.severity}</p>
                    </div>
                    <span className="text-xs uppercase text-emerald-600">Closed</span>
                  </div>
                  {action.description && <p className="mt-2 text-sm text-slate-600">{action.description}</p>}
                  <div className="mt-3 text-xs text-slate-500">
                    Created by {action.created_by?.full_name ?? 'Unknown'}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    Closed {`${formatDate(closedAt)} (${formatRelative(closedAt)})`}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}
