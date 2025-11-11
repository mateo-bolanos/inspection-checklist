import type { ReactNode } from 'react'

import { clsx } from 'clsx'

const variants = {
  neutral: 'bg-slate-100 text-slate-700 ring-slate-200',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-200',
  warning: 'bg-amber-50 text-amber-700 ring-amber-200',
  danger: 'bg-red-50 text-red-700 ring-red-200',
  info: 'bg-brand-50 text-brand-700 ring-brand-200',
}

type BadgeProps = {
  variant?: keyof typeof variants
  children: ReactNode
  className?: string
}

export const Badge = ({ variant = 'neutral', children, className }: BadgeProps) => (
  <span
    className={clsx(
      'inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ring-inset',
      variants[variant],
      className,
    )}
  >
    {children}
  </span>
)
