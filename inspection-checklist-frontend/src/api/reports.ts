import { api } from './client'

export type InspectionReportFilters = {
  start: string
  end: string
  templateId?: string
  assigneeId?: string
  locationId?: string | number
  location?: string
}

const extractFilename = (contentDisposition: string | undefined, fallback: string) => {
  if (!contentDisposition) {
    return fallback
  }
  const match = /filename="?([^";]+)"?/i.exec(contentDisposition)
  if (match?.[1]) {
    return match[1]
  }
  return fallback
}

export const downloadInspectionReport = async (filters: InspectionReportFilters) => {
  const params = {
    start: filters.start,
    end: filters.end,
    type: filters.templateId || undefined,
    assigneeId: filters.assigneeId || undefined,
    locationId: filters.locationId !== undefined && filters.locationId !== null ? String(filters.locationId) : undefined,
    location: filters.location || undefined,
  }
  const response = await api.get<ArrayBuffer>('/reports/inspections.pdf', {
    params,
    responseType: 'blob',
  })
  const blob = new Blob([response.data], { type: 'application/pdf' })
  const filename = extractFilename(
    // Axios lowercases response headers access
    response.headers['content-disposition'],
    `inspections-${filters.start}_${filters.end}.pdf`,
  )
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
