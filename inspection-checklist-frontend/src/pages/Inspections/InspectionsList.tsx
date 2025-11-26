import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { useInspectionsQuery, useTemplatesQuery } from '@/api/hooks'
import { useAuth } from '@/auth/useAuth'
import { EmptyState } from '@/components/feedback/EmptyState'
import { ErrorState } from '@/components/feedback/ErrorState'
import { LoadingState } from '@/components/feedback/LoadingState'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Input } from '@/components/ui/Input'
import { Select } from '@/components/ui/Select'
import { INSPECTION_STATUSES } from '@/lib/constants'
import { formatDate, formatInspectionName, formatScore } from '@/lib/formatters'

type StatusFilter = 'all' | (typeof INSPECTION_STATUSES)[number]

export const InspectionsListPage = () => {
  const navigate = useNavigate()
  const { hasRole } = useAuth()
  const inspectionsQuery = useInspectionsQuery()
  const templatesQuery = useTemplatesQuery()
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')

  const templateNameMap = useMemo(() => {
    const map = new Map<string, string>()
    templatesQuery.data?.forEach((template) => {
      map.set(template.id, template.name)
    })
    return map
  }, [templatesQuery.data])

  const filteredInspections = useMemo(() => {
    if (!inspectionsQuery.data) return []
    const normalizedSearch = searchTerm.trim().toLowerCase()
    return inspectionsQuery.data.filter((inspection) => {
      const templateName = templateNameMap.get(inspection.template_id) ?? ''
      const inspectionLabel = formatInspectionName(templateName || 'Inspection', inspection.started_at, inspection.id)
      const searchTarget = [
        inspectionLabel,
        templateName,
        inspection.location ?? '',
        inspection.status,
        inspection.id,
        inspection.created_by?.full_name ?? '',
        inspection.created_by?.email ?? '',
        inspection.inspection_origin ?? '',
      ]
        .join(' ')
        .toLowerCase()
      const matchesSearch = normalizedSearch === '' || searchTarget.includes(normalizedSearch)
      const matchesStatus = statusFilter === 'all' || inspection.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [inspectionsQuery.data, templateNameMap, searchTerm, statusFilter])

  const canCreateInspection = hasRole(['admin', 'inspector'])
  const canEditInspections = canCreateInspection

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

  const totalCount = inspectionsQuery.data?.length ?? 0

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
        <div className="flex flex-col gap-3 border-b border-slate-100 pb-4 md:flex-row">
          <Input
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search by type, template, status, location, or ID"
            className="md:flex-1"
          />
          <Select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)} className="md:w-48">
            <option value="all">All statuses</option>
            {INSPECTION_STATUSES.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </Select>
        </div>

        <p className="text-xs uppercase tracking-wide text-slate-500">
          Showing {filteredInspections.length} of {totalCount} inspections
        </p>

        {filteredInspections.length === 0 ? (
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
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredInspections.map((inspection) => {
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
                            Actions
                          </Link>
                          <Link className="text-brand-600 hover:underline" to={`/inspections/${inspection.id}`}>
                            View
                          </Link>
                          {canEditInspections && inspection.status === 'draft' && (
                            <Link className="text-slate-600 hover:text-brand-600" to={`/inspections/${inspection.id}/edit`}>
                              Edit
                            </Link>
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
