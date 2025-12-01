import { useMemo, useState } from 'react'
import dayjs from 'dayjs'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock3,
  Flame,
  MapPin,
  Sparkles,
  Target,
  Users,
} from 'lucide-react'

import { useDashboardPrioritiesQuery, useTemplatesQuery, useLocationsQuery, useUsersQuery } from '@/api/hooks'
import { ErrorState } from '@/components/feedback/ErrorState'
import { Card } from '@/components/ui/Card'
import { Skeleton } from '@/components/ui/Skeleton'
import { Badge } from '@/components/ui/Badge'
import { ChartContainer, TrendBar, TrendLine } from '@/components/ui/chart'
import { Select } from '@/components/ui/Select'
import { Input } from '@/components/ui/Input'

type CalendarCell = {
  date: string
  fail_count: number
  inspection_count: number
}

const ProgressBar = ({ value, tone = 'emerald' }: { value: number; tone?: 'emerald' | 'brand' }) => {
  const colors = tone === 'emerald' ? 'bg-emerald-500' : 'bg-brand-500'
  return (
    <div className="h-2 w-full rounded-full bg-slate-100">
      <div className={`h-2 rounded-full ${colors}`} style={{ width: `${Math.min(value, 100)}%` }} />
    </div>
  )
}

const GradientBar = ({ fail, pass }: { fail: number; pass: number }) => {
  const total = Math.max(fail + pass, 1)
  const failPct = Math.round((fail / total) * 100)
  const passPct = 100 - failPct
  return (
    <div className="flex h-2 w-full overflow-hidden rounded-full bg-slate-100">
      <div className="h-full bg-red-500" style={{ width: `${failPct}%` }} />
      <div className="h-full bg-emerald-500" style={{ width: `${passPct}%` }} />
    </div>
  )
}

