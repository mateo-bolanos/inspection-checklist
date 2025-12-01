import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { ChartEmpty } from './ChartEmpty'
import { ChartTooltip } from './ChartTooltip'

type TrendBarProps = {
  data: { [key: string]: any }[]
  xKey: string
  yKey: string
  name?: string
  color?: string
  height?: number
  unit?: string
}

const numberFormatter = new Intl.NumberFormat()

export const TrendBar = ({
  data,
  xKey,
  yKey,
  name = 'Value',
  color = '#2563eb',
  height = 190,
  unit,
}: TrendBarProps) => {
  const normalized = data.map((item) => ({
    ...item,
    [yKey]: Number.isFinite(Number(item[yKey])) ? Number(item[yKey]) : 0,
  }))

  const hasPoints = normalized.some((item) => item[yKey] > 0)

  if (normalized.length === 0 || !hasPoints) {
    return <ChartEmpty height={height} message="No inspections recorded for this range." />
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <BarChart data={normalized} margin={{ top: 10, right: 8, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" vertical={false} />
          <XAxis dataKey={xKey} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: '#475569' }} />
          <YAxis
            width={35}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 12, fill: '#475569' }}
            tickFormatter={(value) => numberFormatter.format(Number(value))}
          />
          <Tooltip
            cursor={{ fill: 'rgba(37, 99, 235, 0.06)' }}
            content={
              <ChartTooltip
                valueFormatter={(value) => numberFormatter.format(Number(value))}
                unit={unit}
                labelFormatter={(label) => String(label)}
              />
            }
          />
          <Bar dataKey={yKey} name={name} fill={color} radius={[10, 10, 6, 6]} maxBarSize={42} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
