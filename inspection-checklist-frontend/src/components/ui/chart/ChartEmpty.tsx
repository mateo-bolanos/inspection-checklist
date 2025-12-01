type ChartEmptyProps = {
  message?: string
  height?: number
}

export const ChartEmpty = ({ message = 'No data for this range.', height = 160 }: ChartEmptyProps) => {
  return (
    <div
      className="flex w-full items-center justify-center rounded-lg border border-dashed border-slate-200 bg-white text-sm text-slate-500"
      style={{ height }}
    >
      {message}
    </div>
  )
}
