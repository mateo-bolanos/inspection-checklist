import { useState } from 'react'

import { useDashboardItemsQuery } from '@/api/hooks'
import { ErrorState } from '@/components/feedback/ErrorState'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { formatScore } from '@/lib/formatters'

export const DashboardItemsPage = () => {
  const [limit, setLimit] = useState(10)
  const { data, isLoading, isError, refetch } = useDashboardItemsQuery(limit)

  if (isLoading) {
    return <Skeleton className="h-40 w-full" />
  }

  if (isError || !data) {
    return (
      <ErrorState
        message="Unable to load item performance"
        action={
          <Button variant="ghost" onClick={() => refetch()}>
            Retry
          </Button>
        }
      />
    )
  }

  return (
    <Card
      title="Failing template items"
      subtitle="Sorted by failure rate"
      actions={
        <select
          className="rounded-md border border-slate-200 px-3 py-1 text-sm"
          value={limit}
          onChange={(event) => setLimit(Number(event.target.value))}
        >
          {[5, 10, 20].map((value) => (
            <option key={value} value={value}>
              Top {value}
            </option>
          ))}
        </select>
      }
    >
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="px-4 py-2">Prompt</th>
              <th className="px-4 py-2">Fail rate</th>
            </tr>
          </thead>
          <tbody>
            {data.failures.map((item) => (
              <tr key={item.item_id} className="border-t border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-900">{item.prompt}</td>
                <td className="px-4 py-3 text-slate-700">{formatScore(item.fail_rate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
