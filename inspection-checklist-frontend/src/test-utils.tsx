import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import type { ReactElement, ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'

import { ToastProvider } from '@/components/ui/ToastProvider'

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

export type RenderOptions = {
  route?: string
}

export const renderWithProviders = (ui: ReactElement, { route = '/' }: RenderOptions = {}) => {
  const client = createTestQueryClient()
  const wrapper = ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={[route]}>
      <QueryClientProvider client={client}>
        <ToastProvider>{children}</ToastProvider>
      </QueryClientProvider>
    </MemoryRouter>
  )
  return render(ui, { wrapper })
}
