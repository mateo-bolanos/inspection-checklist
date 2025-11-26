import { createContext, useContext } from 'react'

import type { ToastPayload } from './ToastProvider'

type ToastContextValue = {
  push: (toast: ToastPayload) => string
  dismiss: (id: string) => void
}

export const ToastContext = createContext<ToastContextValue | undefined>(undefined)

export const useToast = () => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

