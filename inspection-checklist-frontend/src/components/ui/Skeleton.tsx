import { clsx } from 'clsx'
import type { HTMLAttributes } from 'react'

export const Skeleton = ({ className, ...props }: HTMLAttributes<HTMLDivElement>) => {
  return (
    <div
      className={clsx('animate-pulse rounded-md bg-slate-200/80', className)}
      {...props}
    />
  )
}
