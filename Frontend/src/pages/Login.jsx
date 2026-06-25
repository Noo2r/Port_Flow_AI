import { useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { authApi } from '../services/api'

const features = [
  { icon: 'fa-chart-line', title: 'Real-time Analytics',  desc: 'Monitor vessel traffic, berth utilization, and cargo throughput' },
  { icon: 'fa-brain',      title: 'AI-Powered Insights',  desc: 'Predictive analytics for optimal resource allocation' },
  { icon: 'fa-shield-alt', title: 'Enterprise Security',  desc: 'Role-based access control and data protection' },
]

export default function Login() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [showPw, setShowPw] = useState(false)
  const [showForgot, setShowForgot] = useState(false)
  const [loading, setLoading] = useState(false)
  const [loginError, setLoginError] = useState('')
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotStatus, setForgotStatus] = useState('')
  const emailRef = useRef()
  const passwordRef = useRef()

  async function handleSubmit(e) {
    e.preventDefault()
    setLoginError('')
    const email = emailRef.current.value.trim()
    const password = passwordRef.current.value
    if (!email || !password) { setLoginError('Please enter your email and password.'); return }
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setLoginError(err.message || 'Login failed. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  async function handleForgot() {
    if (!forgotEmail) { setForgotStatus('Please enter your email.'); return }
    setForgotStatus('Sending...')
    try {
      await authApi.forgotPassword(forgotEmail)
      setForgotStatus('Reset link sent! Check your inbox.')
    } catch (err) {
      setForgotStatus(err.message || 'Failed to send reset link.')
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
    transition: 'border-color 0.15s',
  }

  return (
    <div className="min-h-screen flex" style={{ background: '#050a14' }}>

      {/* ── Left: Branding panel ── */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden flex-col justify-center px-12 py-16"
        style={{ background: 'linear-gradient(160deg, #060b17 0%, #0a1020 40%, #0d1526 100%)', borderRight: '1px solid #1a2a4a' }}>

        {/* Decorative rings */}
        <div className="absolute top-16 right-16 w-48 h-48 rounded-full pointer-events-none"
          style={{ border: '1px solid rgba(59,130,246,0.08)' }} />
        <div className="absolute top-32 right-32 w-32 h-32 rounded-full pointer-events-none"
          style={{ border: '1px solid rgba(59,130,246,0.06)' }} />
        <div className="absolute bottom-24 right-20 w-64 h-64 rounded-full pointer-events-none"
          style={{ border: '1px solid rgba(6,182,212,0.06)' }} />
        {/* Glow blobs */}
        <div className="absolute top-1/4 right-1/4 w-64 h-64 rounded-full pointer-events-none"
          style={{ background: 'radial-gradient(circle, rgba(29,78,216,0.08) 0%, transparent 70%)' }} />
        <div className="absolute bottom-1/3 right-1/3 w-48 h-48 rounded-full pointer-events-none"
          style={{ background: 'radial-gradient(circle, rgba(6,182,212,0.06) 0%, transparent 70%)' }} />

        {/* Brand */}
        <div className="relative z-10">
          <div className="flex items-center gap-4 mb-10">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #1d4ed8 0%, #0891b2 100%)', boxShadow: '0 0 30px rgba(29,78,216,0.4)' }}>
              <i className="fa-solid fa-anchor text-white text-xl" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white tracking-tight">PortFlow AI</h1>
              <p className="text-sm" style={{ color: '#3d5177' }}>Decision Support System</p>
            </div>
          </div>

          <h2 className="text-4xl font-bold text-white mb-3 leading-tight">
            Intelligent Port<br />Operations
          </h2>
          <p className="text-base mb-12" style={{ color: '#5a6e8d', lineHeight: 1.7 }}>
            AI-powered insights and real-time decision support for modern maritime operations.
          </p>

          <div className="space-y-5">
            {features.map(f => (
              <div key={f.icon} className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5"
                  style={{ background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.2)' }}>
                  <i className={`fa-solid ${f.icon} text-sm`} style={{ color: '#60a5fa' }} />
                </div>
                <div>
                  <h3 className="font-semibold text-sm text-white mb-0.5">{f.title}</h3>
                  <p className="text-sm" style={{ color: '#3d5177' }}>{f.desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Divider */}
          <div className="mt-12 flex items-center gap-3">
            <div className="flex-1 h-px" style={{ background: '#1a2a4a' }} />
            <span className="text-xs" style={{ color: '#2a3a55' }}>Stage-2 Berth Optimizer · CatBoost ETA · 96 berths</span>
            <div className="flex-1 h-px" style={{ background: '#1a2a4a' }} />
          </div>
        </div>
      </div>

      {/* ── Right: Login form ── */}
      <div className="flex-1 flex flex-col justify-center px-8 py-12 lg:px-16 overflow-y-auto">
        <div className="w-full max-w-md mx-auto">

          {/* Mobile logo */}
          <div className="lg:hidden mb-8 flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #1d4ed8, #0891b2)', boxShadow: '0 0 20px rgba(29,78,216,0.35)' }}>
              <i className="fa-solid fa-anchor text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">PortFlow AI</h1>
              <p className="text-xs" style={{ color: '#3d5177' }}>Decision Support System</p>
            </div>
          </div>

          <h2 className="text-3xl font-bold text-white mb-1">Welcome back</h2>
          <p className="text-sm mb-8" style={{ color: '#3d5177' }}>Sign in to access the PortFlow AI system</p>

          <form onSubmit={handleSubmit} className="space-y-5">

            {/* Email */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: '#3d5177' }}>
                Email
              </label>
              <div className="relative">
                <i className="fa-solid fa-envelope absolute left-3 top-1/2 -translate-y-1/2 text-xs pointer-events-none"
                  style={{ color: '#3d5177' }} />
                <input ref={emailRef} type="email" required placeholder="Enter your email"
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'rgba(59,130,246,0.6)'}
                  onBlur={e => e.target.style.borderColor = '#1e3460'} />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: '#3d5177' }}>
                Password
              </label>
              <div className="relative">
                <i className="fa-solid fa-lock absolute left-3 top-1/2 -translate-y-1/2 text-xs pointer-events-none"
                  style={{ color: '#3d5177' }} />
                <input ref={passwordRef} type={showPw ? 'text' : 'password'} required placeholder="Enter your password"
                  style={{ ...inputStyle, paddingRight: '2.5rem' }}
                  onFocus={e => e.target.style.borderColor = 'rgba(59,130,246,0.6)'}
                  onBlur={e => e.target.style.borderColor = '#1e3460'} />
                <button type="button" onClick={() => setShowPw(p => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 transition-colors"
                  style={{ color: '#3d5177' }}
                  onMouseEnter={e => e.currentTarget.style.color = '#60a5fa'}
                  onMouseLeave={e => e.currentTarget.style.color = '#3d5177'}>
                  <i className={`fa-solid ${showPw ? 'fa-eye-slash' : 'fa-eye'} text-xs`} />
                </button>
              </div>
            </div>

            {/* Error */}
            {loginError && (
              <div className="p-3 rounded-xl flex items-center gap-2 text-sm"
                style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#f87171' }}>
                <i className="fa-solid fa-circle-exclamation flex-shrink-0" />
                {loginError}
              </div>
            )}

            {/* Remember / Forgot */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm cursor-pointer" style={{ color: '#5a6e8d' }}>
                <input type="checkbox"
                  style={{ accentColor: '#3b82f6' }} />
                Remember me
              </label>
              <button type="button" onClick={() => setShowForgot(true)}
                className="text-sm font-medium transition-colors"
                style={{ color: '#3b82f6' }}
                onMouseEnter={e => e.currentTarget.style.color = '#60a5fa'}
                onMouseLeave={e => e.currentTarget.style.color = '#3b82f6'}>
                Forgot password?
              </button>
            </div>

            {/* Submit */}
            <button type="submit" disabled={loading}
              className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl font-semibold text-sm text-white transition-all disabled:opacity-50"
              style={{
                background: loading ? '#162445' : 'linear-gradient(135deg, #1d4ed8 0%, #0891b2 100%)',
                border: '1px solid rgba(59,130,246,0.3)',
                boxShadow: loading ? 'none' : '0 0 20px rgba(29,78,216,0.3)',
              }}>
              {loading
                ? <><i className="fa-solid fa-spinner fa-spin" /> Signing In…</>
                : <><i className="fa-solid fa-sign-in-alt" /> Sign In</>}
            </button>
          </form>

          {/* Register link */}
          <p className="mt-6 text-center text-sm" style={{ color: '#3d5177' }}>
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold transition-colors"
              style={{ color: '#3b82f6' }}
              onMouseEnter={e => e.currentTarget.style.color = '#60a5fa'}
              onMouseLeave={e => e.currentTarget.style.color = '#3b82f6'}>
              Create Account
            </Link>
          </p>

          {/* Security notice */}
          <div className="mt-5 p-4 rounded-xl flex items-start gap-3"
            style={{ background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.15)' }}>
            <i className="fa-solid fa-shield-alt text-sm mt-0.5 flex-shrink-0" style={{ color: '#3b82f6' }} />
            <div>
              <h4 className="text-xs font-semibold text-white mb-1">Security Notice</h4>
              <p className="text-xs" style={{ color: '#3d5177', lineHeight: 1.6 }}>
                This system contains confidential port operations data. Access is restricted to authorized personnel only.
              </p>
            </div>
          </div>

          {/* Status */}
          <div className="mt-6 flex items-center justify-center gap-2 text-xs" style={{ color: '#2a3a55' }}>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            System Status: Operational
            <span style={{ color: '#1a2a4a' }}>|</span>
            AI Models: Online
          </div>
        </div>
      </div>

      {/* ── Forgot Password Modal ── */}
      {showForgot && (
        <div className="fixed inset-0 flex items-center justify-center z-50 p-4"
          style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}>
          <div className="w-full max-w-md mx-4 rounded-2xl p-6"
            style={{ background: '#0d1526', border: '1px solid #1e3460', boxShadow: '0 24px 64px rgba(0,0,0,0.75)' }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold text-white">Reset Password</h3>
              <button onClick={() => setShowForgot(false)}
                className="w-7 h-7 flex items-center justify-center rounded-lg transition-all"
                style={{ color: '#3d5177' }}
                onMouseEnter={e => { e.currentTarget.style.color = '#e2e8f0'; e.currentTarget.style.background = '#162445' }}
                onMouseLeave={e => { e.currentTarget.style.color = '#3d5177'; e.currentTarget.style.background = 'transparent' }}>
                <i className="fa-solid fa-times text-sm" />
              </button>
            </div>
            <p className="text-sm mb-4" style={{ color: '#5a6e8d' }}>
              Enter your email and we'll send a link to reset your password.
            </p>
            <div className="space-y-4">
              <input type="email" required placeholder="Enter your email" value={forgotEmail}
                onChange={e => { setForgotEmail(e.target.value); setForgotStatus('') }}
                style={{ ...inputStyle, paddingLeft: '1rem' }} />
              {forgotStatus && (
                <p className="text-sm" style={{ color: forgotStatus.startsWith('Reset') ? '#34d399' : '#f87171' }}>
                  {forgotStatus}
                </p>
              )}
              <div className="flex gap-3">
                <button type="button"
                  onClick={() => { setShowForgot(false); setForgotEmail(''); setForgotStatus('') }}
                  className="flex-1 py-2.5 px-4 rounded-lg text-sm font-medium transition-all"
                  style={{ background: '#111e38', border: '1px solid #1e3460', color: '#94a3b8' }}>
                  Cancel
                </button>
                <button type="button" onClick={handleForgot}
                  className="flex-1 py-2.5 px-4 rounded-lg text-sm font-semibold text-white transition-all"
                  style={{ background: 'linear-gradient(135deg, #1d4ed8, #0891b2)', border: '1px solid rgba(59,130,246,0.3)' }}>
                  Send Reset Link
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
