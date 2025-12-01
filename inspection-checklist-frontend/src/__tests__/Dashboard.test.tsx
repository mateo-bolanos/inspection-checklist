import { afterAll, afterEach, beforeAll, describe, expect, test } from 'vitest'
import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import { screen, waitFor } from '@testing-library/react'

import { OverviewPage } from '@/pages/Dashboard/Overview'
import { resolveApiUrl } from '@/lib/env'
import { renderWithProviders } from '@/test-utils'

const server = setupServer(
  http.get(resolveApiUrl('/dash/overview'), () =>
    HttpResponse.json({
      total_inspections: 12,
      submitted_inspections: 4,
      approval_rate: 75,
      average_score: 87.5,
    }),
  ),
  http.get(resolveApiUrl('/templates/'), () => HttpResponse.json([])),
  http.get(resolveApiUrl('/inspections/'), () =>
    HttpResponse.json({ items: [], total: 0, page: 1, page_size: 4 }),
  ),
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('OverviewPage', () => {
  test('renders metrics from API', async () => {
    renderWithProviders(<OverviewPage />)
    await waitFor(() => expect(screen.getByText('12')).toBeInTheDocument())
    expect(screen.getByText('4')).toBeInTheDocument()
    expect(screen.getByText('75.0%')).toBeInTheDocument()
  })
})
