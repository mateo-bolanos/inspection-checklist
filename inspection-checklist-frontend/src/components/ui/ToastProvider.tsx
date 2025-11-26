import { useCallback, useMemo, useState } from 'react'
import type { PropsWithChildren, ReactNode } from 'react'

import { clsx } from 'clsx'

import { ToastContext } from './toastContext'

export type ToastVariant = 'default' | 'success' | 'error' | 'warning'

export type ToastPayload = {
  id?: string
  title: string
  description?: ReactNode
  variant?: ToastVariant
  duration?: number
}

type ToastEntry = ToastPayload & { id: string }

const variantClasses: Record<ToastVariant, string> = {
  default: 'bg-white text-slate-900 border-slate-200',
  success: 'bg-emerald-50 text-emerald-900 border-emerald-200',
  error: 'bg-red-50 text-red-900 border-red-200',
  warning: 'bg-amber-50 text-amber-900 border-amber-200',
}

export const ToastProvider = ({ children }: PropsWithChildren) => {
  const [toasts, setToasts] = useState<ToastEntry[]>([])

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
  }, [])

  const push = useCallback(
    (toast: ToastPayload) => {
      const id =
        toast.id ?? (typeof crypto !== 'undefined' && 'randomUUID' in crypto ? crypto.randomUUID() : Math.random().toString(36).slice(2))
      const entry: ToastEntry = {
        ...toast,
        id,
        variant: toast.variant ?? 'default',
      }
      setToasts((prev) => [...prev, entry])
      const duration = toast.duration ?? 5000
      window.setTimeout(() => dismiss(id), duration)
      return id
    },
    [dismiss],
  )

  const value = useMemo(() => ({ push, dismiss }), [push, dismiss])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed right-4 top-4 z-50 flex w-80 flex-col gap-3">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={clsx(
              'pointer-events-auto rounded-xl border px-4 py-3 shadow-lg ring-1 ring-black/5',
              variantClasses[toast.variant ?? 'default'],
            )}
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold">{toast.title}</p>
                {toast.description && <p className="text-sm text-slate-600">{toast.description}</p>}
              </div>
              <button className="text-sm text-slate-500 hover:text-slate-900" onClick={() => dismiss(toast.id)} type="button">
                ×
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

