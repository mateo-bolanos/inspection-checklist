import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { useActionsQuery } from '@/api/hooks'
import type { components } from '@/api/gen/schema'
import { ACTION_SEVERITIES } from '@/lib/constants'
import { formatDate, formatRelative } from '@/lib/formatters'
import { Card } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/feedback/EmptyState'
import { LoadingState } from '@/components/feedback/LoadingState'
import { ActionDetailsModal } from '@/pages/Actions/ActionDetailsModal'
import { getActionDisplayStatus } from '@/pages/Actions/utils'

type ActionRecord = components['schemas']['CorrectiveActionRead']

const STATUS_FILTERS = ['all', 'open', 'closed'] as const
const DUE_FILTERS = [
  { value: 'all', label: 'All due dates' },
  { value: 'overdue', label: 'Overdue only' },
  { value: 'upcoming', label: 'Due within 7 days' },
] as const

type StatusFilter = (typeof STATUS_FILTERS)[number]
type DueFilter = (typeof DUE_FILTERS)[number]['value']

export const ActionsSearchPage = () => {
  const { data, isLoading } = useActionsQuery()
  const [severity, setSeverity] = useState<'all' | (typeof ACTION_SEVERITIES)[number]>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [dueFilter, setDueFilter] = useState<DueFilter>('all')
  const [query, setQuery] = useState('')
  const [selectedActionId, setSelectedActionId] = useState<number | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const actionParam = searchParams.get('actionId')
  const inspectionParam = searchParams.get('inspectionId')
  const [inspectionIdFilter, setInspectionIdFilter] = useState(inspectionParam ?? '')

  useEffect(() => {
    if (!data || !actionParam) return
    const actionId = Number(actionParam)
    if (Number.isFinite(actionId)) {
      const exists = data.some((action) => action.id === actionId)
      if (exists) {
        setSelectedActionId(actionId)
      }
    }
  }, [actionParam, data])

  useEffect(() => {
    setInspectionIdFilter(inspectionParam ?? '')
  }, [inspectionParam])

  const updateSearchParams = (entries: Record<string, string | null>) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(entries).forEach(([key, value]) => {
      if (value && value.trim().length > 0) {
        next.set(key, value)
      } else {
        next.delete(key)
      }
    })
    setSearchParams(next, { replace: true })
  }

  const filteredActions = useMemo(() => {
    if (!data) return []
    const normalizedQuery = query.trim().toLowerCase()
    const numericInspectionId = inspectionIdFilter ? Number(inspectionIdFilter) : null
    const withinDueWindow = (action: ActionRecord) => {
      if (dueFilter === 'all') return true
      if (!action.due_date) return false
      const dueDate = new Date(action.due_date)
      const now = Date.now()
      if (dueFilter === 'overdue') {
        return dueDate.getTime() < now
      }
      if (dueFilter === 'upcoming') {
        const diff = dueDate.getTime() - now
        return diff >= 0 && diff <= 7 * 24 * 60 * 60 * 1000
      }
      return true
    }

    return data.filter((action) => {
      if (severity !== 'all' && action.severity !== severity) return false
      const displayStatus = getActionDisplayStatus(action.status)
      if (statusFilter !== 'all' && displayStatus !== statusFilter) return false
      if (!withinDueWindow(action)) return false
      if (numericInspectionId && action.inspection_id !== numericInspectionId) return false
      if (!normalizedQuery) return true
      const haystack = [
        action.title,
        action.description,
        action.resolution_notes,
        action.started_by?.full_name,
        action.closed_by?.full_name,
        action.id.toString(),
        action.inspection_id.toString(),
      ]
        .filter(Boolean)
        .map((value) => value?.toString().toLowerCase())
      return haystack.some((value) => value?.includes(normalizedQuery))
    })
  }, [data, dueFilter, inspectionIdFilter, query, severity, statusFilter])

  const selectedAction =
    selectedActionId && data ? data.find((action) => action.id === selectedActionId) ?? null : null

  const updateActionParam = (actionId: number | null) => {
    updateSearchParams({ actionId: actionId ? actionId.toString() : null })
  }

  const handleInspectionFilterChange = (value: string) => {
    setInspectionIdFilter(value)
    updateSearchParams({ inspectionId: value.trim().length > 0 ? value : null })
  }

  const handleActionClick = (action: ActionRecord) => {
    setSelectedActionId(action.id)
    updateActionParam(action.id)
  }

  const handleModalClose = () => {
    setSelectedActionId(null)
    updateActionParam(null)
  }

  if (isLoading || !data) {
    return <LoadingState label="Loading actions..." />
  }

  return (
    <div className="space-y-6">
      <Card
        title="Search corrective actions"
        subtitle="Filter by severity, status, due date, inspection, or keywords"
        actions={
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search title, description, notes, or IDs"
            className="w-72"
          />
        }
      >
        <div className="flex flex-wrap gap-3">
          <Select
            value={severity}
            onChange={(event) => setSeverity(event.target.value as typeof severity)}
            className="w-40"
          >
            <option value="all">All severities</option>
            {ACTION_SEVERITIES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </Select>
          <Select
            value={statusFilter}
            onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            className="w-36"
          >
            {STATUS_FILTERS.map((option) => (
              <option key={option} value={option}>
                {option === 'all' ? 'All statuses' : option}
              </option>
            ))}
          </Select>
          <Select
            value={dueFilter}
            onChange={(event) => setDueFilter(event.target.value as DueFilter)}
            className="w-48"
          >
            {DUE_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min="1"
              value={inspectionIdFilter}
              onChange={(event) => handleInspectionFilterChange(event.target.value)}
              placeholder="Inspection ID"
              className="w-36"
            />
            {inspectionIdFilter && (
              <Button variant="ghost" type="button" onClick={() => handleInspectionFilterChange('')}>
                Clear inspection
              </Button>
            )}
          </div>
        </div>
      </Card>

      <Card>
        {filteredActions.length === 0 ? (
          <EmptyState title="No matching actions" description="Try adjusting your filters or search keywords." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2">Action</th>
                  <th className="px-4 py-2">Severity</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Due</th>
                  <th className="px-4 py-2">Inspection</th>
                  <th className="px-4 py-2 text-right">Details</th>
                </tr>
              </thead>
              <tbody>
                {filteredActions.map((action) => {
                  const displayStatus = getActionDisplayStatus(action.status)
                  return (
                    <tr key={action.id} className="border-t border-slate-100">
                      <td className="px-4 py-3 font-medium text-slate-900">
                        <div>Action #{action.id}</div>
                        <div className="text-sm font-normal text-slate-600">{action.title}</div>
                        <div className="text-xs text-slate-500">
                          Started by {action.started_by?.full_name ?? 'Unknown'}
                        </div>
                      </td>
                      <td className="px-4 py-3 capitalize text-slate-600">{action.severity}</td>
                      <td className="px-4 py-3 capitalize text-slate-600">
                        {displayStatus}
                        {action.status === 'closed' && action.closed_at && (
                          <div className="text-xs text-slate-500">
                            Closed {formatDate(action.closed_at)}
                          </div>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {action.due_date ? `${formatDate(action.due_date)} (${formatRelative(action.due_date)})` : 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        <Link to={`/inspections/${action.inspection_id}`} className="text-indigo-600 hover:underline">
                          View inspection
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          type="button"
                          className="text-sm font-semibold text-indigo-600 hover:underline"
                          onClick={() => handleActionClick(action)}
                        >
                          Open action
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {selectedAction && (
        <ActionDetailsModal action={selectedAction} onClose={handleModalClose} />
      )}
    </div>
  )
}
