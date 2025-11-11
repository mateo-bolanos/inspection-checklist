import { beforeEach, describe, expect, test } from 'vitest'

import { authStore } from './auth.store'

const sampleUser = {
  id: 'user-1',
  full_name: 'Jane Inspector',
  email: 'jane@example.com',
  role: 'inspector',
}

beforeEach(() => {
  sessionStorage.clear()
  authStore.clear()
})

describe('authStore', () => {
  test('persists token and user to sessionStorage', () => {
    authStore.setState({ token: 'token-123', user: sampleUser })
    const snapshot = authStore.getState()
    expect(snapshot.token).toBe('token-123')
    expect(snapshot.user?.email).toBe('jane@example.com')
    expect(sessionStorage.getItem('inspection_auth_state')).toContain('token-123')
  })

  test('clear removes persisted data', () => {
    authStore.setState({ token: 'token-abc', user: sampleUser })
    authStore.clear()
    const snapshot = authStore.getState()
    expect(snapshot.token).toBeNull()
    expect(sessionStorage.getItem('inspection_auth_state')).toBeNull()
  })
})
