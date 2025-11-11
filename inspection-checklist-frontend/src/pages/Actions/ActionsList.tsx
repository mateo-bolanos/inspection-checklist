import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'

import {
  useActionsQuery,
  useActionFilesQuery,
  useDashboardActionsQuery,
  useUpdateActionMutation,
  useUploadMediaMutation,
} from '@/api/hooks'
import type { components } from '@/api/gen/schema'
import { ACTION_SEVERITIES } from '@/lib/constants'
import { formatDate, formatDateTime, formatRelative } from '@/lib/formatters'
import { useToast } from '@/components/ui/Toast'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Select } from '@/components/ui/Select'
import { Modal } from '@/components/ui/Modal'
import { Textarea } from '@/components/ui/Textarea'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { LoadingState } from '@/components/feedback/LoadingState'

type ActionRecord = components['schemas']['CorrectiveActionRead']

const dueFilters = [
  { value: 'all', label: 'All due dates' },
  { value: 'overdue', label: 'Overdue only' },
  { value: 'upcoming', label: 'Due within 7 days' },
] as const

type DueFilter = (typeof dueFilters)[number]['value']

const getDisplayStatus = (status: ActionRecord['status']) => (status === 'in_progress' ? 'open' : status)

export const ActionsListPage = () => {
  const { data, isLoading } = useActionsQuery()
  const dashboard = useDashboardActionsQuery()
  const [severity, setSeverity] = useState<'all' | (typeof ACTION_SEVERITIES)[number]>('all')
  const [dueFilter, setDueFilter] = useState<DueFilter>('all')
  const [selectedActionId, setSelectedActionId] = useState<number | null>(null)

  const resolveActionDate = (value?: string | null, fallback?: string | null): string =>
    value ?? fallback ?? new Date().toISOString()

  const activeActions = useMemo(() => {
    if (!data) return []
    return data.filter((action) => {
      if (action.status === 'closed') return false
      const severityMatch = severity === 'all' || action.severity === severity
      const isOpen = getDisplayStatus(action.status) === 'open'
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

  const filteredActions = useMemo(() => {
    if (!data) return []
    return data.filter((action) => {
      if (severity !== 'all' && action.severity !== severity) return false
      if (dueFilter === 'overdue') {
        if (!action.due_date) return false
        return new Date(action.due_date).getTime() < Date.now()
      }
      if (dueFilter === 'upcoming') {
        if (!action.due_date) return false
        const due = new Date(action.due_date)
        const diff = due.getTime() - Date.now()
        return diff >= 0 && diff <= 7 * 24 * 60 * 60 * 1000
      }
      return true
    })
  }, [data, dueFilter, severity])

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
      <Card title="Action overview">
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
                  <span className="text-xs uppercase text-slate-500">{getDisplayStatus(action.status)}</span>
                </div>
                {action.description && <p className="mt-2 text-sm text-slate-600">{action.description}</p>}
                <div className="mt-3 text-xs text-slate-500">
                  Started by {action.started_by?.full_name ?? 'Unknown'}
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
                  <div className="mt-3 text-xs text-slate-500">
                    Started by {action.started_by?.full_name ?? 'Unknown'}
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

      <Card
        title="All corrective actions"
        subtitle="Full list filtered by severity (above) and due date"
        actions={
          <div className="flex flex-wrap gap-2 text-sm">
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
        {filteredActions.length === 0 ? (
          <EmptyState title="No actions" description="Nothing matches your filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-2">Action</th>
                  <th className="px-4 py-2">Severity</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Due</th>
                </tr>
              </thead>
              <tbody>
                {filteredActions.map((action) => (
                  <tr key={action.id} className="border-t border-slate-100">
                    <td className="px-4 py-3 font-medium text-slate-900">
                      <div>Action #{action.id}</div>
                      <div className="text-sm font-normal text-slate-600">{action.title}</div>
                      <div className="text-xs text-slate-500">
                        Started by {action.started_by?.full_name ?? 'Unknown'}
                      </div>
                    </td>
                    <td className="px-4 py-3 capitalize text-slate-600">{action.severity}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {getDisplayStatus(action.status)}
                      {action.status === 'closed' && (
                        <div className="text-xs text-slate-500">
                          Closed by {action.closed_by?.full_name ?? 'Unknown'}
                          {action.closed_at ? ` • ${formatDate(action.closed_at)}` : ''}
                        </div>
                      )}
                    </td>
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

      {selectedAction && (
        <ActionDetailsModal action={selectedAction} onClose={() => setSelectedActionId(null)} />
      )}
    </div>
  )
}

type ActionDetailsModalProps = {
  action: ActionRecord
  onClose: () => void
}

const ActionDetailsModal = ({ action, onClose }: ActionDetailsModalProps) => {
  const filesQuery = useActionFilesQuery(action.id)
  const attachments = filesQuery.data ?? []
  const uploadMedia = useUploadMediaMutation()
  const updateAction = useUpdateActionMutation()
  const { push } = useToast()
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [resolutionNotes, setResolutionNotes] = useState(action.resolution_notes ?? '')

  useEffect(() => {
    setResolutionNotes(action.resolution_notes ?? '')
    setPendingFile(null)
  }, [action.id, action.resolution_notes])

  const handleUpload = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!pendingFile) {
      push({ title: 'Choose an image first', variant: 'warning' })
      return
    }
    try {
      await uploadMedia.mutateAsync({ file: pendingFile, actionId: action.id })
      push({ title: 'Image uploaded', variant: 'success' })
      setPendingFile(null)
      filesQuery.refetch()
    } catch (error) {
      push({ title: 'Upload failed', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleCloseAction = async () => {
    if (action.status === 'closed') {
      push({ title: 'Action already closed', variant: 'info' })
      return
    }
    if (!resolutionNotes.trim()) {
      push({ title: 'Add resolution notes first', variant: 'warning' })
      return
    }
    try {
      await updateAction.mutateAsync({
        actionId: action.id,
        data: { status: 'closed', resolution_notes: resolutionNotes.trim() },
      })
      push({ title: 'Action closed', variant: 'success' })
    } catch (error) {
      push({ title: 'Unable to close action', description: String((error as Error).message), variant: 'error' })
    }
  }

  return (
    <Modal
      open
      onOpenChange={(open) => {
        if (!open) onClose()
      }}
      title={`Action #${action.id}`}
      description={action.title}
      widthClass="w-full max-w-2xl"
    >
      <div className="space-y-6 text-sm">
        <section className="rounded-xl border border-slate-100 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Summary</h3>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs text-slate-500">Severity</dt>
              <dd className="text-sm font-medium text-slate-900 capitalize">{action.severity}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Status</dt>
              <dd className="text-sm font-medium text-slate-900 capitalize">{getDisplayStatus(action.status)}</dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Due date</dt>
              <dd className="text-sm font-medium text-slate-900">
                {action.due_date ? `${formatDate(action.due_date)} (${formatRelative(action.due_date)})` : 'unspecified'}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-slate-500">Started by</dt>
              <dd className="text-sm font-medium text-slate-900">{action.started_by?.full_name ?? 'Unknown'}</dd>
            </div>
            {action.closed_by && (
              <div className="sm:col-span-2">
                <dt className="text-xs text-slate-500">Closed by</dt>
                <dd className="text-sm font-medium text-slate-900">
                  {action.closed_by.full_name}
                  {action.closed_at ? ` • ${formatDate(action.closed_at)}` : ''}
                </dd>
              </div>
            )}
          </dl>
        </section>

        <section className="rounded-xl border border-slate-100 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Notes</h3>
          <div className="mt-3 space-y-3 text-sm text-slate-700">
            {action.description && (
              <p>
                <span className="font-semibold">Details:</span> {action.description}
              </p>
            )}
            {action.resolution_notes && (
              <p>
                <span className="font-semibold">Resolution:</span> {action.resolution_notes}
              </p>
            )}
            {!action.description && !action.resolution_notes && (
              <p className="text-slate-500">No notes recorded for this action yet.</p>
            )}
          </div>
        </section>

        <section className="rounded-xl border border-slate-100 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Resolution</h3>
          <div className="mt-3 space-y-3">
            <Textarea
              value={resolutionNotes}
              onChange={(event) => setResolutionNotes(event.target.value)}
              placeholder="Describe how this action was resolved"
              rows={4}
            />
            <Button
              type="button"
              onClick={handleCloseAction}
              disabled={action.status === 'closed' || updateAction.isPending}
            >
              {action.status === 'closed' ? 'Action closed' : 'Close action'}
            </Button>
            {action.status === 'closed' && action.closed_at && (
              <p className="text-xs text-slate-500">
                Closed on {formatDate(action.closed_at)} by {action.closed_by?.full_name ?? 'Unknown'}
              </p>
            )}
          </div>
        </section>

        <section className="rounded-xl border border-slate-100 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Attachments</h3>
              <p className="text-xs text-slate-500">Add images to document the corrective action.</p>
            </div>
            <button
              type="button"
              className="text-xs font-medium text-indigo-600 hover:underline focus:outline-none focus:ring-2 focus:ring-indigo-500/40"
              onClick={() => filesQuery.refetch()}
              disabled={filesQuery.isLoading}
            >
              Refresh
            </button>
          </div>
          <form className="mt-3 flex flex-col gap-2 sm:flex-row sm:items-center" onSubmit={handleUpload}>
            <input
              type="file"
              accept="image/*"
              onChange={(event) => setPendingFile(event.target.files?.[0] ?? null)}
              className="text-sm"
            />
            <Button type="submit" disabled={!pendingFile || uploadMedia.isPending}>
              {uploadMedia.isPending ? 'Uploading...' : 'Upload image'}
            </Button>
          </form>
          <div className="mt-3 space-y-3">
            {filesQuery.isLoading ? (
              <p className="text-sm text-slate-500">Loading attachments...</p>
            ) : filesQuery.isError ? (
              <p className="text-sm text-red-600">Unable to load attachments right now.</p>
            ) : attachments.length === 0 ? (
              <p className="text-sm text-slate-500">No attachments uploaded yet.</p>
            ) : (
              attachments.map((file) => (
                <div key={file.id} className="rounded-lg border border-slate-200 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <a
                      href={file.file_url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm font-semibold text-indigo-600 hover:underline"
                    >
                      View file
                    </a>
                    <span className="text-xs text-slate-500">{formatDateTime(file.created_at)}</span>
                  </div>
                  <p className="text-xs text-slate-500">
                    Uploaded by {file.uploaded_by?.full_name ?? 'Unknown'}
                    {file.description ? ` • ${file.description}` : ''}
                  </p>
                </div>
              ))
            )}
          </div>
        </section>
      </div>
    </Modal>
  )
}
