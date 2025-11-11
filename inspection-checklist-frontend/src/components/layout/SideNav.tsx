import { CheckCircle, ClipboardList, FilePlus2, LayoutDashboard, Layers3, LineChart, ListChecks, Search, Upload } from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { useAuth } from '@/auth/useAuth'
import { clsx } from 'clsx'

const navItems = [
  { label: 'Overview', to: '/dash/overview', icon: LayoutDashboard, roles: ['admin', 'reviewer'] },
  { label: 'Corrective Actions', to: '/dash/actions', icon: LineChart, roles: ['admin', 'reviewer'] },
  { label: 'Failing Items', to: '/dash/items', icon: ListChecks, roles: ['admin', 'reviewer'] },
  { label: 'Templates', to: '/templates', icon: Layers3, roles: ['admin'] },
  { label: 'Start Inspection', to: '/inspections/new', icon: FilePlus2, roles: ['admin', 'inspector'] },
  { label: 'Inspections', to: '/inspections', icon: Search, roles: ['admin', 'inspector', 'reviewer'] },
  { label: 'Actions Board', to: '/actions', icon: ClipboardList, roles: ['admin', 'inspector', 'reviewer'] },
  { label: 'Review Queue', to: '/reviews', icon: CheckCircle, roles: ['admin', 'reviewer'] },
  { label: 'Upload Center', to: '/files/upload', icon: Upload, roles: ['admin', 'inspector'] },
]

export const SideNav = () => {
  const { user } = useAuth()
  const role = user?.role ?? 'inspector'

  return (
    <aside className="hidden w-64 border-r border-slate-200 bg-white/90 p-4 md:block">
      <nav className="flex flex-col gap-1">
        {navItems
          .filter((item) => item.roles.includes(role))
          .map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  clsx(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100',
                    isActive && 'bg-brand-50 text-brand-700',
                  )
                }
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </NavLink>
            )
          })}
      </nav>
    </aside>
  )
}
