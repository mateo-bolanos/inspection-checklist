import type { ReactNode } from 'react'

import { clsx } from 'clsx'

export type FormFieldProps = {
  label: string
  htmlFor?: string
  description?: ReactNode
  error?: ReactNode
  required?: boolean
  children: ReactNode
  className?: string
}

export const FormField = ({ label, htmlFor, description, error, required, children, className }: FormFieldProps) => {
  return (
    <label className={clsx('flex w-full flex-col gap-2 text-sm text-slate-600', className)} htmlFor={htmlFor}>
      <span className="flex items-center gap-1 text-sm font-medium text-slate-900">
        {label}
        {required && <span className="text-red-500">*</span>}
      </span>
      {description && <span className="text-xs text-slate-500">{description}</span>}
      {children}
      {error && <span className="text-xs text-red-600">{error}</span>}
    </label>
  )
}
