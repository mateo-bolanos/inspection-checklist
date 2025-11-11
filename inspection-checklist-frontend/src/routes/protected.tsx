import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'

import { useAuth } from '@/auth/useAuth'

export type ProtectedRouteProps = {
  children: ReactNode
  roles?: string[]
}

export const ProtectedRoute = ({ children, roles }: ProtectedRouteProps) => {
  const location = useLocation()
  const { isHydrated, isAuthenticated, hasRole, defaultRoute } = useAuth()

  if (!isHydrated) {
    return null
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (roles && !hasRole(roles)) {
    return <Navigate to={defaultRoute} replace />
  }

  return <>{children}</>
}
