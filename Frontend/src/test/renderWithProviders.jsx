/**
 * Shared test render helper.
 *
 * Any page using the hooks in src/hooks/queries.js needs a QueryClient in
 * context, or useQuery() throws. Tests render pages in isolation (no real
 * App.jsx tree), so each test file needs to supply its own — this wraps
 * MemoryRouter + a fresh QueryClient (retry disabled, so failed queries
 * don't hang a test waiting for retries) so every test gets a clean cache.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

export function renderWithProviders(ui, { route = '/' } = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        {ui}
      </MemoryRouter>
    </QueryClientProvider>
  )
}
