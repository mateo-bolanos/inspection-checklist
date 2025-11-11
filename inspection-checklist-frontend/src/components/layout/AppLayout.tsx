import { Outlet } from 'react-router-dom'

import { useAuth } from '@/auth/useAuth'
import { LoadingState } from '@/components/feedback/LoadingState'

import { SideNav } from './SideNav'
import { TopNav } from './TopNav'

export const AppLayout = () => {
  const { isHydrated } = useAuth()

  if (!isHydrated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50">
        <LoadingState label="Loading your workspace..." />
      </div>
    )
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <TopNav />
      <div className="flex flex-1">
        <SideNav />
        <main className="flex-1 space-y-6 bg-slate-50 px-4 py-6 md:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
