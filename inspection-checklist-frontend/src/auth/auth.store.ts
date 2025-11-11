import type { components } from '@/api/gen/schema'
import { resetQueryCache } from '@/lib/queryClient'

export type AuthUser = components['schemas']['UserRead']

export type AuthState = {
  token: string | null
  user: AuthUser | null
  isHydrated: boolean
}

const STORAGE_KEY = 'inspection_auth_state'

const listeners = new Set<() => void>()

let state: AuthState = {
  token: null,
  user: null,
  isHydrated: typeof window === 'undefined',
}

const persist = () => {
  if (typeof window === 'undefined') {
    return
  }
  if (state.token) {
    const payload = JSON.stringify({ token: state.token, user: state.user })
    sessionStorage.setItem(STORAGE_KEY, payload)
  } else {
    sessionStorage.removeItem(STORAGE_KEY)
  }
}

const hydrate = () => {
  if (state.isHydrated) {
    return
  }
  if (typeof window === 'undefined') {
    state = { ...state, isHydrated: true }
    return
  }
  const raw = sessionStorage.getItem(STORAGE_KEY)
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as Pick<AuthState, 'token' | 'user'>
      state = { ...state, ...parsed, isHydrated: true }
    } catch (error) {
      console.error('Failed to parse auth session payload', error)
      sessionStorage.removeItem(STORAGE_KEY)
      state = { ...state, isHydrated: true }
    }
  } else {
    state = { ...state, isHydrated: true }
  }
}

hydrate()

const notify = () => {
  listeners.forEach((listener) => listener())
}

export const authStore = {
  subscribe(listener: () => void) {
    listeners.add(listener)
    return () => listeners.delete(listener)
  },
  getState(): AuthState {
    hydrate()
    return state
  },
  setState(partial: Partial<AuthState>) {
    state = { ...state, ...partial }
    persist()
    notify()
  },
  clear() {
    state = { token: null, user: null, isHydrated: true }
    persist()
    resetQueryCache()
    notify()
  },
}
