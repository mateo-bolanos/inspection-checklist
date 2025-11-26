import {
  CalendarClock,
  CheckCircle,
  ClipboardList,
  FilePlus2,
  FileSearch2,
  FileText,
  LayoutDashboard,
  Layers3,
  ListChecks,
  Search,
} from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { useAuth } from '@/auth/useAuth'
import { clsx } from 'clsx'

const navItems = [
  { label: 'Overview', to: '/dash/overview', icon: LayoutDashboard, roles: ['admin', 'reviewer'] },
  { label: 'Failing Items', to: '/dash/items', icon: ListChecks, roles: ['admin', 'reviewer'] },
  { label: 'Reports', to: '/reports', icon: FileText, roles: ['admin', 'reviewer'] },
  { label: 'Templates', to: '/templates', icon: Layers3, roles: ['admin'] },
  { label: 'Assignments', to: '/assignments', icon: CalendarClock, roles: ['admin', 'inspector'] },
  { label: 'Start Inspection', to: '/inspections/new', icon: FilePlus2, roles: ['admin', 'inspector'] },
  { label: 'Inspections', to: '/inspections', icon: Search, roles: ['admin', 'inspector', 'reviewer'] },
  { label: 'Actions Board', to: '/actions', icon: ClipboardList, roles: ['admin', 'inspector', 'reviewer', 'action_owner'] },
  { label: 'Search Actions', to: '/actions/search', icon: FileSearch2, roles: ['admin', 'inspector', 'reviewer', 'action_owner'] },
  { label: 'Review Queue', to: '/reviews', icon: CheckCircle, roles: ['admin', 'reviewer'] },
]

type SideNavProps = {
  className?: string
  onNavigate?: () => void
}

export const SideNav = ({ className, onNavigate }: SideNavProps) => {
  const { user } = useAuth()
  const role = user?.role ?? 'inspector'

  return (
    <nav className={clsx('flex flex-col gap-1', className)}>
      {navItems
        .filter((item) => item.roles.includes(role))
        .map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={onNavigate}
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
  )
}
