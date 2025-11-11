const rawApiBaseUrl = import.meta.env.VITE_API_BASE_URL

if (!rawApiBaseUrl) {
  console.warn('VITE_API_BASE_URL is not set. Falling back to http://localhost:8000.')
}

export const API_BASE_URL = (rawApiBaseUrl ?? 'http://localhost:8000').replace(/\/+$/, '')

const ABSOLUTE_URL_PATTERN = /^https?:\/\//i

export const resolveApiUrl = (path?: string | null): string => {
  if (!path) {
    return ''
  }
  if (ABSOLUTE_URL_PATTERN.test(path)) {
    return path
  }
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}
