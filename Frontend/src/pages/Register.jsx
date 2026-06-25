import { useState, useRef } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const navigate = useNavigate()
  const { register } = useAuth()

  const [showPw,   setShowPw]   = useState(false)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState('')
  const [success,  setSuccess]  = useState(false)

  const nameRef    = useRef()
  const emailRef   = useRef()
  const passRef    = useRef()
  const confirmRef = useRef()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')

    const name     = nameRef.current.value.trim()
    const email    = emailRef.current.value.trim()
    const password = passRef.current.value
    const confirm  = confirmRef.current.value

    if (password !== confirm) { setError('Passwords do not match.'); return }
    if (password.length < 8)  { setError('Password must be at least 8 characters.'); return }
    if (!/[A-Z]/.test(password)) { setError('Password must contain at least one uppercase letter.'); return }
    if (!/\d/.test(password))    { setError('Password must contain at least one digit.'); return }

    setLoading(true)
    try {
      await register(name, email, password)
      setSuccess(true)
    } catch (err) {
      setError(err.message || 'Registration failed. Please try again.')
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

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#050a14' }}>
        <div className="w-full max-w-md mx-auto px-8 text-center">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
            style={{ background: 'rgba(52,211,153,0.1)', border: '1px solid rgba(52,211,153,0.3)' }}>
            <i className="fa-solid fa-circle-check text-2xl" style={{ color: '#34d399' }} />
          </div>
          <h2 className="text-2xl font-bold text-white mb-3">Account Created</h2>
          <p className="text-sm mb-2" style={{ color: '#5a6e8d', lineHeight: 1.7 }}>
            Your account has been created with <strong style={{ color: '#94a3b8' }}>Read Only</strong> access.
          </p>
          <p className="text-sm mb-8" style={{ color: '#5a6e8d', lineHeight: 1.7 }}>
            Contact a PortFlow administrator to have your role upgraded so you can access operational features.
          </p>
          <button
            onClick={() => navigate('/login')}
            className="w-full py-3 px-4 rounded-xl font-semibold text-sm text-white"
            style={{
              background: 'linear-gradient(135deg, #1d4ed8 0%, #0891b2 100%)',
              border: '1px solid rgba(59,130,246,0.3)',
            }}>
            <i className="fa-solid fa-sign-in-alt mr-2" />Go to Sign In
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex" style={{ background: '#050a14' }}>

      {/* ── Left: Branding panel ── */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden flex-col justify-center px-12 py-16"
        style={{ background: 'linear-gradient(160deg, #060b17 0%, #0a1020 40%, #0d1526 100%)', borderRight: '1px solid #1a2a4a' }}>

        <div className="absolute top-16 right-16 w-48 h-48 rounded-full pointer-events-none"
          style={{ border: '1px solid rgba(59,130,246,0.08)' }} />
        <div className="absolute top-32 right-32 w-32 h-32 rounded-full pointer-events-none"
          style={{ border: '1px solid rgba(59,130,246,0.06)' }} />
        <div className="absolute bottom-24 right-20 w-64 h-64 rounded-full pointer-events-none"
          style={{ border: '1px solid rgba(6,182,212,0.06)' }} />
        <div className="absolute top-1/4 right-1/4 w-64 h-64 rounded-full pointer-events-none"
          style={{ background: 'radial-gradient(circle, rgba(29,78,216,0.08) 0%, transparent 70%)' }} />

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
            Join the<br />Port Network
          </h2>
          <p className="text-base mb-10" style={{ color: '#5a6e8d', lineHeight: 1.7 }}>
            Create your account to request access to PortFlow AI. An administrator will assign your operational role.
          </p>

          <div className="p-5 rounded-2xl" style={{ background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.12)' }}>
            <div className="flex items-start gap-3 mb-4">
              <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: 'rgba(59,130,246,0.15)' }}>
                <i className="fa-solid fa-id-badge text-xs" style={{ color: '#60a5fa' }} />
              </div>
              <div>
                <p className="text-sm font-semibold text-white mb-1">Available Roles</p>
                <p className="text-xs" style={{ color: '#3d5177' }}>Assigned by administrator after account creation</p>
              </div>
            </div>
            <div className="space-y-2">
              {[
                { role: 'Port Manager',   desc: 'Full operational access' },
                { role: 'Vessel Agent',   desc: 'Vessel & voyage management' },
                { role: 'Operations',     desc: 'Berth & cargo operations' },
                { role: 'Analyst',        desc: 'Analytics & AI predictions' },
                { role: 'Read Only',      desc: 'View-only access (default)' },
              ].map(r => (
                <div key={r.role} className="flex items-center justify-between">
                  <span className="text-xs font-medium" style={{ color: '#94a3b8' }}>{r.role}</span>
                  <span className="text-xs" style={{ color: '#3d5177' }}>{r.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Right: Register form ── */}
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

          <h2 className="text-3xl font-bold text-white mb-1">Create Account</h2>
          <p className="text-sm mb-8" style={{ color: '#3d5177' }}>
            Request access to the PortFlow AI system
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Full Name */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: '#3d5177' }}>
                Full Name
              </label>
              <div className="relative">
                <i className="fa-solid fa-user absolute left-3 top-1/2 -translate-y-1/2 text-xs pointer-events-none"
                  style={{ color: '#3d5177' }} />
                <input ref={nameRef} type="text" required minLength={2} placeholder="Your full name"
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'rgba(59,130,246,0.6)'}
                  onBlur={e => e.target.style.borderColor = '#1e3460'} />
              </div>
            </div>

            {/* Email */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: '#3d5177' }}>
                Email
              </label>
              <div className="relative">
                <i className="fa-solid fa-envelope absolute left-3 top-1/2 -translate-y-1/2 text-xs pointer-events-none"
                  style={{ color: '#3d5177' }} />
                <input ref={emailRef} type="email" required placeholder="you@example.com"
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
                <input ref={passRef} type={showPw ? 'text' : 'password'} required placeholder="Min 8 chars, 1 uppercase, 1 digit"
                  style={{ ...inputStyle, paddingRight: '2.5rem' }}
                  onFocus={e => e.target.style.borderColor = 'rgba(59,130,246,0.6)'}
                  onBlur={e => e.target.style.borderColor = '#1e3460'} />
                <button type="button" onClick={() => setShowPw(p => !p)}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  style={{ color: '#3d5177' }}
                  onMouseEnter={e => e.currentTarget.style.color = '#60a5fa'}
                  onMouseLeave={e => e.currentTarget.style.color = '#3d5177'}>
                  <i className={`fa-solid ${showPw ? 'fa-eye-slash' : 'fa-eye'} text-xs`} />
                </button>
              </div>
            </div>

            {/* Confirm password */}
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: '#3d5177' }}>
                Confirm Password
              </label>
              <div className="relative">
                <i className="fa-solid fa-lock absolute left-3 top-1/2 -translate-y-1/2 text-xs pointer-events-none"
                  style={{ color: '#3d5177' }} />
                <input ref={confirmRef} type={showPw ? 'text' : 'password'} required placeholder="Repeat your password"
                  style={inputStyle}
                  onFocus={e => e.target.style.borderColor = 'rgba(59,130,246,0.6)'}
                  onBlur={e => e.target.style.borderColor = '#1e3460'} />
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="p-3 rounded-xl flex items-center gap-2 text-sm"
                style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.25)', color: '#f87171' }}>
                <i className="fa-solid fa-circle-exclamation flex-shrink-0" />
                {error}
              </div>
            )}

            {/* Role notice */}
            <div className="p-3 rounded-xl flex items-start gap-2"
              style={{ background: 'rgba(59,130,246,0.06)', border: '1px solid rgba(59,130,246,0.15)' }}>
              <i className="fa-solid fa-circle-info text-xs mt-0.5 flex-shrink-0" style={{ color: '#60a5fa' }} />
              <p className="text-xs" style={{ color: '#5a6e8d', lineHeight: 1.5 }}>
                New accounts start with <strong style={{ color: '#94a3b8' }}>Read Only</strong> access. An administrator will assign your operational role after review.
              </p>
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
                ? <><i className="fa-solid fa-spinner fa-spin" /> Creating Account…</>
                : <><i className="fa-solid fa-user-plus" /> Create Account</>}
            </button>
          </form>

          <p className="mt-6 text-center text-sm" style={{ color: '#3d5177' }}>
            Already have an account?{' '}
            <Link to="/login" className="font-semibold transition-colors"
              style={{ color: '#3b82f6' }}
              onMouseEnter={e => e.currentTarget.style.color = '#60a5fa'}
              onMouseLeave={e => e.currentTarget.style.color = '#3b82f6'}>
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
