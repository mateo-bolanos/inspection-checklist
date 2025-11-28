import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { useActionFilesQuery, useActionAssigneesQuery, useUpdateActionMutation, useUploadMediaMutation } from '@/api/hooks'
import { getErrorMessage } from '@/api/client'
import type { components } from '@/api/gen/schema'
import { useAuth } from '@/auth/useAuth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Modal } from '@/components/ui/Modal'
import { Select } from '@/components/ui/Select'
import { Textarea } from '@/components/ui/Textarea'
import { useToast } from '@/components/ui/toastContext'
import { formatDate, formatDateTime, formatRelative } from '@/lib/formatters'
import { downloadFileWithAuth } from '@/lib/download'
import { LoadingState } from '@/components/feedback/LoadingState'
import { getActionDisplayStatus } from '@/pages/Actions/utils'

type ActionRecord = components['schemas']['CorrectiveActionRead']

type ActionDetailsModalProps = {
  action: ActionRecord
  onClose: () => void
}

export const ActionDetailsModal = ({ action, onClose }: ActionDetailsModalProps) => {
  const filesQuery = useActionFilesQuery(action.id)
  const attachments = filesQuery.data ?? []
  const uploadMedia = useUploadMediaMutation()
  const updateAction = useUpdateActionMutation()
  const assigneesQuery = useActionAssigneesQuery()
  const assigneeOptions = assigneesQuery.data ?? []
  const { push } = useToast()
  const { hasRole } = useAuth()
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [noteDraft, setNoteDraft] = useState('')
  const [latestResolutionNote, setLatestResolutionNote] = useState(action.resolution_notes ?? '')
  const [assigneeId, setAssigneeId] = useState(action.assigned_to_id ?? '')
  const [workOrderRequired, setWorkOrderRequired] = useState<boolean>(action.work_order_required ?? false)
  const [workOrderNumber, setWorkOrderNumber] = useState<string>(action.work_order_number ?? '')
  const navigate = useNavigate()
  const canReassign = hasRole(['admin', 'reviewer'])
  const canClose = hasRole(['admin', 'reviewer'])
  const canViewInspection = hasRole(['admin', 'reviewer', 'inspector'])

  useEffect(() => {
    setNoteDraft('')
    setPendingFile(null)
    setAssigneeId(action.assigned_to_id ?? '')
    setLatestResolutionNote(action.resolution_notes ?? '')
    setWorkOrderRequired(action.work_order_required ?? false)
    setWorkOrderNumber(action.work_order_number ?? '')
  }, [action.id, action.assigned_to_id, action.resolution_notes])

  const handleDownload = async (file: components['schemas']['MediaFileRead']) => {
    const fallbackName = file.file_url.split('/').pop()
    try {
      await downloadFileWithAuth(file.file_url, fallbackName)
    } catch (error) {
      push({ title: 'Unable to download file', description: getErrorMessage(error), variant: 'error' })
    }
  }

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

  const handleAddNote = async () => {
    const content = noteDraft.trim()
    if (!content) {
      push({ title: 'Add notes before saving', variant: 'warning' })
      return
    }
    try {
      await updateAction.mutateAsync({
        actionId: action.id,
        data: { resolution_notes: content },
      })
      push({ title: 'Note saved', variant: 'success' })
      setNoteDraft('')
      setLatestResolutionNote(content)
    } catch (error) {
      push({ title: 'Unable to save notes', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleCloseAction = async () => {
    if (!canClose) {
      push({ title: 'Only managers can close actions', variant: 'warning' })
      return
    }
    if (displayStatus === 'closed') {
      push({ title: 'Action already closed', variant: 'warning' })
      return
    }
    const content = noteDraft.trim()
    const existing = latestResolutionNote.trim()
    if (!content && !existing) {
      push({ title: 'Add notes before closing', variant: 'warning' })
      return
    }
    try {
      await updateAction.mutateAsync({
        actionId: action.id,
        data: {
          status: 'closed',
          ...(content ? { resolution_notes: content } : {}),
        },
      })
      push({ title: 'Action closed', variant: 'success' })
      if (content) {
        setNoteDraft('')
        setLatestResolutionNote(content)
      }
    } catch (error) {
      push({ title: 'Unable to close action', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleReassign = async () => {
    if (!canReassign) return
    const nextAssignee = assigneeId.trim()
    if (!nextAssignee) {
      push({ title: 'Select an assignee', variant: 'warning' })
      return
    }
    try {
      await updateAction.mutateAsync({ actionId: action.id, data: { assigned_to_id: nextAssignee } })
      push({ title: 'Assignee updated', variant: 'success' })
    } catch (error) {
      push({ title: 'Unable to update assignee', description: String((error as Error).message), variant: 'error' })
    }
  }

  const handleWorkOrderUpdate = async () => {
    try {
      await updateAction.mutateAsync({
        actionId: action.id,
        data: {
          work_order_required: workOrderRequired,
          work_order_number: workOrderNumber || undefined,
        },
      })
      push({ title: 'Work order updated', variant: 'success' })
    } catch (error) {
      push({ title: 'Unable to update work order', description: String((error as Error).message), variant: 'error' })
    }
  }

  const goToInspection = () => {
    onClose()
    navigate(`/inspections/${action.inspection_id}`)
  }

  const isUploading = uploadMedia.isPending
  const isSaving = updateAction.isPending
  const noteEntries = useMemo(() => {
    const entries = action.note_entries ?? []
    return [...entries].sort(
      (a, b) => new Date(b.created_at ?? '').getTime() - new Date(a.created_at ?? '').getTime(),
    )
  }, [action.note_entries])
  const displayStatus = useMemo(() => getActionDisplayStatus(action.status), [action.status])

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
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Summary</h3>
              <dl className="mt-3 grid gap-3 sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-slate-500">Severity</dt>
                  <dd className="text-sm font-medium text-slate-900 capitalize">{action.severity}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Assigned to</dt>
                  <dd className="text-sm font-medium text-slate-900">
                    {action.assignee?.full_name || action.assignee?.email || 'Unassigned'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Status</dt>
                  <dd className="text-sm font-medium text-slate-900 capitalize">{displayStatus}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Due date</dt>
                  <dd className="text-sm font-medium text-slate-900">
                    {action.due_date
                      ? `${formatDate(action.due_date)} (${formatRelative(action.due_date)})`
                      : 'unspecified'}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Started by</dt>
                  <dd className="text-sm font-medium text-slate-900">{action.started_by?.full_name ?? 'Unknown'}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Work order required</dt>
                  <dd className="text-sm font-medium text-slate-900">{action.work_order_required ? 'Yes' : 'No'}</dd>
                </div>
                {action.work_order_number && (
                  <div>
                    <dt className="text-xs text-slate-500">Work order #</dt>
                    <dd className="text-sm font-medium text-slate-900">{action.work_order_number}</dd>
                  </div>
                )}
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
            </div>
            {canViewInspection && (
              <Button type="button" variant="secondary" onClick={goToInspection}>
                View inspection
              </Button>
            )}
          </div>
        </section>

        {canReassign && (
          <section className="rounded-xl border border-slate-100 p-4">
            <div className="flex flex-wrap items-center gap-3">
              <div>
                <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Reassign</h3>
                <p className="text-xs text-slate-500">Send this action to another owner or inspector.</p>
              </div>
              <div className="flex flex-1 flex-wrap gap-2">
                <Select
                  value={assigneeId}
                  onChange={(event) => setAssigneeId(event.target.value)}
                  disabled={assigneesQuery.isLoading}
                >
                  <option value="">Select a user</option>
                  {assigneeOptions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.full_name || option.email}
                    </option>
                  ))}
                </Select>
                <Button type="button" onClick={handleReassign} disabled={isSaving || !assigneeId}>
                  Update assignee
                </Button>
              </div>
            </div>
            {assigneesQuery.isError && <p className="mt-2 text-xs text-red-600">Unable to load potential assignees.</p>}
          </section>
        )}

        <section className="rounded-xl border border-slate-100 p-4 space-y-3">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Details</h3>
          {action.description ? (
            <p className="text-sm text-slate-700">
              <span className="font-semibold">Description:</span> {action.description}
            </p>
          ) : (
            <p className="text-sm text-slate-500">No description provided.</p>
          )}
        </section>

        {canClose && (
          <section className="rounded-xl border border-slate-100 p-4 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Work order</h3>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={workOrderRequired}
                  onChange={(event) => setWorkOrderRequired(event.target.checked)}
                />
                Work order required to close
              </label>
              <Input
                value={workOrderNumber}
                onChange={(event) => setWorkOrderNumber(event.target.value)}
                placeholder="WO-1234"
                className="w-48"
              />
              <Button type="button" variant="secondary" onClick={handleWorkOrderUpdate} disabled={isSaving}>
                Save work order
              </Button>
            </div>
            {action.work_order_required && !action.work_order_number && (
              <p className="text-xs text-amber-700">A work order number is required before closing this action.</p>
            )}
          </section>
        )}

        <section className="rounded-xl border border-slate-100 p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Notes</h3>
          <p className="mt-2 text-xs text-slate-500">Use notes to track progress before closing the action.</p>
          <Textarea
            className="mt-3"
            value={noteDraft}
            onChange={(event) => setNoteDraft(event.target.value)}
            placeholder="Add investigation notes or interim updates"
            rows={4}
            disabled={isSaving}
          />
          <div className="mt-3 flex flex-wrap gap-3">
            <Button type="button" variant="secondary" onClick={handleAddNote} disabled={isSaving}>
              Save note
            </Button>
            <Button
              type="button"
              onClick={handleCloseAction}
              disabled={displayStatus === 'closed' || isSaving || !canClose}
            >
              {displayStatus === 'closed' ? 'Action closed' : 'Close action'}
            </Button>
            {displayStatus === 'closed' && action.closed_at && (
              <p className="text-xs text-slate-500">
                Closed on {formatDate(action.closed_at)} by {action.closed_by?.full_name ?? 'Unknown'}
              </p>
            )}
          </div>
          <div className="mt-4 max-h-60 space-y-2 overflow-y-auto rounded-xl border border-slate-100 p-3">
            {noteEntries.length === 0 ? (
              <p className="text-sm text-slate-500">No notes recorded yet.</p>
            ) : (
              noteEntries.map((entry) => (
                <div key={entry.id} className="rounded-lg border border-slate-100 bg-white p-2">
                  <p className="text-xs font-medium text-slate-500">
                    {entry.author?.full_name || entry.author?.email || entry.author_id || 'Unknown user'} •{' '}
                    {formatDateTime(entry.created_at)}
                  </p>
                  <p className="text-sm text-slate-900 whitespace-pre-line">{entry.body}</p>
                </div>
              ))
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
            <Button type="submit" disabled={!pendingFile || isUploading}>
              {isUploading ? 'Uploading...' : 'Upload image'}
            </Button>
          </form>
          <div className="mt-3 space-y-3">
            {filesQuery.isLoading ? (
              <LoadingState label="Loading attachments..." />
            ) : filesQuery.isError ? (
              <p className="text-sm text-red-600">Unable to load attachments right now.</p>
            ) : attachments.length === 0 ? (
              <p className="text-sm text-slate-500">No attachments uploaded yet.</p>
            ) : (
              attachments.map((file) => (
                <div key={file.id} className="rounded-lg border border-slate-200 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <button
                      type="button"
                      className="text-sm font-semibold text-indigo-600 hover:underline"
                      onClick={() => handleDownload(file)}
                    >
                      Download file
                    </button>
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
