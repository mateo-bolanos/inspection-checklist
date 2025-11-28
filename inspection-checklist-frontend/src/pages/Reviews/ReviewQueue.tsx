import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import {
  useApproveInspectionMutation,
  useInspectionQuery,
  useInspectionsQuery,
  useRejectInspectionMutation,
  useTemplateQuery,
  useTemplatesQuery,
} from '@/api/hooks'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { EmptyState } from '@/components/feedback/EmptyState'
import { LoadingState } from '@/components/feedback/LoadingState'
import { formatDateTime, formatInspectionName } from '@/lib/formatters'
import { useToast } from '@/components/ui/toastContext'
import { Modal } from '@/components/ui/Modal'
import { Textarea } from '@/components/ui/Textarea'
import { Checkbox } from '@/components/ui/Checkbox'

export const ReviewQueuePage = () => {
  const inspections = useInspectionsQuery()
  const templates = useTemplatesQuery()
  const approve = useApproveInspectionMutation()
  const reject = useRejectInspectionMutation()
  const { push } = useToast()
  const [rejecting, setRejecting] = useState<{ id: number | string; label: string } | null>(null)
  const [reason, setReason] = useState('')
  const [followUp, setFollowUp] = useState('')
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set())
  const inspectionDetail = useInspectionQuery(rejecting?.id ?? '', { enabled: Boolean(rejecting?.id) })
  const templateDetail = useTemplateQuery(inspectionDetail.data?.template_id, {
    enabled: Boolean(inspectionDetail.data?.template_id),
  })

  const allTemplateItems = useMemo(() => {
    const template = templateDetail.data
    if (!template) return []
    return template.sections?.flatMap((section) =>
      (section.items || []).map((item) => ({
        id: item.id,
        prompt: item.prompt || item.id,
      })),
    ) || []
  }, [templateDetail.data])

  const failingItemIds = useMemo(() => {
    const detail = inspectionDetail.data
    if (!detail) return new Set<string>()
    return new Set((detail.responses || []).filter((resp) => resp.result === 'fail').map((resp) => resp.template_item_id))
  }, [inspectionDetail.data])

  useEffect(() => {
    if (failingItemIds.size > 0) {
      setSelectedItems(new Set(failingItemIds))
    } else {
      setSelectedItems(new Set())
    }
  }, [failingItemIds])

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
    const trimmedReason = reason.trim()
    const trimmedFollowUp = followUp.trim()
    if (!trimmedReason) {
      push({ title: 'Rejection reason required', description: 'Explain why the inspection is denied.', variant: 'error' })
      return
    }
    if (selectedItems.size === 0) {
      push({ title: 'Select at least one failed item', variant: 'error' })
      return
    }
    try {
      await reject.mutateAsync({
        inspectionId,
        reason: trimmedReason,
        follow_up_instructions: trimmedFollowUp || undefined,
        item_ids: Array.from(selectedItems),
      })
      push({ title: 'Inspection rejected', variant: 'success' })
      setRejecting(null)
      setReason('')
      setFollowUp('')
      setSelectedItems(new Set())
    } catch (error) {
      push({ title: 'Reject failed', description: String((error as Error).message), variant: 'error' })
    }
  }

  if (inspections.isLoading) {
    return <LoadingState label="Loading review queue..." />
  }

  const closeRejectDialog = () => {
    setRejecting(null)
    setReason('')
    setFollowUp('')
    setSelectedItems(new Set())
  }

  return (
    <>
      <Card title="Review queue" subtitle="Submitted inspections awaiting review">
        {queue.length === 0 ? (
          <EmptyState title="All caught up" description="No inspections need review." />
        ) : (
          <div className="space-y-3">
            {queue.map((inspection) => {
              const inspectionLabel = formatInspectionName(
                templateNameMap.get(inspection.template_id) || 'Inspection',
                inspection.started_at,
                inspection.id,
              )
              return (
                <div key={inspection.id} className="rounded-xl border border-slate-200 p-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-slate-900">{inspectionLabel}</p>
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
                        <Button
                          variant="ghost"
                          onClick={() => {
                            setRejecting({ id: inspection.id, label: inspectionLabel })
                            setReason('')
                            setFollowUp('')
                          }}
                          disabled={reject.isPending}
                        >
                          Reject
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      <Modal
        open={Boolean(rejecting)}
        onOpenChange={(open) => {
          if (!open) {
            closeRejectDialog()
          }
        }}
        title={rejecting ? `Reject ${rejecting.label}` : 'Reject inspection'}
        description="Send this inspection back to the inspector with a denial note and rework instructions."
      >
        <div className="space-y-3">
          {inspectionDetail.isLoading && <p className="text-xs text-slate-500">Loading inspection details...</p>}
          {templateDetail.isLoading && <p className="text-xs text-slate-500">Loading checklist items...</p>}
          {allTemplateItems.length > 0 && (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="text-xs font-semibold uppercase text-amber-700">Select items to send back</p>
              <div className="mt-2 space-y-2">
                {allTemplateItems.map((item) => (
                  <label key={item.id} className="flex items-start gap-2 text-sm text-slate-800">
                    <Checkbox
                      checked={selectedItems.has(item.id)}
                      onCheckedChange={(checked) => {
                        setSelectedItems((current) => {
                          const next = new Set(current)
                          if (checked) {
                            next.add(item.id)
                          } else {
                            next.delete(item.id)
                          }
                          return next
                        })
                      }}
                    />
                    <span>{item.prompt}</span>
                  </label>
                ))}
              </div>
            </div>
          )}
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">Why is it denied?</p>
            <Textarea
              placeholder="Explain what failed review and why."
              value={reason}
              onChange={(event) => setReason(event.target.value)}
              rows={3}
            />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase text-slate-500">What must be fixed?</p>
            <Textarea
              placeholder="List the corrective work the inspector should complete before resubmitting."
              value={followUp}
              onChange={(event) => setFollowUp(event.target.value)}
              rows={3}
            />
            <p className="mt-1 text-xs text-slate-500">
              This will generate an urgent assignment tagged “Denied” for the original inspector.
            </p>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={closeRejectDialog} disabled={reject.isPending}>
              Cancel
            </Button>
            <Button
              type="button"
              variant="secondary"
              loading={reject.isPending}
              onClick={() => (rejecting ? handleReject(rejecting.id) : null)}
            >
              Send back to inspector
            </Button>
          </div>
        </div>
      </Modal>
    </>
  )
}
