import type { ReactNode } from 'react'
import { clsx } from 'clsx'

type ChartContainerProps = {
  children: ReactNode
  className?: string
  header?: ReactNode
  tone?: 'brand' | 'emerald' | 'slate'
  padding?: 'normal' | 'compact'
}

const toneBackground: Record<NonNullable<ChartContainerProps['tone']>, string> = {
  brand: 'from-brand-50/70 via-white to-white',
  emerald: 'from-emerald-50/70 via-white to-white',
  slate: 'from-slate-50/80 via-white to-white',
}

export const ChartContainer = ({
  children,
  className,
  header,
  tone = 'slate',
  padding = 'normal',
}: ChartContainerProps) => {
  return (
    <div
      className={clsx(
        'relative overflow-hidden rounded-xl border border-slate-100 bg-white',
        padding === 'compact' ? 'p-3' : 'p-4',
        className,
      )}
    >
      <div
        className={clsx(
          'pointer-events-none absolute inset-0 opacity-80',
          'bg-gradient-to-b',
          toneBackground[tone],
        )}
        aria-hidden="true"
      />
      <div className="absolute inset-x-0 -top-16 h-24 bg-[radial-gradient(240px_circle_at_50%_50%,rgba(59,130,246,0.08),transparent)]" />
      <div className="relative">
        {header && <div className="mb-2 flex items-center justify-between">{header}</div>}
        {children}
      </div>
    </div>
  )
}
