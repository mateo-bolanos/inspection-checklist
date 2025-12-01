import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getErrorMessage } from '@/api/client'
import { useDeleteInspectionMutation, useInspectionsQuery, useTemplatesQuery } from '@/api/hooks'
import { useAuth } from '@/auth/useAuth'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { LoadingState } from '@/components/feedback/LoadingState'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { useToast } from '@/components/ui/toastContext'
import { INSPECTION_STATUSES } from '@/lib/constants'
import { formatDate, formatInspectionName, formatScore } from '@/lib/formatters'

type StatusFilter = 'all' | (typeof INSPECTION_STATUSES)[number]
type OriginFilter = 'all' | 'assignment' | 'independent'
const PAGE_SIZE = 30

export const InspectionsListPage = () => {
  const navigate = useNavigate()
  const { hasRole } = useAuth()
  const [page, setPage] = useState(1)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [templateFilter, setTemplateFilter] = useState<'all' | string>('all')
  const [originFilter, setOriginFilter] = useState<OriginFilter>('all')
  const [locationFilter, setLocationFilter] = useState('')
  const inspectionsQuery = useInspectionsQuery({
    page,
    pageSize: PAGE_SIZE,
    status: statusFilter === 'all' ? null : statusFilter,
    templateId: templateFilter === 'all' ? null : templateFilter,
    origin: originFilter === 'all' ? null : originFilter,
    location: locationFilter.trim() || null,
    search: searchTerm.trim() || null,
  })
  const templatesQuery = useTemplatesQuery()
  const deleteMutation = useDeleteInspectionMutation()
  const { push } = useToast()

  const templateNameMap = useMemo(() => {
    const map = new Map<string, string>()
    templatesQuery.data?.forEach((template) => {
      map.set(template.id, template.name)
    })
    return map
  }, [templatesQuery.data])

  useEffect(() => {
    if (!inspectionsQuery.data) return
    const totalPages = Math.max(1, Math.ceil((inspectionsQuery.data.total || 0) / PAGE_SIZE))
    if (page > totalPages) {
      setPage(totalPages)
    }
  }, [inspectionsQuery.data, page])

  const canCreateInspection = hasRole(['admin', 'inspector'])
  const canEditInspections = canCreateInspection

  const inspections = inspectionsQuery.data?.items ?? []
  const totalCount = inspectionsQuery.data?.total ?? 0
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE))
  const showingStart = inspections.length === 0 ? 0 : (page - 1) * PAGE_SIZE + 1
  const showingEnd = inspections.length === 0 ? 0 : (page - 1) * PAGE_SIZE + inspections.length

  const handleDelete = async (inspectionId: number) => {
    if (!window.confirm('Delete this draft inspection? This cannot be undone.')) return
    try {
      await deleteMutation.mutateAsync(inspectionId)
      push({ title: 'Inspection deleted', variant: 'success' })
    } catch (error) {
      push({ title: 'Unable to delete inspection', description: getErrorMessage(error), variant: 'error' })
    }
  }

  if (inspectionsQuery.isLoading) {
    return <LoadingState label="Loading inspections..." />
  }

  if (inspectionsQuery.isError) {
    return (
      <ErrorState
        message="Unable to load inspections"
        action={
          <button className="text-sm font-semibold text-brand-600" onClick={() => inspectionsQuery.refetch()}>
            Try again
          </button>
        }
      />
    )
  }

  return (
    <Card
      title="Inspections"
      subtitle="Search and filter every inspection in one place."
      actions={
        canCreateInspection ? (
          <Button onClick={() => navigate('/inspections/new')}>New inspection</Button>
        ) : undefined
      }
    >
      <div className="space-y-4">
        <div className="flex flex-col gap-3 border-b border-slate-100 pb-4 md:flex-row md:flex-wrap">
          <Input
            value={searchTerm}
            onChange={(event) => {
              setSearchTerm(event.target.value)
              setPage(1)
            }}
            placeholder="Search by template, location, creator, or ID"
            className="md:flex-1"
          />
          <Input
            value={locationFilter}
            onChange={(event) => {
              setLocationFilter(event.target.value)
              setPage(1)
            }}
            placeholder="Filter by location/department"
            className="md:w-64"
          />
          <Select
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value as StatusFilter)
              setPage(1)
            }}
            className="md:w-44"
          >
            <option value="all">All statuses</option>
            {INSPECTION_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </Select>
          <Select
            value={templateFilter}
            onChange={(event) => {
              setTemplateFilter(event.target.value as 'all' | string)
              setPage(1)
            }}
            className="md:w-56"
          >
            <option value="all">All templates</option>
            {templatesQuery.data?.map((template) => (
              <option key={template.id} value={template.id}>
                {template.name}
              </option>
            ))}
          </Select>
          <Select
            value={originFilter}
            onChange={(event) => {
              setOriginFilter(event.target.value as OriginFilter)
              setPage(1)
            }}
            className="md:w-48"
          >
            <option value="all">All origins</option>
            <option value="assignment">Assignment</option>
            <option value="independent">Independent</option>
          </Select>
        </div>

        <div className="flex flex-col justify-between gap-3 text-xs uppercase tracking-wide text-slate-500 sm:flex-row sm:items-center">
          <p>
            Showing {showingStart}-{showingEnd} of {totalCount} inspections
          </p>
          <div className="flex gap-2">
            <Button variant="secondary" disabled={page <= 1} onClick={() => setPage((prev) => Math.max(1, prev - 1))}>
              Previous
            </Button>
            <Button
              variant="secondary"
              disabled={page >= totalPages || totalCount === 0}
              onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
            >
              Next
            </Button>
          </div>
        </div>

        {inspections.length === 0 ? (
          <EmptyState title="No inspections match" description="Try a different search or reset the filters." />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="px-4 py-2">Inspection</th>
                  <th className="px-4 py-2">Template</th>
                  <th className="px-4 py-2">Created by</th>
                  <th className="px-4 py-2">Status</th>
                  <th className="px-4 py-2">Location</th>
                  <th className="px-4 py-2">Started</th>
                  <th className="px-4 py-2">Score</th>
                  <th className="px-4 py-2 text-right">Options</th>
                </tr>
              </thead>
              <tbody>
                {inspections.map((inspection) => {
                  const templateName = templateNameMap.get(inspection.template_id)
                  const inspectionLabel = formatInspectionName(templateName || 'Inspection', inspection.started_at, inspection.id)
                  return (
                    <tr key={inspection.id} className="border-t border-slate-100">
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-900">{inspectionLabel}</div>
                        <p className="text-xs text-slate-500">ID #{inspection.id}</p>
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        <div>{templateName || '—'}</div>
                        <p className="text-xs text-slate-500">
                          {inspection.inspection_origin === 'assignment' ? 'Assignment' : 'Independent'}
                        </p>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{inspection.created_by?.full_name ?? 'Unknown'}</td>
                      <td className="px-4 py-3 capitalize text-slate-600">{inspection.status}</td>
                      <td className="px-4 py-3 text-slate-600">{inspection.location || 'Unassigned'}</td>
                      <td className="px-4 py-3 text-slate-600">{formatDate(inspection.started_at?.toString())}</td>
                      <td className="px-4 py-3 text-slate-900">{formatScore(inspection.overall_score)}</td>
                      <td className="px-4 py-3">
                        <div className="flex flex-wrap justify-end gap-3 text-sm font-semibold">
                          <Link
                            className="text-indigo-600 hover:underline"
                            to={`/actions/search?inspectionId=${inspection.id}`}
                          >
                            Issues
                          </Link>
                          <Link className="text-brand-600 hover:underline" to={`/inspections/${inspection.id}`}>
                            View
                          </Link>
                          {canEditInspections && inspection.status === 'draft' && (
                            <>
                              <Link
                                className="text-slate-600 hover:text-brand-600"
                                to={`/inspections/${inspection.id}/edit`}
                              >
                                Edit
                              </Link>
                              <button
                                type="button"
                                className="text-red-600 hover:underline disabled:opacity-60"
                                disabled={deleteMutation.isPending}
                                onClick={() => handleDelete(inspection.id)}
                              >
                                Delete
                              </button>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Card>
  )
}
