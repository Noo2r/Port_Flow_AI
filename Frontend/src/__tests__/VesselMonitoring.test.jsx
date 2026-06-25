/**
 * TC-FE-VSL — Vessel Monitoring Page Tests
 * PortFlow AI Frontend Tests
 *
 * Run: npx vitest run src/__tests__/VesselMonitoring.test.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '../test/renderWithProviders'

// ── mock vessels API ─────────────────────────────────────────────────────────
// vi.mock() factories are hoisted above the rest of the module, so a plain
// top-level `const` referenced inside one throws "Cannot access before
// initialization". vi.hoisted() runs before that hoisting, making it safe.
const { mockVessels } = vi.hoisted(() => ({
  mockVessels: [
    {
      id: 1, name: 'MV Alpha', imo_number: 'IMO9000001',
      vessel_type: 'container', status: 'at_sea', flag: 'EG',
      call_sign: 'EGAA1', created_at: '2026-01-01T00:00:00Z',
    },
    {
      id: 2, name: 'MV Beta', imo_number: 'IMO9000002',
      vessel_type: 'tanker', status: 'berthed', flag: 'GR',
      call_sign: 'GRBB2', created_at: '2026-01-02T00:00:00Z',
    },
  ],
}))

// Real api.js calls resolve the flat array/object directly (no {data: ...}
// envelope) — see services/api.js's request() helper.
vi.mock('../services/api', () => ({
  vesselsApi: {
    list: vi.fn().mockResolvedValue(mockVessels),
    create: vi.fn().mockResolvedValue({ id: 3, name: 'MV Gamma', imo_number: 'IMO9000003', vessel_type: 'bulk_carrier', status: 'at_sea', flag: 'US' }),
    delete: vi.fn().mockResolvedValue({}),
  },
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'admin' }, isAuthenticated: true }),
}))

import VesselMonitoring from '../pages/VesselMonitoring'

function renderPage() {
  return renderWithProviders(<VesselMonitoring />)
}

describe('TC-FE-VSL — Vessel Monitoring Page', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('TC-FE-VSL-01: renders vessel names from API in table', async () => {
    renderPage()
    await waitFor(() => {
      expect(screen.getByText('MV Alpha')).toBeTruthy()
      expect(screen.getByText('MV Beta')).toBeTruthy()
    })
  })

  it('TC-FE-VSL-02: shows empty state when no vessels returned', async () => {
    const { vesselsApi } = await import('../services/api')
    vi.mocked(vesselsApi.list).mockResolvedValueOnce([])

    renderPage()
    await waitFor(() => {
      // Should show empty state text or no table rows
      const rows = document.querySelectorAll('tbody tr')
      expect(rows.length).toBe(0)
    })
  })

  it('TC-FE-VSL-03: "Add Vessel" button opens modal with form fields', async () => {
    renderPage()
    await waitFor(() => screen.getByText('MV Alpha'))

    const addBtn = screen.getByRole('button', { name: /add vessel|new vessel/i })
    fireEvent.click(addBtn)

    await waitFor(() => {
      // Modal should appear
      expect(
        document.querySelector('input[name="name"]') ||
        screen.queryByPlaceholderText(/vessel name/i)
      ).toBeTruthy()
    })
  })

  it('TC-FE-VSL-04: submit Add Vessel form calls POST API', async () => {
    const { vesselsApi } = await import('../services/api')
    renderPage()
    await waitFor(() => screen.getByText('MV Alpha'))

    const addBtn = screen.getByRole('button', { name: /add vessel|new vessel/i })
    fireEvent.click(addBtn)

    await waitFor(() => {
      const nameInput = document.querySelector('input[name="name"]') ||
                        screen.queryByPlaceholderText(/vessel name/i)
      if (nameInput) {
        fireEvent.change(nameInput, { target: { value: 'MV Gamma' } })
      }
    })

    // IMO is required too — fill it so native form validation doesn't block submit
    const imoInput = document.querySelector('input[name="imo_number"]')
    if (imoInput) {
      fireEvent.change(imoInput, { target: { value: '9000003' } })
    }

    const submitBtn = document.querySelector('button[type="submit"]') ||
                      screen.queryByRole('button', { name: /save|create|add/i })
    if (submitBtn) fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(vesselsApi.create).toHaveBeenCalled()
    }, { timeout: 2000 })
  })

  it('TC-FE-VSL-05: page renders without throwing', () => {
    expect(() => renderPage()).not.toThrow()
  })

  it('TC-FE-VSL-06: vessel API is called on mount', async () => {
    const { vesselsApi } = await import('../services/api')
    renderPage()
    await waitFor(() => {
      expect(vesselsApi.list).toHaveBeenCalled()
    })
  })
})
