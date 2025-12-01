import type { NameType, Payload, ValueType } from 'recharts/types/component/DefaultTooltipContent'
import type { TooltipContentProps } from 'recharts'

type ChartTooltipProps = Partial<TooltipContentProps<ValueType, NameType>> & {
  valueFormatter?: (value: ValueType) => string
  unit?: string
}

export const ChartTooltip = ({ active, payload, label, labelFormatter, valueFormatter, unit }: ChartTooltipProps) => {
  const items = (payload ?? []) as Payload<ValueType, NameType>[]

  if (!active || items.length === 0) {
    return null
  }

  const formattedLabel = labelFormatter ? labelFormatter(label, items) : String(label)

  return (
    <div className="rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-lg">
      <p className="text-xs font-semibold text-slate-500">{formattedLabel}</p>
      {items.map((entry: Payload<ValueType, NameType>) => {
        const key = entry.dataKey?.toString() ?? entry.name
        const color = entry.color ?? '#2563eb'
        const rawValue = entry.value ?? 0
        const value = valueFormatter ? valueFormatter(rawValue) : rawValue
        return (
          <div key={key} className="mt-1 flex items-center gap-2 text-sm text-slate-700">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
            <span className="font-semibold text-slate-900">
              {value}
              {unit ? ` ${unit}` : ''}
            </span>
            {entry.name && <span className="text-slate-500">{entry.name}</span>}
          </div>
        )
      })}
    </div>
  )
}
