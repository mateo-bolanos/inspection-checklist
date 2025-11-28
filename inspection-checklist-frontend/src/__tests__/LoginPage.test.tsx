import { afterAll, afterEach, beforeAll, describe, expect, test } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import userEvent from '@testing-library/user-event'

import { resolveApiUrl } from '@/lib/env'
import { renderWithProviders } from '@/test-utils'
import { LoginPage } from '@/pages/Login'
import { screen, waitFor } from '@testing-library/react'

const server = setupServer(
  http.post(resolveApiUrl('/auth/login'), async () => {
    return HttpResponse.json({ access_token: 'token-123', token_type: 'bearer' })
  }),
  http.get(resolveApiUrl('/auth/me'), () =>
    HttpResponse.json({ id: '1', email: 'admin@example.com', full_name: 'Admin', role: 'admin' }),
  ),
)

beforeAll(() => server.listen())
afterEach(() => {
  server.resetHandlers()
  sessionStorage.clear()
})
afterAll(() => server.close())

describe('LoginPage', () => {
  test('logs in successfully', async () => {
    renderWithProviders(<LoginPage />)
    await userEvent.type(screen.getByLabelText(/email/i), 'admin@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'secret123')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => expect(sessionStorage.getItem('inspection_auth_state')).toContain('token-123'))
  })

  test('shows error on invalid credentials', async () => {
    server.use(
      http.post(resolveApiUrl('/auth/login'), () =>
        HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 }),
      ),
    )
    renderWithProviders(<LoginPage />)

    await userEvent.type(screen.getByLabelText(/email/i), 'admin@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'badpass')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument())
  })
})
