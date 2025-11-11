export const LoadingState = ({ label = 'Loading data...' }: { label?: string }) => {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-600">
      <span className="h-3 w-3 animate-ping rounded-full bg-brand-500" />
      {label}
    </div>
  )
}