const CalendarHeatmap = ({ cells }: { cells: CalendarCell[] }) => {
  const latestDate = useMemo(() => {
    if (cells.length === 0) return dayjs()
    return cells.reduce((max, curr) => (dayjs(curr.date).isAfter(max) ? dayjs(curr.date) : max), dayjs(cells[0].date))
  }, [cells])

  const monthStart = latestDate.startOf('month')
  const monthEnd = latestDate.endOf('month')
  const startOffset = monthStart.day() // 0=Sun
  const gridStart = monthStart.subtract(startOffset, 'day')
  const gridEnd = monthEnd.add(6 - monthEnd.day(), 'day')
  const cellMap = useMemo(
    () =>
      new Map(
        cells.map((cell) => [
          dayjs(cell.date).format('YYYY-MM-DD'),
          { fail: cell.fail_count, inspections: cell.inspection_count },
        ]),
      ),
    [cells],
  )
  const days: { key: string; label: string; fail: number; inMonth: boolean }[] = []
  for (let cursor = gridStart; cursor.isBefore(gridEnd) || cursor.isSame(gridEnd, 'day'); cursor = cursor.add(1, 'day')) {
    const key = cursor.format('YYYY-MM-DD')
    const entry = cellMap.get(key)
    days.push({
      key,
      label: cursor.date().toString(),
      fail: entry?.fail ?? 0,
      inMonth: cursor.isSame(monthStart, 'month'),
    })
  }
  const maxFail = Math.max(...days.map((d) => d.fail), 1)

  return (
    <div className="space-y-2">
      <div className="grid grid-cols-7 text-center text-[10px] font-semibold uppercase tracking-wide text-slate-500">
        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((d) => (
          <span key={d}>{d}</span>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1 rounded-xl border border-slate-100 bg-white p-2">
        {days.map((day) => {
          const intensity = day.fail / maxFail
          const bgOpacity = day.fail === 0 ? 0.08 : 0.2 + intensity * 0.65
          return (
            <div
              key={day.key}
              className={`flex h-12 flex-col items-center justify-center rounded-md text-[11px] font-semibold ${
                day.inMonth ? 'text-slate-700' : 'text-slate-300'
              }`}
              style={{ backgroundColor: `rgba(16, 121, 255, ${bgOpacity})` }}
              title={`${day.key}: ${day.fail} fails`}
            >
              <span>{day.label}</span>
              <span className="text-[10px] text-slate-600">{day.fail}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

const dateToStr = (value: dayjs.Dayjs | null) => (value ? value.format('YYYY-MM-DD') : undefined)

const FilterBar = ({
  preset,
  onPresetChange,
  startDate,
  endDate,
  onDateChange,
  templateId,
  onTemplateChange,
  location,
  onLocationChange,
  itemQuery,
  onItemQueryChange,
  inspectorId,
  onInspectorChange,
  templates,
  locations,
  inspectors,
  onReset,
}: {
  preset: string
  onPresetChange: (value: string) => void
  startDate: string | undefined
  endDate: string | undefined
  onDateChange: (start?: string, end?: string) => void
  templateId: string
  onTemplateChange: (value: string) => void
  location: string
  onLocationChange: (value: string) => void
  itemQuery: string
  onItemQueryChange: (value: string) => void
  inspectorId: string
  onInspectorChange: (value: string) => void
  templates: { id: string; name: string }[]
  locations: { id: number; name: string }[]
  inspectors: { id: string; name: string }[]
  onReset: () => void
}) => {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 shadow-sm md:flex-row md:items-end md:justify-between">
      <div className="flex flex-wrap gap-3">
        <div className="flex items-center gap-2">
          {['30', '60', '90', 'custom'].map((option) => (
            <button
              key={option}
              onClick={() => onPresetChange(option)}
              className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${
                preset === option
                  ? 'bg-brand-50 text-brand-700 ring-brand-200'
                  : 'bg-slate-50 text-slate-600 ring-slate-200'
              }`}
              type="button"
            >
              {option === '30' && '30 days'}
              {option === '60' && '60 days'}
              {option === '90' && '90 days'}
              {option === 'custom' && 'Custom'}
            </button>
          ))}
        </div>
        {preset === 'custom' && (
          <div className="flex items-center gap-2 text-xs">
            <Input
              type="date"
              value={startDate || ''}
              onChange={(e) => onDateChange(e.target.value || undefined, endDate)}
              className="h-9"
            />
            <span className="text-slate-500">to</span>
            <Input
              type="date"
              value={endDate || ''}
              onChange={(e) => onDateChange(startDate, e.target.value || undefined)}
              className="h-9"
            />
          </div>
        )}
      </div>
      <div className="flex flex-col gap-3 md:flex-row md:flex-nowrap md:items-center">
        <Select
          value={templateId}
          onChange={(e) => onTemplateChange(e.target.value)}
          className="h-9 w-full text-sm md:w-56"
        >
          <option value="">All templates</option>
          {templates.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </Select>
        <Select
          value={location}
          onChange={(e) => onLocationChange(e.target.value)}
          className="h-9 w-full text-sm md:w-56"
        >
          <option value="">All locations</option>
          {locations.map((loc) => (
            <option key={loc.id} value={loc.name}>
              {loc.name}
            </option>
          ))}
        </Select>
        <Select
          value={inspectorId}
          onChange={(e) => onInspectorChange(e.target.value)}
          className="h-9 w-full text-sm md:w-52"
        >
          <option value="">All inspectors</option>
          {inspectors.map((inspector) => (
            <option key={inspector.id} value={inspector.id}>
              {inspector.name}
            </option>
          ))}
        </Select>
        <Input
          placeholder="Checklist item contains..."
          value={itemQuery}
          onChange={(e) => onItemQueryChange(e.target.value)}
          className="h-9 text-sm"
        />
        <button
          type="button"
          onClick={onReset}
          className="rounded-md bg-slate-100 px-3 py-2 text-xs font-semibold text-slate-700 ring-1 ring-slate-200 hover:bg-slate-200"
        >
          Reset
        </button>
      </div>
    </div>
  )
}

export const DashboardPrioritiesPage = () => {
  const [preset, setPreset] = useState<'30' | '60' | '90' | 'custom'>('90')
  const [customStart, setCustomStart] = useState<string | undefined>(undefined)
  const [customEnd, setCustomEnd] = useState<string | undefined>(undefined)
  const [templateId, setTemplateId] = useState('')
  const [location, setLocation] = useState('')
  const [inspectorId, setInspectorId] = useState('')
  const [itemQuery, setItemQuery] = useState('')
  const [calendarMonth, setCalendarMonth] = useState(dayjs().format('YYYY-MM'))

  const computeDates = () => {
    const today = dayjs()
    if (preset === '30') {
      return { start: dateToStr(today.subtract(29, 'day')), end: dateToStr(today) }
    }
    if (preset === '60') {
      return { start: dateToStr(today.subtract(59, 'day')), end: dateToStr(today) }
    }
    if (preset === '90') {
      return { start: dateToStr(today.subtract(89, 'day')), end: dateToStr(today) }
    }
    return { start: customStart, end: customEnd }
  }

  const filters = useMemo(() => {
    const { start, end } = computeDates()
    return {
      start,
      end,
      template_id: templateId || undefined,
      location: location || undefined,
      locations: undefined,
      inspector_id: inspectorId || undefined,
      item: itemQuery || undefined,
      calendar_month: calendarMonth,
    }
  }, [preset, customStart, customEnd, templateId, location, inspectorId, itemQuery, calendarMonth])

  const { data, isLoading, isError, refetch } = useDashboardPrioritiesQuery(filters)
  const templatesQuery = useTemplatesQuery()
  const locationsQuery = useLocationsQuery()
  const inspectorsQuery = useUsersQuery('inspector')

  const calendarHeatmap = data?.calendar_heatmap ?? []
  const monthlyTrend = data?.monthly_fail_trend ?? []
  const cadenceApi = data?.cadence ?? []

  const templates = (templatesQuery.data ?? []).map((t) => ({ id: t.id, name: t.name }))
  const locations = (locationsQuery.data ?? []).map((l) => ({ id: l.id, name: l.name }))
  const inspectors = (inspectorsQuery.data ?? []).map((u) => ({
    id: u.id,
    name: (u.full_name || '').trim() || u.email || 'Inspector',
  }))

  const aggregatedByMonth = useMemo(
    () =>
      calendarHeatmap.reduce((acc, cell) => {
        const month = dayjs(cell.date).format('YYYY-MM')
        const entry = acc.get(month) ?? { fails: 0, inspections: 0 }
        entry.fails += cell.fail_count
        entry.inspections += cell.inspection_count
        acc.set(month, entry)
        return acc
      }, new Map<string, { fails: number; inspections: number }>()),
    [calendarHeatmap],
  )

  const rangeDays = useMemo(() => {
    if (filters.start && filters.end) {
      return dayjs(filters.end).diff(dayjs(filters.start), 'day') + 1
    }
    const dates = calendarHeatmap.map((c) => c.date).sort()
    if (dates.length >= 2) {
      return dayjs(dates[dates.length - 1]).diff(dayjs(dates[0]), 'day') + 1
    }
    return 0
  }, [filters.start, filters.end, calendarHeatmap])

  const useDailyBuckets = rangeDays > 0 && rangeDays <= 45

  const dailySeries = useMemo(
    () =>
      calendarHeatmap
        .slice()
        .sort((a, b) => (a.date > b.date ? 1 : -1))
        .map((cell) => ({
          date: cell.date,
          fails: cell.fail_count,
          inspections: cell.inspection_count,
        })),
    [calendarHeatmap],
  )

  const monthlySeries = useDailyBuckets
    ? dailySeries.map((d) => ({ month: d.date, fails: d.fails }))
    : (
        monthlyTrend.length > 0
          ? monthlyTrend.map((p) => ({ month: p.month, fails: p.fail_count }))
          : Array.from(aggregatedByMonth.entries()).map(([month, entry]) => ({ month, fails: entry.fails }))
      ).sort((a, b) => (a.month > b.month ? 1 : -1))

  const cadenceSeries = useDailyBuckets
    ? dailySeries.map((d) => ({ month: d.date, inspections: d.inspections }))
    : (
        cadenceApi.length > 0
          ? cadenceApi.map((p) => ({ month: p.month, inspections: p.inspections }))
          : Array.from(aggregatedByMonth.entries()).map(([month, entry]) => ({
              month,
              inspections: entry.inspections,
            }))
      ).sort((a, b) => (a.month > b.month ? 1 : -1))

  const monthFailMap = useMemo(() => {
    const map = new Map<string, number>()
    monthlySeries.forEach((p) => {
      const key = dayjs(p.month).format('YYYY-MM')
      map.set(key, (map.get(key) ?? 0) + (p.fails ?? 0))
    })
    return map
  }, [monthlySeries])

  const monthInspectionMap = useMemo(() => {
    const map = new Map<string, number>()
    cadenceSeries.forEach((p) => {
      const key = dayjs(p.month).format('YYYY-MM')
      map.set(key, (map.get(key) ?? 0) + (p.inspections ?? 0))
    })
    return map
  }, [cadenceSeries])

  const failTrendData = monthlySeries.map((p) => ({
    label: dayjs(`${p.month}${useDailyBuckets ? '' : '-01'}`).format(useDailyBuckets ? 'MMM D' : 'MMM YY'),
    value: p.fails ?? 0,
  }))

  const cadenceChartData = cadenceSeries.map((p) => ({
    label: dayjs(`${p.month}${useDailyBuckets ? '' : '-01'}`).format(useDailyBuckets ? 'MMM D' : 'MMM YY'),
    value: p.inspections ?? 0,
  }))

  const availableMonths = useMemo(() => {
    const months = new Set<string>()
    monthlySeries.forEach((p) => months.add(dayjs(p.month).format('YYYY-MM')))
    cadenceSeries.forEach((p) => months.add(dayjs(p.month).format('YYYY-MM')))
    return Array.from(months).sort()
  }, [monthlySeries, cadenceSeries])

  if (isLoading) {
    return (
      <div className="grid gap-4 md:grid-cols-2">
        {[...Array(4)].map((_, idx) => (
          <Card key={idx}>
            <Skeleton className="h-24 w-full" />
          </Card>
        ))}
      </div>
    )
  }

  if (isError || !data) {
    return (
      <ErrorState
        message="Unable to load dashboard priorities"
        action={
          <button className="text-sm font-semibold text-brand-600" onClick={() => refetch()}>
            Try again
          </button>
        }
      />
    )
  }

  const completionRate = data.completion.completion_rate
  const openInspections = data.completion.open
  const openIssues = data.issue_closure.open
  const warehouseHotspot = data.hotspots.find((h) => h.location.toLowerCase().includes('warehouse'))

  return (
    <div className="space-y-6">
      <FilterBar
        preset={preset}
        onPresetChange={(value) => setPreset(value as typeof preset)}
        startDate={filters.start}
        endDate={filters.end}
        onDateChange={(start, end) => {
          setCustomStart(start)
          setCustomEnd(end)
        }}
        templateId={templateId}
        onTemplateChange={setTemplateId}
        location={location}
        onLocationChange={setLocation}
        itemQuery={itemQuery}
        onItemQueryChange={setItemQuery}
        inspectorId={inspectorId}
        onInspectorChange={setInspectorId}
        templates={templates}
        locations={locations}
        inspectors={inspectors}
        onReset={() => {
          setPreset('90')
          setCustomStart(undefined)
          setCustomEnd(undefined)
          setTemplateId('')
          setLocation('')
          setInspectorId('')
          setItemQuery('')
          setCalendarMonth(dayjs().format('YYYY-MM'))
        }}
      />
      <section className="rounded-2xl bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 p-6 shadow-xl">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="space-y-3 text-white">
            <div className="flex items-center gap-3 text-sm">
              <Badge variant="info">Live · Data-backed</Badge>
              <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-200">
                Powered by SQLite
              </span>
            </div>
            <h1 className="text-2xl font-semibold leading-tight md:text-3xl">Dashboards · Inspection priorities</h1>
            <p className="max-w-3xl text-slate-200">
              Ten tiles wired to the current database: completion health, closure, fail themes, hotspots, cadence, and
              workload—ready for deeper charting and queries.
            </p>
          </div>
          <div className="flex items-center gap-3 rounded-xl bg-white/10 px-4 py-3 text-sm text-slate-100 ring-1 ring-white/15">
            <Sparkles className="h-5 w-5 text-amber-300" />
            <div>
              <p className="font-semibold text-white">This week&apos;s lift</p>
              <p className="text-slate-200">
                Close {openInspections} open inspections · {openIssues} open issues
              </p>
            </div>
          </div>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl bg-white/5 p-4 text-white ring-1 ring-white/10">
            <p className="text-sm text-slate-200">Completion rate</p>
            <p className="mt-2 text-3xl font-semibold">{completionRate}%</p>
            <p className="text-xs text-slate-200">
              {data.completion.completed} of {data.completion.total} inspections done · {openInspections} open
            </p>
          </div>
          <div className="rounded-xl bg-white/5 p-4 text-white ring-1 ring-white/10">
            <p className="text-sm text-slate-200">Issue closure</p>
            <p className="mt-2 text-3xl font-semibold">{data.issue_closure.closure_rate}%</p>
            <p className="text-xs text-slate-200">
              {data.issue_closure.closed} closed · {openIssues} open · {data.issue_closure.with_corrective_action} with corrective actions
            </p>
          </div>
          <div className="rounded-xl bg-white/5 p-4 text-white ring-1 ring-white/10">
            <p className="text-sm text-slate-200">Longest gap</p>
            <p className="mt-2 text-3xl font-semibold">{data.longest_gap_days} days</p>
            <p className="text-xs text-slate-200">Between inspections</p>
          </div>
          <div className="rounded-xl bg-white/5 p-4 text-white ring-1 ring-white/10">
            <p className="text-sm text-slate-200">Hotspot</p>
            <p className="mt-2 text-3xl font-semibold">
              {warehouseHotspot ? `${warehouseHotspot.issue_count} issues` : '—'}
            </p>
            <p className="text-xs text-slate-200">
              {warehouseHotspot ? `${warehouseHotspot.location} leads issue count` : 'No hotspots yet'}
            </p>
          </div>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-12">
        <Card
          className="lg:col-span-5"
          title={
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-brand-600" />
              <span>Completion health</span>
            </div>
          }
          subtitle="Closed vs open inspections"
        >
          <div className="space-y-4">
            <div className="flex items-center justify-between text-sm font-semibold text-slate-700">
              <span>Completed</span>
              <span>
                {data.completion.completed}/{data.completion.total}
              </span>
            </div>
            <ProgressBar value={completionRate} />
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>{openInspections} open inspections need attention</span>
              <Badge variant="warning">Act now</Badge>
            </div>
          </div>
        </Card>

        <Card
          className="lg:col-span-7"
          title={
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-600" />
              <span>Issue closure</span>
            </div>
          }
          subtitle={`${data.issue_closure.total} issues logged · closure + corrective actions`}
        >
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <p className="text-sm text-slate-600">Closed</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{data.issue_closure.closed}</p>
              <p className="text-xs text-slate-500">{data.issue_closure.closure_rate}% closure rate</p>
            </div>
            <div className="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <p className="text-sm text-slate-600">Open</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{openIssues}</p>
              <p className="text-xs text-slate-500">Keep follow-ups moving</p>
            </div>
            <div className="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <p className="text-sm text-slate-600">With corrective action</p>
              <p className="mt-1 text-2xl font-semibold text-slate-900">{data.issue_closure.with_corrective_action}</p>
              <p className="text-xs text-slate-500">
                {data.issue_closure.total ? Math.round((data.issue_closure.with_corrective_action / data.issue_closure.total) * 100) : 0}
                % have next steps
              </p>
            </div>
          </div>
          <div className="mt-4 space-y-2 text-sm text-slate-600">
            <div className="flex items-center gap-2">
              <Badge variant="danger">Blocker</Badge>
              <span>{openIssues} issues still waiting on completion; push owners for closure.</span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="info">Workflow</Badge>
              <span>Surface overdue items first and highlight missing corrective actions.</span>
            </div>
          </div>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <Card
          className="lg:col-span-5"
          title={
            <div className="flex items-center gap-2">
              <Flame className="h-5 w-5 text-amber-600" />
              <span>Top fail categories</span>
            </div>
          }
          subtitle="Pass / fail by checklist item"
        >
          <div className="space-y-3">
            {data.fail_categories.map((item) => (
              <div key={item.label} className="space-y-1">
                <div className="flex items-center justify-between text-sm text-slate-700">
                  <span className="truncate pr-2">{item.label}</span>
                  <span className="font-semibold">{item.fail_rate}% fail</span>
                </div>
                <GradientBar fail={item.fail_count} pass={item.pass_count} />
              </div>
            ))}
          </div>
          <div className="mt-3 text-xs text-slate-500">
            Stack shows fail (red) vs pass (green). Prioritize the highest fail-rate items first.
          </div>
        </Card>

        <Card
          className="lg:col-span-7"
          title={
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-brand-600" />
              <span>Fail trend (filtered)</span>
            </div>
          }
          subtitle="Fail counts within the selected filters"
        >
          <ChartContainer className="bg-gradient-to-b from-brand-50/60 to-white">
            <TrendLine data={failTrendData} xKey="label" yKey="value" color="#2563eb" name="Fails" />
          </ChartContainer>
          <div className="mt-3 text-xs text-slate-500">
            Peaks highlight periods with higher fail counts; driven by your current filters.
          </div>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <Card
          className="lg:col-span-5"
          title={
            <div className="flex items-center gap-2">
              <MapPin className="h-5 w-5 text-emerald-600" />
              <span>Hotspot locations</span>
            </div>
          }
          subtitle="Issues by area"
        >
          <div className="space-y-4">
            {data.hotspots.length === 0 ? (
              <p className="text-sm text-slate-600">No issues logged yet.</p>
            ) : (
              data.hotspots.map((spot) => (
                <div key={spot.location} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <div className="flex items-center justify-between text-sm text-slate-700">
                    <span>{spot.location}</span>
                    <Badge variant="warning">{spot.issue_count} issues</Badge>
                  </div>
                  <ProgressBar value={Math.min((spot.issue_count / (data.issue_closure.total || 1)) * 100, 100)} tone="brand" />
                </div>
              ))
            )}
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-slate-100 bg-white p-3">
                <p className="text-xs font-semibold text-slate-700">Map idea</p>
                <p className="text-xs text-slate-500">Stacked bars by area + severity heat dots</p>
              </div>
              <div className="rounded-lg border border-slate-100 bg-white p-3">
                <p className="text-xs font-semibold text-slate-700">Next step</p>
                <p className="text-xs text-slate-500">Walk hotspots first and close open issues.</p>
              </div>
            </div>
          </div>
        </Card>

        <Card
          className="lg:col-span-7"
          title={
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-indigo-600" />
              <span>Inspector workload</span>
            </div>
          }
          subtitle="Assignments vs outcomes"
        >
          <div className="space-y-4">
            {data.inspector_workload.map((inspector) => (
              <div key={inspector.inspector_id} className="space-y-1">
                <div className="flex items-center justify-between text-sm text-slate-700">
                  <span>{inspector.name}</span>
                  <span className="font-semibold">{inspector.inspection_count} inspections</span>
                </div>
                <ProgressBar value={(inspector.inspection_count / (data.completion.total || 1)) * 100} tone="brand" />
              </div>
            ))}
            <div className="mt-2 text-xs text-slate-500">
              Rebalance heavy workloads to compare outcomes side-by-side.
            </div>
          </div>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <Card
          className="lg:col-span-4"
          title={
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-600" />
              <span>Duplicates & data quality</span>
            </div>
          }
          subtitle="Reduce noise + rework"
        >
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm text-slate-700">
              <span>Duplicate item entries</span>
              <Badge variant="danger">{data.duplicates.duplicate_records}</Badge>
            </div>
            <p className="text-xs text-slate-500">
              {data.duplicates.days_with_duplicates} days with duplicates; max {data.duplicates.max_duplicates_in_day} in a single day—flag spikes automatically.
            </p>
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <Target className="h-4 w-4 text-brand-600" />
              <span>Rule: collapse identical item+date, prompt inspector to merge.</span>
            </div>
          </div>
        </Card>

        <Card
          className="lg:col-span-4"
          title={
            <div className="flex items-center gap-2">
              <Clock3 className="h-5 w-5 text-amber-600" />
              <span>Cycle time anomalies</span>
            </div>
          }
          subtitle="Time-to-submit distribution"
        >
          <div className="space-y-2 text-sm text-slate-700">
            <div className="flex items-center justify-between">
              <span>Average</span>
              <span className="font-semibold">{data.duration.average_minutes ?? '—'} min</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Median</span>
              <span className="font-semibold">{data.duration.median_minutes ?? '—'} min</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Max</span>
              <span className="font-semibold">{data.duration.max_minutes ?? '—'} min</span>
            </div>
            <div className="h-16 rounded-lg bg-slate-50">
              <div className="flex h-full items-end gap-1 px-2 pb-1">
                <div className="h-4 w-6 rounded-md bg-slate-200" />
                <div className="h-6 w-6 rounded-md bg-slate-200" />
                <div className="h-8 w-6 rounded-md bg-slate-200" />
                <div className="h-5 w-6 rounded-md bg-slate-200" />
                <div className="h-12 w-6 rounded-md bg-amber-400" title="outlier" />
              </div>
            </div>
            <p className="text-xs text-slate-500">Alert when duration &gt; 30 min; show inspector note prompt.</p>
          </div>
        </Card>

        <Card
          className="lg:col-span-4"
          title={
            <div className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-emerald-600" />
              <span>Issue density</span>
            </div>
          }
          subtitle="Find inspections generating multiple findings"
        >
          <div className="space-y-3 text-sm text-slate-700">
            <div className="flex items-center justify-between">
              <span>Avg issues per inspection</span>
              <span className="font-semibold">{data.issue_density.average_issues ?? '—'}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>Max issues on a single inspection</span>
              <span className="font-semibold">{data.issue_density.max_issues ?? '—'}</span>
            </div>
            <ProgressBar
              value={
                data.issue_density.max_issues
                  ? ((data.issue_density.average_issues ?? 0) / data.issue_density.max_issues) * 100
                  : 0
              }
            />
            <p className="text-xs text-slate-500">
              Highlight repeat offenders and auto-create follow-up checklist.
            </p>
          </div>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-12">
        <Card
          className="lg:col-span-12"
          title={
            <div className="flex items-center gap-2">
              <Clock3 className="h-5 w-5 text-brand-600" />
              <span>Cadence & coverage gaps</span>
            </div>
          }
          subtitle="Area + calendar heatmap"
        >
          <div className="grid gap-3 lg:grid-cols-3">
            <div className="space-y-2 rounded-lg border border-slate-100 bg-slate-50 p-4">
              <p className="text-sm font-semibold text-slate-700">Inspections (filtered)</p>
              <ChartContainer className="bg-gradient-to-b from-brand-50/60 to-white">
                <TrendBar data={cadenceChartData} xKey="label" yKey="value" color="#2563eb" name="Inspections" />
              </ChartContainer>
            </div>
            <div className="space-y-3 rounded-lg border border-slate-100 bg-white p-4">
              <p className="text-sm font-semibold text-slate-700">Longest gaps</p>
              <div className="space-y-2 text-xs text-slate-600">
                <div className="flex items-center justify-between">
                  <span>Max gap</span>
                  <Badge variant="warning">{data.longest_gap_days} days</Badge>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <Target className="h-4 w-4 text-brand-600" />
                  <span>Target: no gaps over 14 days; add reminders.</span>
                </div>
                <div className="flex items-center gap-2 text-slate-600">
                  <MapPin className="h-4 w-4 text-emerald-600" />
                  <span>{data.cadence.length} months of coverage tracked.</span>
                </div>
              </div>
            </div>
            <div className="space-y-3 rounded-lg border border-slate-100 bg-white p-4">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-semibold text-slate-700">Calendar heatmap (fails per day)</p>
                <Select
                  value={calendarMonth}
                  onChange={(e) => setCalendarMonth(e.target.value || dayjs().format('YYYY-MM'))}
                  className="h-9 w-36 text-sm"
                >
                  {availableMonths.length === 0 ? (
                    <option value={calendarMonth}>{dayjs(calendarMonth).format('MMM YYYY')}</option>
                  ) : (
                    availableMonths.map((month) => (
                      <option key={month} value={month}>
                        {dayjs(`${month}-01`).format('MMM YYYY')}
                      </option>
                    ))
                  )}
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs text-slate-600">
                <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <p className="font-semibold text-slate-700">Current month</p>
                  <p>{dayjs(`${calendarMonth}-01`).format('MMM YYYY')}</p>
                  <p>Fails: {monthFailMap.get(calendarMonth) ?? 0}</p>
                  <p>Inspections: {monthInspectionMap.get(calendarMonth) ?? 0}</p>
                </div>
                <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <p className="font-semibold text-slate-700">Prior month</p>
                  <p>{dayjs(`${calendarMonth}-01`).subtract(1, 'month').format('MMM YYYY')}</p>
                  <p>Fails: {monthFailMap.get(dayjs(`${calendarMonth}-01`).subtract(1, 'month').format('YYYY-MM')) ?? 0}</p>
                  <p>Inspections: {monthInspectionMap.get(dayjs(`${calendarMonth}-01`).subtract(1, 'month').format('YYYY-MM')) ?? 0}</p>
                </div>
              </div>
              {data.calendar_heatmap.length === 0 ? (
                <p className="text-xs text-slate-500">No fails recorded yet.</p>
              ) : (
                <CalendarHeatmap cells={data.calendar_heatmap as CalendarCell[]} />
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  )
}
