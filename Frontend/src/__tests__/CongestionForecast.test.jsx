/**
 * TC-FE-CONGESTION — Congestion Forecast Page Tests
 * PortFlow AI Frontend Tests
 *
 * Run: npx vitest run src/__tests__/CongestionForecast.test.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import { renderWithProviders } from '../test/renderWithProviders'

// vi.mock() factories are hoisted above the rest of the module, so a plain
// top-level `const` referenced inside one throws "Cannot access before
// initialization". vi.hoisted() runs before that hoisting, making it safe.
const { mockPrediction } = vi.hoisted(() => ({
  mockPrediction: {
    congestion_level: 0.71, congestion_pct: 71.0, congestion_label: 'High', congestion_color: '#f97316',
    queue_length: 4, risk_score: 0.56, risk_pct: 56.0, confidence: 0.58,
    top_factors: [{ feature: 'port_congestion_index', importance_pct: 4.1 }],
    congestion_model: 'LightGBM', queue_model: 'CatBoost',
  },
}))

vi.mock('../services/api', () => ({
  congestionApi: {
    portOverview: vi.fn().mockResolvedValue({
      ports: [
        { port_id: 'PORT_A', port_name: 'Alexandria', congestion_label: 'High', congestion_pct: 71.0, congestion_color: '#f97316' },
        { port_id: 'PORT_B', port_name: 'Port Said', congestion_label: 'Low', congestion_pct: 12.0, congestion_color: '#22c55e' },
      ],
      count: 2,
    }),
    evaluation: vi.fn().mockResolvedValue({
      models: {
        congestion: { name: 'LightGBM', R2: 0.937, MAE: 0.038, grade: 'Excellent' },
        queue: { name: 'CatBoost', R2: 0.51, MAE: 1.69, grade: 'Good' },
      },
    }),
    modelInfo: vi.fn().mockResolvedValue({
      congestion_model_name: 'LightGBM', queue_model_name: 'CatBoost', features: 43,
      metrics: {
        congestion: { MAE: 0.038, RMSE: 0.053, R2: 0.937 },
        queue: { MAE: 1.69, RMSE: 2.17, R2: 0.51 },
      },
      feature_importance: { congestion: [], queue: [] },
    }),
    predict: vi.fn().mockResolvedValue(mockPrediction),
  },
}))

vi.mock('../context/AuthContext', () => ({
  useAuth: () => ({ user: { role: 'analyst' }, isAuthenticated: true }),
}))

import CongestionForecast from '../pages/CongestionForecast'

function renderPage() {
  return renderWithProviders(<CongestionForecast />)
}

describe('TC-FE-CONGESTION — Congestion Forecast Page', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('TC-FE-CONGESTION-01: renders without throwing', () => {
    expect(() => renderPage()).not.toThrow()
  })

  it('TC-FE-CONGESTION-02: fetches port overview, evaluation, model info, and an initial prediction on mount', async () => {
    const { congestionApi } = await import('../services/api')
    renderPage()
    await waitFor(() => {
      expect(congestionApi.portOverview).toHaveBeenCalled()
      expect(congestionApi.evaluation).toHaveBeenCalled()
      expect(congestionApi.modelInfo).toHaveBeenCalled()
      expect(congestionApi.predict).toHaveBeenCalled()
    })
  })

  it('TC-FE-CONGESTION-03: displays real port names and labels from the API, not hardcoded ports', async () => {
    renderPage()
    await waitFor(() => {
      expect(document.body.textContent).toContain('Alexandria')
      expect(document.body.textContent).toContain('Port Said')
    }, { timeout: 3000 })
  })

  it('TC-FE-CONGESTION-04: port congestion percentages come from the API response', async () => {
    renderPage()
    await waitFor(() => {
      // 71% and 12% are the mocked congestion_pct values — they must not be
      // replaced by a hardcoded placeholder.
      expect(document.body.textContent).toMatch(/71(\.0)?%/)
      expect(document.body.textContent).toMatch(/12(\.0)?%/)
    }, { timeout: 3000 })
  })

  it('TC-FE-CONGESTION-05: clicking "Generate Forecast" submits the form with parsed numeric values', async () => {
    const { congestionApi } = await import('../services/api')
    renderPage()
    await waitFor(() => expect(congestionApi.predict).toHaveBeenCalledTimes(1))

    // The form lives under the "Live Forecast" tab, not the default "Port Overview" tab.
    const liveForecastTab = screen.getByRole('button', { name: /live forecast/i })
    liveForecastTab.click()

    const predictBtn = await screen.findByRole('button', { name: /generate forecast/i })
    predictBtn.click()

    await waitFor(() => expect(congestionApi.predict).toHaveBeenCalledTimes(2))
    // Form values must be parsed to numbers, not sent as raw strings
    const lastCallArg = congestionApi.predict.mock.calls.at(-1)[0]
    expect(typeof lastCallArg.loa_m).toBe('number')
    expect(Number.isNaN(lastCallArg.loa_m)).toBe(false)
  })
})
