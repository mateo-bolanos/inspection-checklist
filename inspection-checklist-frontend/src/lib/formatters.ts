import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'

dayjs.extend(relativeTime)

export const formatDate = (value?: string | null) => {
  if (!value) return '—'
  return dayjs(value).format('MMM D, YYYY')
}

export const formatDateTime = (value?: string | null) => {
  if (!value) return '—'
  return dayjs(value).format('MMM D, YYYY • h:mm A')
}

export const formatRelative = (value?: string | null) => {
  if (!value) return '—'
  return dayjs(value).fromNow()
}

export const formatScore = (value?: number | null, digits = 1) => {
  if (value === undefined || value === null) return '—'
  return `${value.toFixed(digits)}%`
}

export const formatInspectionName = (
  templateName?: string | null,
  startedAt?: string | null,
  fallback?: string | number,
) => {
  const trimmedName = templateName?.trim()
  const formattedDate = startedAt ? dayjs(startedAt).format('DD/MM/YY HH:mm') : null

  if (trimmedName && formattedDate) {
    return `${trimmedName} ${formattedDate}`
  }
  if (trimmedName) return trimmedName
  if (formattedDate) return formattedDate
  if (fallback !== undefined && fallback !== null) {
    return String(fallback)
  }
  return ''
}

export const capitalize = (value?: string | null) => {
  if (!value) return ''
  return value.charAt(0).toUpperCase() + value.slice(1)
}
