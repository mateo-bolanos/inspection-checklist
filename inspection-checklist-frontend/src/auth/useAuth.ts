import { useEffect, useMemo, useRef, useState } from 'react'
import { useSyncExternalStore } from 'react'

import { api } from '@/api/client'
import type { components } from '@/api/gen/schema'
import { ROLE_HOME_ROUTE } from '@/lib/constants'
import { resetQueryCache } from '@/lib/queryClient'

import type { AuthUser } from './auth.store'
import { authStore } from './auth.store'

export const useAuth = () => {
  const auth = useSyncExternalStore(authStore.subscribe, authStore.getState)
  const [isBootstrapping, setBootstrapping] = useState(false)
  const hasFetchedRef = useRef(false)

  useEffect(() => {
    let isActive = true
    if (auth.token && !auth.user && !hasFetchedRef.current) {
      hasFetchedRef.current = true
      setBootstrapping(true)
      api
        .get<components['schemas']['UserRead']>('/auth/me')
        .then((response) => {
          if (!isActive) return
          authStore.setState({ user: response.data })
        })
        .catch((error) => {
          const status = error?.response?.status
          if (status === 401) {
            authStore.clear()
          }
        })
        .finally(() => {
          if (!isActive) return
          setBootstrapping(false)
          hasFetchedRef.current = false
        })
    }
    return () => {
      isActive = false
    }
  }, [auth.token, auth.user])

  const login = (token: string, user?: AuthUser | null) => {
    resetQueryCache()
    authStore.setState({ token, user: user ?? auth.user })
  }

  const logout = () => {
    authStore.clear()
  }

  const hasRole = (roles?: string[]) => {
    if (!roles || roles.length === 0) return true
    return roles.includes(auth.user?.role ?? '')
  }

  const defaultRoute = ROLE_HOME_ROUTE[auth.user?.role ?? 'inspector'] ?? '/dash/overview'

  const value = useMemo(
    () => ({
      token: auth.token,
      user: auth.user,
      isAuthenticated: Boolean(auth.token),
      isHydrated: auth.isHydrated && !isBootstrapping,
      isBootstrapping,
      login,
      logout,
      hasRole,
      defaultRoute,
    }),
    [auth.token, auth.user, auth.isHydrated, isBootstrapping, defaultRoute],
  )

  return value
}
