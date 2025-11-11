import type { ReactNode } from 'react'

export const ErrorState = ({ message, action }: { message: string; action?: ReactNode }) => {
  return (
    <div className="rounded-2xl border border-red-200 bg-red-50 p-6 text-center text-red-700">
      <p className="font-semibold">{message}</p>
      {action && <div className="mt-3 flex justify-center">{action}</div>}
    </div>
  )
}
