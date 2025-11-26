import { api } from '@/api/client'

const extractFileName = (disposition?: string | null, fallback?: string) => {
  if (disposition) {
    const match = /filename\*?=(?:UTF-8'')?"?([^";]+)/i.exec(disposition)
    if (match?.[1]) {
      return decodeURIComponent(match[1])
    }
  }
  if (fallback) {
    return fallback
  }
  return 'attachment'
}

export const downloadFileWithAuth = async (path: string, fallbackName?: string) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const response = await api.get<ArrayBuffer>(normalizedPath, { responseType: 'arraybuffer' })
  const filename = extractFileName(response.headers['content-disposition'], fallbackName)
  const blob = new Blob([response.data])
  const link = document.createElement('a')
  const url = window.URL.createObjectURL(blob)
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
