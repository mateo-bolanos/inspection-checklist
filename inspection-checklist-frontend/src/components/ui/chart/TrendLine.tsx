import { Area, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { ChartEmpty } from './ChartEmpty'
import { ChartTooltip } from './ChartTooltip'

type TrendLineProps = {
  data: { [key: string]: any }[]
  xKey: string
  yKey: string
  name?: string
  color?: string
  height?: number
  fill?: string
}

const numberFormatter = new Intl.NumberFormat()

export const TrendLine = ({
  data,
  xKey,
  yKey,
  name = 'Value',
  color = '#2563eb',
  height = 190,
  fill = 'rgba(37, 99, 235, 0.12)',
}: TrendLineProps) => {
  const normalized = data.map((item) => ({
    ...item,
    [yKey]: Number.isFinite(Number(item[yKey])) ? Number(item[yKey]) : 0,
  }))

  const hasPoints = normalized.some((item) => item[yKey] > 0)

  if (normalized.length === 0 || !hasPoints) {
    return <ChartEmpty height={height} message="No fails recorded for this range." />
  }

  return (
    <div style={{ height }}>
      <ResponsiveContainer>
        <LineChart data={normalized} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
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
            content={({ active, payload, label }) => {
              const firstEntry = payload && payload.length > 0 ? [payload[0]] : []
              return (
                <ChartTooltip
                  active={Boolean(active)}
                  payload={firstEntry}
                  label={label}
                  valueFormatter={(value) => numberFormatter.format(Number(value))}
                  labelFormatter={(lb) => String(lb)}
                />
              )
            }}
            cursor={{ stroke: color, strokeOpacity: 0.1, strokeWidth: 32 }}
          />
          <defs>
            <linearGradient id="lineFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={fill} stopOpacity={1} />
              <stop offset="100%" stopColor={fill} stopOpacity={0} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey={yKey}
            stroke="transparent"
            fill="url(#lineFill)"
            isAnimationActive={false}
            name={name}
          />
          <Line
            type="monotone"
            dataKey={yKey}
            name={name}
            stroke={color}
            strokeWidth={3}
            dot={{ r: 3, stroke: 'white', strokeWidth: 1.5 }}
            activeDot={{ r: 5 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
