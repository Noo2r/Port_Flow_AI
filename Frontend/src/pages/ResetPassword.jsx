import { useState, useRef, useEffect } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { authApi } from '../services/api'

export default function ResetPassword() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token')

  const [showPw,  setShowPw]  = useState(false)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState('')
  const [success, setSuccess] = useState(false)

  const passRef    = useRef()
  const confirmRef = useRef()

  useEffect(() => {
    if (!token) setError('No reset token found. Please request a new password reset link.')
  }, [token])

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    const password = passRef.current.value
    const confirm  = confirmRef.current.value

    if (password !== confirm)    { setError('Passwords do not match.'); return }
    if (password.length < 8)     { setError('Password must be at least 8 characters.'); return }
    if (!/[A-Z]/.test(password)) { setError('Password must contain at least one uppercase letter.'); return }
    if (!/\d/.test(password))    { setError('Password must contain at least one digit.'); return }

    setLoading(true)
    try {
      await authApi.resetPassword(token, password)
      setSuccess(true)
      setTimeout(() => navigate('/login'), 3000)
    } catch (err) {
      setError(err.message || 'Reset failed. The link may have expired — please request a new one.')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    background: '#111e38',
    border: '1px solid #1e3460',
    color: '#e2e8f0',
    borderRadius: '0.5rem',
    padding: '0.75rem 1rem 0.75rem 2.5rem',
    width: '100%',
    fontSize: '0.875rem',
    outline: 'none',
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#050a14' }}>
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center"
            style={{ background: 'linear-gradient(135deg, #1d4ed8, #0891b2)', boxShadow: '0 0 24px rgba(29,78,216,0.4)' }}>
            <i className="fa-solid fa-anchor text-white text-lg" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white">PortFlow AI</h1>
            <p className="text-xs" style={{ color: '#3d5177' }}>Decision Support System</p>
          </div>
        </div>

        <div className="rounded-2xl p-8" style={{ background: '#0d1526', border: '1px solid #1e3460' }}>

          {success ? (
            <div className="text-center py-4">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
                style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.3)' }}>
                <i className="fa-solid fa-circle-check text-xl" style={{ color: '#34d399' }} />
              </div>
              <h2 className="text-xl font-bold text-white mb-2">Password Reset</h2>
              <p className="text-sm" style={{ color: '#5a6e8d' }}>
                Your password has been updated. Redirecting you to sign in…
              </p>
            </div>
          ) : (
            <>
              <div className="mb-6">
                <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-4"
                  style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
                  <i className="fa-solid fa-key text-lg" style={{ color: '#60a5fa' }} />
                </div>
                <h2 className="text-2xl font-bold text-white mb-1">Set New Password</h2>
                <p className="text-sm" style={{ color: '#3d5177' }}>
                  Choose a strong password for your PortFlow AI account.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">

                {/* New Password */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: '#3d5177' }}>
                    New Password
                  </label>
                  <div className="relative">
                    <i className="fa-solid fa-lock absolute left-3 top-1/2 -translate-y-1/2 text-xs pointer-events-none"
                      style={{ color: '#3d5177' }} />
                    <input ref={passRef} type={showPw ? 'text' : 'password'} required
                      placeholder="Min 8 chars, 1 uppercase, 1 digit"
                      disabled={!token}
                      style={{ ...inputStyle, paddingRight: '2.5rem' }}
                      onFocus={e => e.target.style.borderColor = 'rgba(59,130,246,0.6)'}
                      onBlur={e => e.target.style.borderColor = '#1e3460'} />
                    <button type="button" onClick={() => setShowPw(p => !p)}
                      className="absolute right-3 top-1/2 -translate-y-1/2"
                      style={{ color: '#3d5177' }}>
                      <i className={`fa-solid ${showPw ? 'fa-eye-slash' : 'fa-eye'} text-xs`} />
                    </button>
                  </div>
                </div>

                {/* Confirm Password */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: '#3d5177' }}>
                    Confirm Password
                  </label>
                  <div className="relative">
                    <i className="fa-solid fa-lock absolute left-3 top-1/2 -translate-y-1/2 text-xs pointer-events-none"
                      style={{ color: '#3d5177' }} />
                    <input ref={confirmRef} type={showPw ? 'text' : 'password'} required
                      placeholder="Repeat your new password"
                      disabled={!token}
                      style={inputStyle}
                      onFocus={e => e.target.style.borderColor = 'rgba(59,130,246,0.6)'}
                      onBlur={e => e.target.style.borderColor = '#1e3460'} />
                  </div>
                </div>

                {/* Error */}
                {error && (
                  <div className="p-3 rounded-xl flex items-start gap-2 text-sm"
                    style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#f87171' }}>
                    <i className="fa-solid fa-circle-exclamation flex-shrink-0 mt-0.5" />
                    <span>{error}</span>
                  </div>
                )}

                <button type="submit" disabled={loading || !token}
                  className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl font-semibold text-sm text-white transition-all disabled:opacity-50"
                  style={{
                    background: 'linear-gradient(135deg, #1d4ed8 0%, #0891b2 100%)',
                    border: '1px solid rgba(59,130,246,0.3)',
                    boxShadow: '0 0 20px rgba(29,78,216,0.3)',
                  }}>
                  {loading
                    ? <><i className="fa-solid fa-spinner fa-spin" /> Resetting…</>
                    : <><i className="fa-solid fa-shield-check" /> Reset Password</>}
                </button>
              </form>
            </>
          )}

          <p className="mt-5 text-center text-xs" style={{ color: '#3d5177' }}>
            <Link to="/login" style={{ color: '#3b82f6' }}>
              <i className="fa-solid fa-arrow-left mr-1" />Back to Sign In
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
