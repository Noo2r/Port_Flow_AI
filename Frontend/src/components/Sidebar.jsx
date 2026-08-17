import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navGroups = [
  {
    label: 'Operations',
    accent: '#3b82f6',  // blue
    items: [
      { to: '/dashboard',     icon: 'fa-gauge-high',    label: 'Dashboard',          color: '#60a5fa' },
      { to: '/maritime-map', icon: 'fa-map-location-dot', label: 'Live Maritime Map',  color: '#38bdf8' },
      { to: '/vessels',      icon: 'fa-ship',           label: 'Vessel Management',  color: '#60a5fa' },
      { to: '/berth',     icon: 'fa-warehouse',       label: 'Berth Allocation',   color: '#60a5fa' },
      { to: '/cargo',     icon: 'fa-clipboard-list',  label: 'Cargo & Work Orders',color: '#60a5fa' },
    ],
  },
  {
    label: 'Intelligence',
    accent: '#06b6d4',  // cyan
    items: [
      { to: '/chat',         icon: 'fa-comments',     label: 'AI Assistant',       color: '#a78bfa' },
      { to: '/analytics',    icon: 'fa-chart-column', label: 'Analytics',          color: '#22d3ee' },
      {
        to: '/predictions', icon: 'fa-brain', label: 'ETA Prediction', color: '#a78bfa',
        children: [
          { to: '/evaluation', icon: 'fa-flask', label: 'Model Evaluation', color: '#f59e0b' },
        ],
      },
      { to: '/port-ops',     icon: 'fa-anchor',       label: 'Port Operations',    color: '#22d3ee' },
      { to: '/congestion',   icon: 'fa-water',        label: 'Congestion Forecast', color: '#f97316' },
      { to: '/notifications',icon: 'fa-bell',         label: 'Alerts',             color: '#fbbf24' },
    ],
  },
  {
    label: 'System',
    accent: '#6b7280',  // gray
    items: [
      { to: '/admin', icon: 'fa-gear', label: 'Administration', color: '#8899bb' },
    ],
  },
]

/** Returns true for roles that belong to the TECHNICAL bucket. */
function isTechnicalRole(role) {
  return role === 'admin' || role === 'port_manager' || role === 'analyst'
}

