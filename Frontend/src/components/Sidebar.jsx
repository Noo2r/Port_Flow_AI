import { NavLink, useNavigate } from 'react-router-dom'

const navItems = [
  { to: '/dashboard',      icon: 'fa-chart-line', label: 'Dashboard' },
  { to: '/vessels',        icon: 'fa-ship',        label: 'Vessel Management' },
  { to: '/berth',          icon: 'fa-warehouse',   label: 'Berth Operations' },
  { to: '/cargo',          icon: 'fa-truck',       label: 'Cargo Tracking' },
  { to: '/notifications',  icon: 'fa-bell',        label: 'Alerts & Notifications' },
  { to: '/analytics',      icon: 'fa-chart-bar',   label: 'Analytics' },
  { to: '/admin',          icon: 'fa-cog',         label: 'Settings' },
]

export default function Sidebar() {
  const navigate = useNavigate()

  return (
    <div className="w-64 bg-navy text-white flex flex-col flex-shrink-0">
      {/* Logo */}
      <div className="p-6 border-b border-navy-light">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
            <i className="fa-solid fa-anchor text-white text-lg" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">PortOps DSS</h1>
            <p className="text-xs text-gray-300">Decision Support</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {navItems.map(({ to, icon, label }) => (
            <li key={to}>
              <NavLink
                to={to}
                className={({ isActive }) =>
                  `flex items-center space-x-3 p-3 rounded-lg transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-300 hover:bg-navy-light'
                  }`
                }
              >
                <i className={`fa-solid ${icon} w-4`} />
                <span>{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      {/* User */}
      <div className="p-4 border-t border-navy-light">
        <div className="flex items-center space-x-3">
          <img
            src="https://storage.googleapis.com/uxpilot-auth.appspot.com/avatars/avatar-2.jpg"
            alt="User"
            className="w-8 h-8 rounded-full"
          />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">John Harbor</p>
            <p className="text-xs text-gray-400">Port Manager</p>
          </div>
          <button
            onClick={() => navigate('/login')}
            className="text-gray-400 hover:text-white transition-colors"
            title="Sign out"
          >
            <i className="fa-solid fa-sign-out-alt" />
          </button>
        </div>
      </div>
    </div>
  )
}
