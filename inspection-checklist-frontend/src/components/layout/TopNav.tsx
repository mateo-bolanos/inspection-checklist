import { Menu, ShieldCheck, UserRound } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '@/auth/useAuth'
import { Button } from '@/components/ui/Button'

type TopNavProps = {
  onToggleSidebar?: () => void
}

export const TopNav = ({ onToggleSidebar }: TopNavProps) => {
  const { user, logout, defaultRoute } = useAuth()
  const navigate = useNavigate()

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="rounded-md p-2 text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 md:hidden"
        >
          <span className="sr-only">Toggle navigation</span>
          <Menu className="h-5 w-5" />
        </button>
        <button
          type="button"
          className="flex items-center gap-2 text-lg font-semibold text-slate-900"
          onClick={() => navigate(defaultRoute)}
        >
          <ShieldCheck className="h-6 w-6 text-brand-600" />
          Safety Inspection
        </button>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 rounded-full bg-slate-50 px-3 py-1 text-sm text-slate-600">
          <UserRound className="h-4 w-4 text-slate-500" />
          <span className="font-medium text-slate-900">{user?.full_name}</span>
          <span className="text-xs uppercase text-slate-500">{user?.role}</span>
        </div>
        <Button variant="ghost" onClick={logout}>
          Logout
        </Button>
      </div>
    </header>
  )
}