export default function Sidebar() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const initials = (user?.full_name || user?.email || 'U')
    .split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)

  return (
    <div className="w-60 flex flex-col flex-shrink-0 select-none"
      style={{ background: '#030710', borderRight: '1px solid rgba(148,163,184,0.07)' }}>

      {/* ── Brand ── */}
      <div className="px-5 py-5" style={{ borderBottom: '1px solid rgba(148,163,184,0.07)' }}>
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 relative"
            style={{
              background: 'linear-gradient(135deg, #1d4ed8 0%, #0891b2 100%)',
              boxShadow: '0 0 20px rgba(29,78,216,0.5), inset 0 1px 0 rgba(255,255,255,0.15)',
            }}>
            <i className="fa-solid fa-anchor text-white text-sm" />
          </div>
          <div>
            <h1 className="text-sm font-bold tracking-tight text-white">PortFlow AI</h1>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <p className="text-[10px]" style={{ color: '#2a3f66' }}>Port Operations DSS</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── Nav ── */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto space-y-5">
        {navGroups.map(group => {
          // Filter items by role bucket:
          //   /admin            → admin only (unchanged)
          //   /analytics        → technical bucket only (admin, port_manager, analyst)
          //   /evaluation child → technical bucket only (hidden via parent's children filter below)
          const technical = isTechnicalRole(user?.role)
          const visibleItems = group.items
            .filter(item =>
              item.to !== '/admin' || user?.role === 'admin'
            )
            .filter(item =>
              item.to !== '/analytics' || technical
            )
            .map(item => {
              // Strip the Model Evaluation child from /predictions for non-technical roles
              if (item.children && !technical) {
                return { ...item, children: item.children.filter(c => c.to !== '/evaluation') }
              }
              return item
            })
          if (visibleItems.length === 0) return null
          return (
          <div key={group.label}>
            <div className="flex items-center gap-2 px-2 mb-2">
              <div className="flex-1 h-px" style={{ background: `linear-gradient(90deg, ${group.accent}33, transparent)` }} />
              <p className="text-[10px] font-bold uppercase tracking-widest" style={{ color: group.accent + '99' }}>
                {group.label}
              </p>
            </div>
            <ul className="space-y-0.5">
              {visibleItems.map(({ to, icon, label, color, children }) => (
                <li key={to}>
                  <NavLink to={to}>
                    {({ isActive }) => (
                      <div
                        className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm cursor-pointer transition-all duration-150"
                        style={isActive ? {
                          background: `${color}18`,
                          border: `1px solid ${color}30`,
                          color: color,
                          fontWeight: 600,
                        } : {
                          background: 'transparent',
                          border: '1px solid transparent',
                          color: '#2a3f66',
                        }}
                        onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = `${color}0d`; e.currentTarget.style.color = '#8899bb' }}}
                        onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#2a3f66' }}}
                      >
                        <i className={`fa-solid ${icon} w-4 text-center text-sm flex-shrink-0`}
                          style={{ color: isActive ? color : '#1e2e4a', filter: isActive ? `drop-shadow(0 0 4px ${color}99)` : 'none' }} />
                        <span className="flex-1">{label}</span>
                        {isActive && (
                          <span className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                            style={{ background: color, boxShadow: `0 0 6px ${color}` }} />
                        )}
                      </div>
                    )}
                  </NavLink>
                  {children?.length > 0 && (
                    <ul className="mt-0.5 space-y-0.5 ml-3 pl-3" style={{ borderLeft: '1px solid rgba(148,163,184,0.1)' }}>
                      {children.map(child => (
                        <li key={child.to}>
                          <NavLink to={child.to}>
                            {({ isActive }) => (
                              <div
                                className="flex items-center gap-2.5 px-2 py-2 rounded-lg text-xs cursor-pointer transition-all duration-150"
                                style={isActive ? {
                                  background: `${child.color}18`,
                                  border: `1px solid ${child.color}30`,
                                  color: child.color,
                                  fontWeight: 600,
                                } : {
                                  background: 'transparent',
                                  border: '1px solid transparent',
                                  color: '#2a3f66',
                                }}
                                onMouseEnter={e => { if (!isActive) { e.currentTarget.style.background = `${child.color}0d`; e.currentTarget.style.color = '#8899bb' }}}
                                onMouseLeave={e => { if (!isActive) { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#2a3f66' }}}
                              >
                                <i className={`fa-solid ${child.icon} w-3.5 text-center flex-shrink-0`}
                                  style={{ color: isActive ? child.color : '#1e2e4a', filter: isActive ? `drop-shadow(0 0 4px ${child.color}99)` : 'none' }} />
                                <span className="flex-1">{child.label}</span>
                                {isActive && (
                                  <span className="w-1 h-1 rounded-full flex-shrink-0"
                                    style={{ background: child.color, boxShadow: `0 0 4px ${child.color}` }} />
                                )}
                              </div>
                            )}
                          </NavLink>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          </div>
          )
        })}
      </nav>

      {/* ── User footer ── */}
      <div className="px-3 py-4" style={{ borderTop: '1px solid rgba(148,163,184,0.07)' }}>
        <div className="flex items-center gap-3 px-2">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold flex-shrink-0"
            style={{
              background: 'linear-gradient(135deg, #1d4ed8, #0891b2)',
              boxShadow: '0 0 12px rgba(29,78,216,0.4)',
            }}>
            {initials}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold truncate" style={{ color: '#ccd9f0' }}>
              {user?.full_name || user?.email || 'Guest'}
            </p>
            <p className="text-[10px] capitalize truncate" style={{ color: '#2a3f66' }}>
              {(user?.role || '').replace(/_/g, ' ') || 'User'}
            </p>
          </div>
          <button
            onClick={handleLogout}
            className="w-7 h-7 flex items-center justify-center rounded-lg transition-all flex-shrink-0"
            style={{ color: '#2a3f66', background: 'transparent' }}
            onMouseEnter={e => { e.currentTarget.style.color = '#fb7185'; e.currentTarget.style.background = 'rgba(239,68,68,0.1)' }}
            onMouseLeave={e => { e.currentTarget.style.color = '#2a3f66'; e.currentTarget.style.background = 'transparent' }}
            title="Sign out"
          >
            <i className="fa-solid fa-right-from-bracket text-xs" />
          </button>
        </div>
      </div>

    </div>
  )
}
