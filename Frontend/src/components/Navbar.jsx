import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Navbar({ title, subtitle, children }) {
  const navigate = useNavigate()
  const [time, setTime] = useState(
    new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  )

  useEffect(() => {
    const id = setInterval(() => {
      setTime(new Date().toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    }, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="flex-shrink-0 px-6 py-3.5"
      style={{
        background: '#030710',
        borderBottom: '1px solid rgba(148,163,184,0.07)',
        boxShadow: '0 1px 0 rgba(59,130,246,0.05)',
      }}>
      <div className="flex items-center justify-between gap-4">

        {/* Left — page title */}
        <div className="min-w-0">
          <h1 className="text-lg font-bold truncate" style={{ color: '#f0f6ff' }}>{title}</h1>
          {subtitle && (
            <p className="text-[11px] mt-0.5 truncate font-mono" style={{ color: '#2a3f66' }}>{subtitle}</p>
          )}
        </div>

        {/* Right — actions + utilities */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {children}

          {/* Live clock */}
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl"
            style={{ background: '#080f1e', border: '1px solid rgba(148,163,184,0.09)' }}>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs tabular-nums font-mono" style={{ color: '#3d5a8a' }}>{time}</span>
          </div>

          {/* Notifications bell */}
          <button
            onClick={() => navigate('/notifications')}
            className="relative w-9 h-9 flex items-center justify-center rounded-xl transition-all"
            style={{ background: '#080f1e', border: '1px solid rgba(148,163,184,0.09)', color: '#3d5a8a' }}
            onMouseEnter={e => {
              e.currentTarget.style.color = '#fbbf24'
              e.currentTarget.style.borderColor = 'rgba(245,158,11,0.3)'
              e.currentTarget.style.boxShadow = '0 0 12px rgba(245,158,11,0.15)'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.color = '#3d5a8a'
              e.currentTarget.style.borderColor = 'rgba(148,163,184,0.09)'
              e.currentTarget.style.boxShadow = 'none'
            }}
            title="Notifications"
          >
            <i className="fa-solid fa-bell text-sm" />
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-rose-500 rounded-full"
              style={{ border: '2px solid #030710', boxShadow: '0 0 6px rgba(244,63,94,0.8)' }} />
          </button>
        </div>
      </div>
    </div>
  )
}
