import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { X } from 'lucide-react'

import { useAuth } from '@/auth/useAuth'
import { LoadingState } from '@/components/feedback/LoadingState'

import { SideNav } from './SideNav'
import { TopNav } from './TopNav'

export const AppLayout = () => {
  const { isHydrated } = useAuth()
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false)
  const logoSrc = '/moore-logo.png'

  const toggleMobileNav = () => setIsMobileNavOpen((prev) => !prev)
  const closeMobileNav = () => setIsMobileNavOpen(false)

  if (!isHydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <LoadingState label="Loading your workspace..." />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <TopNav onToggleSidebar={toggleMobileNav} />
      <div className="flex flex-1">
        <aside className="hidden w-64 border-r border-slate-200 bg-white/90 p-4 md:block">
          <SideNav />
        </aside>
        <main className="flex-1 space-y-6 bg-slate-50 px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>

      <div
        className={`fixed inset-0 z-40 bg-slate-900/50 transition-opacity md:hidden ${
          isMobileNavOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={closeMobileNav}
      />
      <div
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-xl transition-transform md:hidden ${
          isMobileNavOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <div className="flex items-center gap-2">
            <img src={logoSrc} alt="Moore brand logo" className="h-7 w-auto brightness-0" />
            <p className="text-sm font-semibold text-slate-700">Navigation</p>
          </div>
          <button
            type="button"
            onClick={closeMobileNav}
            className="rounded-md p-1 text-slate-500 transition hover:bg-slate-100 hover:text-slate-900"
          >
            <span className="sr-only">Close menu</span>
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="p-4">
          <SideNav onNavigate={closeMobileNav} />
        </div>
      </div>
    </div>
  )
}
