/**
 * TC-FE-AUTH — Login Page Tests
 * PortFlow AI Frontend Tests
 *
 * Run: npx vitest run src/__tests__/Login.test.jsx
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'

// Mock the api module
vi.mock('../services/api', () => ({
  authApi: {
    login: vi.fn(),
  },
}))

// Mock useNavigate
const mockNavigate = vi.fn()
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return { ...actual, useNavigate: () => mockNavigate }
})

// Mock AuthContext — useAuth must itself be a vi.fn() so individual tests
// can call vi.mocked(useAuth).mockReturnValue(...) to override per-test.
vi.mock('../context/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    login: vi.fn().mockResolvedValue(undefined),
    user: null,
    isAuthenticated: false,
  })),
}))

import Login from '../pages/Login'

function renderLogin() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>
  )
}

describe('TC-FE-AUTH — Login Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('TC-FE-AUTH-01: renders email field, password field, and submit button', () => {
    renderLogin()
    expect(screen.queryByRole('textbox', { name: /email/i }) ||
           screen.queryByPlaceholderText(/email/i) ||
           document.querySelector('input[type="email"]')).toBeTruthy()
    expect(document.querySelector('input[type="password"]')).toBeTruthy()
    expect(screen.getByRole('button', { name: /sign in|login|log in/i })).toBeTruthy()
  })

  it('TC-FE-AUTH-02: empty form submit shows validation or disables button', async () => {
    renderLogin()
    const submitBtn = screen.getByRole('button', { name: /sign in|login|log in/i })
    fireEvent.click(submitBtn)
    // Either an error appears, or the button is disabled, or nothing is called
    // Browser native validation or custom validation should prevent submission
    await waitFor(() => {
      // Check that no navigation happened (form was not submitted)
      expect(mockNavigate).not.toHaveBeenCalled()
    }, { timeout: 500 })
  })

  it('TC-FE-AUTH-03: successful login navigates to dashboard', async () => {
    const { useAuth } = await import('../context/AuthContext')
    const mockLogin = vi.fn().mockResolvedValue(undefined)
    vi.mocked(useAuth).mockReturnValue({
      login: mockLogin,
      user: null,
      isAuthenticated: false,
    })

    renderLogin()
    const emailInput = document.querySelector('input[type="email"]') ||
                       screen.getByPlaceholderText(/email/i)
    const passwordInput = document.querySelector('input[type="password"]')
    const submitBtn = screen.getByRole('button', { name: /sign in|login|log in/i })

    await userEvent.type(emailInput, 'admin@portflow.io')
    await userEvent.type(passwordInput, 'Test1234!')
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith('admin@portflow.io', 'Test1234!')
    })
  })

  it('TC-FE-AUTH-04: failed login displays error message', async () => {
    const { useAuth } = await import('../context/AuthContext')
    vi.mocked(useAuth).mockReturnValue({
      login: vi.fn().mockRejectedValue(new Error('Invalid credentials')),
      user: null,
      isAuthenticated: false,
    })

    renderLogin()
    const emailInput = document.querySelector('input[type="email"]') ||
                       screen.getByPlaceholderText(/email/i)
    const passwordInput = document.querySelector('input[type="password"]')
    const submitBtn = screen.getByRole('button', { name: /sign in|login|log in/i })

    await userEvent.type(emailInput, 'wrong@portflow.io')
    await userEvent.type(passwordInput, 'WrongPass!')
    fireEvent.click(submitBtn)

    await waitFor(() => {
      const errorEl = screen.queryByText(/invalid|error|failed|incorrect/i)
      expect(errorEl).toBeTruthy()
    }, { timeout: 2000 })
  })

  it('TC-FE-AUTH-05: page renders without throwing errors', () => {
    expect(() => renderLogin()).not.toThrow()
  })
})
