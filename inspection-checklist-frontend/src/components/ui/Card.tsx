import type { ReactNode } from 'react'

import { clsx } from 'clsx'

type CardProps = {
  title?: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  className?: string
  children: ReactNode
}

export const Card = ({ title, subtitle, actions, className, children }: CardProps) => {
  return (
    <section className={clsx('rounded-xl border border-slate-200 bg-white p-5 shadow-sm', className)}>
      {(title || actions) && (
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            {typeof title === 'string' ? <h2 className="text-lg font-semibold text-slate-900">{title}</h2> : title}
            {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div>{children}</div>
    </section>
  )
}
