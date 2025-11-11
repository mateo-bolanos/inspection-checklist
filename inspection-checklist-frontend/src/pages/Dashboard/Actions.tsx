import { useMemo, useState } from 'react'

import { useActionsQuery, useDashboardActionsQuery } from '@/api/hooks'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { formatDate, formatRelative } from '@/lib/formatters'

const severityOptions = ['all', 'low', 'medium', 'high', 'critical'] as const
const dueFilters = [
  { value: 'all', label: 'All due dates' },
  { value: 'overdue', label: 'Overdue only' },
  { value: 'upcoming', label: 'Due within 7 days' },
] as const

type DueFilter = (typeof dueFilters)[number]['value']

export const DashboardActionsPage = () => {
  const dashboard = useDashboardActionsQuery()
  const actionsQuery = useActionsQuery()
  const [severity, setSeverity] = useState<(typeof severityOptions)[number]>('all')
  const [dueFilter, setDueFilter] = useState<DueFilter>('all')

  const filteredActions = useMemo(() => {
    if (!actionsQuery.data) return []
    return actionsQuery.data.filter((action) => {
      if (severity !== 'all' && action.severity !== severity) return false
      if (dueFilter === 'overdue' && !action.due_date) return false
      if (dueFilter === 'overdue') {
        return new Date(action.due_date) < new Date()
      }
      if (dueFilter === 'upcoming' && action.due_date) {
        const due = new Date(action.due_date)
        const diff = due.getTime() - Date.now()
        return diff >= 0 && diff <= 7 * 24 * 60 * 60 * 1000
      }
      return true
    })
  }, [actionsQuery.data, dueFilter, severity])

  if (dashboard.isError) {
    return <ErrorState message="Could not load action metrics" action={<Button variant="ghost" onClick={() => dashboard.refetch()}>Retry</Button>} />
  }

  return (
    <div className="space-y-6">
      {dashboard.data && (
        <Card title="Open actions by severity">
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
        </Card>
      )}

      <Card
        title="Corrective actions"
        actions={
          <div className="flex flex-wrap gap-2 text-sm">
            <Select value={severity} onChange={(event) => setSeverity(event.target.value as (typeof severityOptions)[number])}>
              {severityOptions.map((option) => (
                <option key={option} value={option}>
                  {option === 'all' ? 'All severities' : option}
                </option>
              ))}
            </Select>
            <Select value={dueFilter} onChange={(event) => setDueFilter(event.target.value as DueFilter)}>
              {dueFilters.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
        }
      >
        {actionsQuery.isLoading ? (
          <p className="text-sm text-slate-500">Loading actions...</p>
        ) : filteredActions.length === 0 ? (
          <EmptyState title="No actions" description="Nothing matches your filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2">Title</th>
                  <th className="px-4 py-2">Severity</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Due</th>
                </tr>
              </thead>
              <tbody>
                {filteredActions.map((action) => (
                  <tr key={action.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-medium text-slate-900">{action.title}</td>
                    <td className="px-4 py-3 capitalize text-slate-600">{action.severity}</td>
                    <td className="px-4 py-3 text-slate-600">{action.status}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {action.due_date ? `${formatDate(action.due_date)} (${formatRelative(action.due_date)})` : 'N/A'}
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
