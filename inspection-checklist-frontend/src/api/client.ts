import axios, { type AxiosError } from 'axios'

import { authStore } from '@/auth/auth.store'

const baseURL = import.meta.env.VITE_API_BASE_URL

if (!baseURL) {
  // eslint-disable-next-line no-console
  console.warn('VITE_API_BASE_URL is not set. API calls will fail until configured.')
}

export const api = axios.create({
  baseURL: baseURL ?? 'http://localhost:8000',
})

type ErrorResponse = {
  detail?: string | { msg?: string } | string[]
}

api.interceptors.request.use((config) => {
  const token = authStore.getState().token
  if (token) {
    config.headers = config.headers ?? {}
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ErrorResponse>) => {
    if (!error.response) {
      error.message =
        'Network error. If this is a CORS issue, allow http://localhost:5173 in the FastAPI settings.'
    }
    if (error.response?.status === 401) {
      authStore.clear()
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export const getErrorMessage = (error: unknown) => {
  if (axios.isAxiosError<ErrorResponse>(error)) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) {
      return detail.join(', ')
    }
    if (typeof detail === 'object' && detail?.msg) {
      return detail.msg
    }
    if (typeof detail === 'string') {
      return detail
    }
    return error.message
  }
  if (error instanceof Error) {
    return error.message
  }
  return 'Unexpected error'
}
