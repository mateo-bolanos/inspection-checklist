import type { ReactNode } from 'react'

export const EmptyState = ({ title, description, action }: { title: string; description?: string; action?: ReactNode }) => {
  return (
    <div className="rounded-2xl border border-dashed border-slate-200 bg-slate-50 p-8 text-center">
      <p className="text-base font-semibold text-slate-900">{title}</p>
      {description && <p className="mt-2 text-sm text-slate-500">{description}</p>}
      {action && <div className="mt-4 flex justify-center">{action}</div>}
    </div>
  )
}
