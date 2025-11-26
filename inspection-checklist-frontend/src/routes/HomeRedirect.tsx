import { Navigate } from 'react-router-dom'

import { useAuth } from '@/auth/useAuth'

export const HomeRedirect = () => {
  const { defaultRoute } = useAuth()
  return <Navigate to={defaultRoute} replace />
}

