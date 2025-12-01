import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { useActionsQuery, useActionAssigneesQuery } from '@/api/hooks'
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
import { useAuth } from '@/auth/useAuth'

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
  const { user, hasRole } = useAuth()
  const canSeeAll = hasRole(['admin', 'reviewer'])
  const assigneesQuery = useActionAssigneesQuery()
  const assigneeOptions = assigneesQuery.data ?? []
  const [severity, setSeverity] = useState<'all' | (typeof ACTION_SEVERITIES)[number]>('all')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [dueFilter, setDueFilter] = useState<DueFilter>('all')
  const [query, setQuery] = useState('')
  const [selectedActionId, setSelectedActionId] = useState<number | null>(null)
  const [searchParams, setSearchParams] = useSearchParams()
  const actionParam = searchParams.get('actionId')
  const inspectionParam = searchParams.get('inspectionId')
  const assigneeParam = searchParams.get('assigneeId')
  const mineParam = searchParams.get('mine')
  const locationParam = searchParams.get('location')
  const [inspectionIdFilter, setInspectionIdFilter] = useState(inspectionParam ?? '')
  const [assigneeFilter, setAssigneeFilter] = useState(assigneeParam ?? '')
  const [locationFilter, setLocationFilter] = useState(locationParam ?? '')
  const [mineOnlyState, setMineOnlyState] = useState(mineParam === '1' || !canSeeAll)
  const mineOnly = !canSeeAll || mineOnlyState
  const isActionOwner = !canSeeAll
  const assignedToParam = mineOnly ? user?.id ?? undefined : assigneeFilter || undefined
  const { data, isLoading } = useActionsQuery({
    assignedTo: assignedToParam,
    location: locationFilter || null,
    enabled: !mineOnly || Boolean(user?.id),
  })

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

  useEffect(() => {
    setAssigneeFilter(assigneeParam ?? '')
  }, [assigneeParam])

  useEffect(() => {
    setLocationFilter(locationParam ?? '')
  }, [locationParam])

  useEffect(() => {
    if (canSeeAll) {
      setMineOnlyState(mineParam === '1')
    }
  }, [mineParam, canSeeAll])

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
    const normalizedLocation = locationFilter.trim().toLowerCase()
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
      if (normalizedLocation) {
        const locationValue = (action.inspection_location ?? '').toLowerCase()
        if (!locationValue.includes(normalizedLocation)) return false
      }
      if (!withinDueWindow(action)) return false
      if (numericInspectionId && action.inspection_id !== numericInspectionId) return false
      if (!normalizedQuery) return true
      const haystack = [
        action.title,
        action.description,
        action.resolution_notes,
        action.started_by?.full_name,
        action.closed_by?.full_name,
        action.assignee?.full_name,
        action.assignee?.email,
        action.inspection_location,
        action.id.toString(),
        action.inspection_id.toString(),
      ]
        .filter(Boolean)
        .map((value) => value?.toString().toLowerCase())
      return haystack.some((value) => value?.includes(normalizedQuery))
    })
  }, [data, dueFilter, inspectionIdFilter, locationFilter, query, severity, statusFilter])

  const selectedAction =
    selectedActionId && data ? data.find((action) => action.id === selectedActionId) ?? null : null

  const updateActionParam = (actionId: number | null) => {
    updateSearchParams({ actionId: actionId ? actionId.toString() : null })
  }

  const handleInspectionFilterChange = (value: string) => {
    setInspectionIdFilter(value)
    updateSearchParams({ inspectionId: value.trim().length > 0 ? value : null })
  }

  const handleAssigneeFilterChange = (value: string) => {
    setAssigneeFilter(value)
    updateSearchParams({ assigneeId: value.trim().length > 0 ? value : null })
  }

  const handleLocationFilterChange = (value: string) => {
    setLocationFilter(value)
    updateSearchParams({ location: value.trim().length > 0 ? value : null })
  }

  const handleMineOnlyChange = (checked: boolean) => {
    if (!canSeeAll) return
    setMineOnlyState(checked)
    updateSearchParams({ mine: checked ? '1' : null })
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
    return <LoadingState label="Loading issues..." />
  }

  return (
    <div className="space-y-6">
      <Card
        title="Search issues"
        subtitle="Filter by severity, status, due date, inspection, or keywords"
        actions={
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search issue name, corrective action, notes, or IDs"
            className="w-72"
          />
        }
      >
        <div className="flex flex-wrap gap-3 lg:flex-nowrap lg:items-center">
          <div className="min-w-[10rem] flex-shrink-0">
            <Select
              value={severity}
              onChange={(event) => setSeverity(event.target.value as typeof severity)}
            >
              <option value="all">All severities</option>
              {ACTION_SEVERITIES.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </Select>
          </div>
          <div className="min-w-[9rem] flex-shrink-0">
            <Select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}>
              {STATUS_FILTERS.map((option) => (
                <option key={option} value={option}>
                  {option === 'all' ? 'All statuses' : option}
                </option>
              ))}
            </Select>
          </div>
          <div className="min-w-[12rem] flex-shrink-0">
            <Input
              value={locationFilter}
              onChange={(event) => handleLocationFilterChange(event.target.value)}
              placeholder="Filter by department/location"
            />
          </div>
          <div className="min-w-[12rem] flex-shrink-0">
            <Select value={dueFilter} onChange={(event) => setDueFilter(event.target.value as DueFilter)}>
              {DUE_FILTERS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex items-center gap-2 min-w-[12rem] flex-shrink-0">
            <Input
              type="number"
              min="1"
              value={inspectionIdFilter}
              onChange={(event) => handleInspectionFilterChange(event.target.value)}
              placeholder="Inspection ID"
            />
            {inspectionIdFilter && (
              <Button variant="ghost" type="button" onClick={() => handleInspectionFilterChange('')}>
                Clear inspection
              </Button>
            )}
          </div>
          <div className="min-w-[12rem] flex-shrink-0">
            <Select
              value={assigneeFilter}
              onChange={(event) => handleAssigneeFilterChange(event.target.value)}
              disabled={mineOnly || assigneesQuery.isLoading}
            >
              <option value="">All assignees</option>
              {assigneeOptions.map((assignee) => (
                <option key={assignee.id} value={assignee.id}>
                  {assignee.full_name || assignee.email || 'User'}
                </option>
              ))}
            </Select>
          </div>
          <label className="flex items-center gap-2 text-sm text-slate-600">
            <input
              type="checkbox"
              checked={mineOnly}
              onChange={(event) => handleMineOnlyChange(event.target.checked)}
              disabled={isActionOwner}
            />
            Mine only
          </label>
        </div>
      </Card>

      <Card>
        {filteredActions.length === 0 ? (
          <EmptyState title="No matching issues" description="Try adjusting your filters or search keywords." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2">Issue</th>
                  <th className="px-4 py-2">Severity</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Due</th>
                  <th className="px-4 py-2">Assignee</th>
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
                        <div>Issue #{action.id}</div>
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
                        {action.assignee?.full_name || action.assignee?.email || 'Unassigned'}
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
                          Open issue
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
