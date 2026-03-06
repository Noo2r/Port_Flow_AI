import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const roles = [
  { value: 'port_authority',   icon: 'fa-building',      label: 'Port Authority',    sub: 'Operations oversight' },
  { value: 'terminal_operator',icon: 'fa-warehouse',     label: 'Terminal Operator', sub: 'Terminal management' },
  { value: 'berth_planner',    icon: 'fa-calendar-alt',  label: 'Berth Planner',     sub: 'Scheduling & planning' },
  { value: 'shipping_agent',   icon: 'fa-ship',          label: 'Shipping Agent',    sub: 'Vessel coordination' },
]

export default function Login() {
  const navigate = useNavigate()
  const [selectedRole, setSelectedRole] = useState('')
  const [showPw, setShowPw] = useState(false)
  const [showForgot, setShowForgot] = useState(false)
  const [loading, setLoading] = useState(false)

  function handleSubmit(e) {
    e.preventDefault()
    if (!selectedRole) { alert('Please select your role before signing in.'); return }
    setLoading(true)
    setTimeout(() => navigate('/dashboard'), 1500)
  }

  return (
    <div className="min-h-screen flex">
      {/* Left – Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-navy relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-navy to-navy-dark" />
        {/* Decorative circles */}
        <div className="absolute top-20 right-20 w-32 h-32 border border-blue-400/20 rounded-full" />
        <div className="absolute bottom-20 right-32 w-24 h-24 border border-blue-400/20 rounded-full" />
        <div className="absolute top-1/2 right-10 w-16 h-16 border border-blue-400/20 rounded-full" />

        <div className="relative z-10 flex flex-col justify-center px-12 py-16">
          <div className="flex items-center space-x-4 mb-8">
            <div className="w-16 h-16 bg-blue-600 rounded-xl flex items-center justify-center">
              <i className="fa-solid fa-anchor text-white text-2xl" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">PortFlow AI</h1>
              <p className="text-blue-200 text-lg">Decision Support System</p>
            </div>
          </div>
          <h2 className="text-4xl font-bold text-white mb-4">Intelligent Port Operations Management</h2>
          <p className="text-xl text-blue-200 mb-10">Streamline your maritime operations with AI-powered insights and real-time decision support.</p>

          <div className="space-y-6">
            {[
              { icon: 'fa-chart-line', title: 'Real-time Analytics',  desc: 'Monitor vessel traffic, berth utilization, and cargo throughput' },
              { icon: 'fa-brain',      title: 'AI-Powered Insights',  desc: 'Predictive analytics for optimal resource allocation' },
              { icon: 'fa-shield-alt', title: 'Enterprise Security',  desc: 'Role-based access control and data protection' },
            ].map(f => (
              <div key={f.icon} className="flex items-center space-x-4">
                <div className="w-12 h-12 bg-blue-600/30 rounded-lg flex items-center justify-center flex-shrink-0">
                  <i className={`fa-solid ${f.icon} text-blue-200 text-lg`} />
                </div>
                <div>
                  <h3 className="text-white font-semibold">{f.title}</h3>
                  <p className="text-blue-200 text-sm">{f.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right – Form */}
      <div className="flex-1 flex flex-col justify-center px-8 py-12 lg:px-16">
        <div className="w-full max-w-md mx-auto">
          {/* Mobile logo */}
          <div className="lg:hidden mb-8 flex items-center justify-center space-x-3">
            <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center">
              <i className="fa-solid fa-anchor text-white text-lg" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">PortFlow AI</h1>
              <p className="text-gray-600 text-sm">Decision Support System</p>
            </div>
          </div>

          <h2 className="text-3xl font-bold text-gray-900 mb-2">Welcome Back</h2>
          <p className="text-gray-600 mb-8">Please sign in to access the PortFlow AI system</p>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Role selection */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-3">Select Your Role</label>
              <div className="grid grid-cols-2 gap-3">
                {roles.map(r => (
                  <label key={r.value} className="cursor-pointer">
                    <input type="radio" name="role" value={r.value} className="sr-only"
                      onChange={() => setSelectedRole(r.value)} />
                    <div className={`p-4 border-2 rounded-lg transition-all ${selectedRole === r.value ? 'border-blue-600 bg-blue-50' : 'border-gray-200 hover:border-gray-300'}`}>
                      <div className="flex items-center space-x-3">
                        <i className={`fa-solid ${r.icon} ${selectedRole === r.value ? 'text-blue-600' : 'text-gray-500'}`} />
                        <div>
                          <p className="font-medium text-gray-900 text-sm">{r.label}</p>
                          <p className="text-xs text-gray-500">{r.sub}</p>
                        </div>
                      </div>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            {/* Username */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Username or Email</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fa-solid fa-user text-gray-400" />
                </div>
                <input type="text" required placeholder="Enter your username or email"
                  className="block w-full pl-10 pr-3 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent" />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <i className="fa-solid fa-lock text-gray-400" />
                </div>
                <input type={showPw ? 'text' : 'password'} required placeholder="Enter your password"
                  className="block w-full pl-10 pr-10 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent" />
                <button type="button" onClick={() => setShowPw(p => !p)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600">
                  <i className={`fa-solid ${showPw ? 'fa-eye-slash' : 'fa-eye'}`} />
                </button>
              </div>
            </div>

            {/* Remember / Forgot */}
            <div className="flex items-center justify-between">
              <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input type="checkbox" className="rounded border-gray-300 text-blue-600" />
                Remember me
              </label>
              <button type="button" onClick={() => setShowForgot(true)}
                className="text-sm text-blue-600 hover:text-blue-500 font-medium">
                Forgot password?
              </button>
            </div>

            <button type="submit" disabled={loading}
              className="w-full flex justify-center items-center gap-2 py-3 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium disabled:opacity-60">
              {loading
                ? <><i className="fa-solid fa-spinner fa-spin" /> Signing In...</>
                : <><i className="fa-solid fa-sign-in-alt" /> Sign In</>
              }
            </button>
          </form>

          {/* Security notice */}
          <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-start space-x-3">
              <i className="fa-solid fa-info-circle text-blue-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-sm font-medium text-blue-900">Security Notice</h4>
                <p className="text-sm text-blue-700 mt-1">This system contains confidential port operations data. Access is restricted to authorized personnel only.</p>
              </div>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-center space-x-2 text-sm text-gray-600">
            <div className="w-2 h-2 bg-status-green rounded-full" />
            <span>System Status: Operational</span>
            <span className="text-gray-400">|</span>
            <span>Last Updated: 2 min ago</span>
          </div>
        </div>
      </div>

      {/* Forgot Password Modal */}
      {showForgot && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Reset Password</h3>
              <button onClick={() => setShowForgot(false)} className="text-gray-400 hover:text-gray-600">
                <i className="fa-solid fa-times" />
              </button>
            </div>
            <p className="text-gray-600 mb-4">Enter your email address and we'll send you a link to reset your password.</p>
            <div className="space-y-4">
              <input type="email" required placeholder="Enter your email"
                className="block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600" />
              <div className="flex space-x-3">
                <button onClick={() => setShowForgot(false)}
                  className="flex-1 py-2 px-4 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">Cancel</button>
                <button onClick={() => { alert('Password reset link sent!'); setShowForgot(false) }}
                  className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Send Reset Link</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
