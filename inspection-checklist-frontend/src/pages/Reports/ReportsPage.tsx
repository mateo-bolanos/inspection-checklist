import { useMemo, useState } from 'react'

import { useAssignmentsQuery, useLocationsQuery, useTemplatesQuery } from '@/api/hooks'
import { getErrorMessage } from '@/api/client'
import { downloadInspectionReport } from '@/api/reports'
import { Card } from '@/components/ui/Card'

const formatDateInput = (value: Date) => value.toISOString().slice(0, 10)
const subtractDays = (value: Date, days: number) => new Date(value.getTime() - days * 24 * 60 * 60 * 1000)

export const ReportsPage = () => {
  const templatesQuery = useTemplatesQuery()
  const assignmentsQuery = useAssignmentsQuery()
  const locationsQuery = useLocationsQuery()
  const locationOptions = useMemo(() => {
    if (!locationsQuery.data) {
      return []
    }
    return [...locationsQuery.data]
      .map((location) => ({
        id: String(location.id),
        name: location.name,
      }))
      .sort((a, b) => a.name.localeCompare(b.name))
  }, [locationsQuery.data])
  const assigneeOptions = useMemo(() => {
    if (!assignmentsQuery.data) {
      return []
    }
    const unique = new Map<string, { id: string; name: string; email?: string }>()
    assignmentsQuery.data.forEach((assignment) => {
      const assignee = assignment.assignee
      if (!assignee || unique.has(assignee.id)) {
        return
      }
      unique.set(assignee.id, {
        id: assignee.id,
        name: assignee.full_name || assignee.email || 'User',
        email: assignee.email ?? undefined,
      })
    })
    return [...unique.values()].sort((a, b) => a.name.localeCompare(b.name))
  }, [assignmentsQuery.data])

  const [reportStart, setReportStart] = useState(() => formatDateInput(subtractDays(new Date(), 30)))
  const [reportEnd, setReportEnd] = useState(() => formatDateInput(new Date()))
  const [reportTemplateId, setReportTemplateId] = useState('')
  const [reportAssigneeId, setReportAssigneeId] = useState('')
  const [reportLocationId, setReportLocationId] = useState('')
  const [reportLocationName, setReportLocationName] = useState('')
  const [isDownloadingReport, setIsDownloadingReport] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  const locationPlaceholder = locationsQuery.isLoading ? 'Loading locations…' : 'Any location'
  const assigneePlaceholder = assignmentsQuery.isLoading ? 'Loading team…' : 'Any assignee'
  const noAssigneeOptions = !assignmentsQuery.isLoading && assigneeOptions.length === 0

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Inspection reports</h1>
        <p className="mt-2 text-sm text-slate-600">
          Generate downloadable PDF summaries of submitted inspections across any date range.
        </p>
      </div>

      <Card title="Report generator" subtitle="Filter a PDF summary by date, template, assignee, or location.">
        <form
          className="space-y-4"
          onSubmit={async (event) => {
            event.preventDefault()
            setReportError(null)
            if (!reportStart || !reportEnd) {
              setReportError('Start and end dates are required.')
              return
            }
            if (new Date(reportStart) > new Date(reportEnd)) {
              setReportError('Start date must be on or before the end date.')
              return
            }
            setIsDownloadingReport(true)
            try {
              await downloadInspectionReport({
                start: reportStart,
                end: reportEnd,
                templateId: reportTemplateId || undefined,
                assigneeId: reportAssigneeId || undefined,
                locationId: reportLocationId || undefined,
                location: reportLocationName || undefined,
              })
            } catch (error) {
              setReportError(getErrorMessage(error))
            } finally {
              setIsDownloadingReport(false)
            }
          }}
        >
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <label className="space-y-1 text-sm font-medium text-slate-700">
              <span>Date start</span>
              <input
                type="date"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                value={reportStart}
                max={reportEnd || undefined}
                onChange={(event) => setReportStart(event.target.value)}
                required
              />
            </label>
            <label className="space-y-1 text-sm font-medium text-slate-700">
              <span>Date end</span>
              <input
                type="date"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                value={reportEnd}
                min={reportStart || undefined}
                onChange={(event) => setReportEnd(event.target.value)}
                required
              />
            </label>
            <label className="space-y-1 text-sm font-medium text-slate-700">
              <span>Template</span>
              <select
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                value={reportTemplateId}
                onChange={(event) => setReportTemplateId(event.target.value)}
                disabled={templatesQuery.isLoading}
              >
                <option value="">Any template</option>
                {templatesQuery.data?.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-1 text-sm font-medium text-slate-700">
              <span>Location</span>
              <select
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                value={reportLocationId}
                onChange={(event) => setReportLocationId(event.target.value)}
                disabled={locationsQuery.isLoading}
              >
                <option value="">{locationPlaceholder}</option>
                {locationOptions.map((location) => (
                  <option key={location.id} value={location.id}>
                    {location.name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-500">
                Select from saved locations. Leave blank to include every location.
              </p>
            </label>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <label className="space-y-1 text-sm font-medium text-slate-700">
              <span>Custom location match</span>
              <input
                type="text"
                placeholder="Matches legacy location text"
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                value={reportLocationName}
                onChange={(event) => setReportLocationName(event.target.value)}
              />
              <p className="text-xs text-slate-500">Optional fallback for inspections that predate the new locations list.</p>
            </label>
            <label className="space-y-1 text-sm font-medium text-slate-700">
              <span>Assignee</span>
              <select
                className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm shadow-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
                value={reportAssigneeId}
                onChange={(event) => setReportAssigneeId(event.target.value)}
                disabled={assignmentsQuery.isLoading}
              >
                <option value="">{assigneePlaceholder}</option>
                {assigneeOptions.map((assignee) => (
                  <option key={assignee.id} value={assignee.id}>
                    {assignee.name}
                  </option>
                ))}
              </select>
              {noAssigneeOptions && (
                <p className="text-xs text-slate-500">Assignments will appear here once you add the first schedule.</p>
              )}
            </label>
          </div>
          {reportError && <p className="text-sm text-red-600">{reportError}</p>}
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={isDownloadingReport}
              className="rounded-md bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-brand-300"
            >
              {isDownloadingReport ? 'Preparing PDF…' : 'Download PDF'}
            </button>
            <p className="text-xs text-slate-500">Runs against submitted inspections in the selected range.</p>
          </div>
        </form>
      </Card>
    </div>
  )
}

