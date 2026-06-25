// ── Premium Midnight UI Component Library ────────────────────────────────────

// Maps Tailwind iconBg class → rich inline style for dark theme
const ICON_BG = {
  'bg-blue-100':    { bg: 'rgba(59,130,246,0.18)',  glow: 'rgba(59,130,246,0.25)',  color: '#60a5fa' },
  'bg-cyan-100':    { bg: 'rgba(6,182,212,0.18)',    glow: 'rgba(6,182,212,0.25)',   color: '#22d3ee' },
  'bg-teal-100':    { bg: 'rgba(20,184,166,0.18)',   glow: 'rgba(20,184,166,0.25)',  color: '#2dd4bf' },
  'bg-green-100':   { bg: 'rgba(16,185,129,0.18)',   glow: 'rgba(16,185,129,0.25)',  color: '#4ade80' },
  'bg-emerald-100': { bg: 'rgba(16,185,129,0.18)',   glow: 'rgba(16,185,129,0.25)',  color: '#34d399' },
  'bg-yellow-100':  { bg: 'rgba(234,179,8,0.18)',    glow: 'rgba(234,179,8,0.25)',   color: '#fde047' },
  'bg-amber-100':   { bg: 'rgba(245,158,11,0.18)',   glow: 'rgba(245,158,11,0.25)',  color: '#fbbf24' },
  'bg-orange-100':  { bg: 'rgba(249,115,22,0.18)',   glow: 'rgba(249,115,22,0.25)',  color: '#fb923c' },
  'bg-red-100':     { bg: 'rgba(239,68,68,0.18)',    glow: 'rgba(239,68,68,0.25)',   color: '#f87171' },
  'bg-rose-100':    { bg: 'rgba(244,63,94,0.18)',    glow: 'rgba(244,63,94,0.25)',   color: '#fb7185' },
  'bg-purple-100':  { bg: 'rgba(168,85,247,0.18)',   glow: 'rgba(168,85,247,0.25)',  color: '#c084fc' },
  'bg-violet-100':  { bg: 'rgba(139,92,246,0.18)',   glow: 'rgba(139,92,246,0.25)',  color: '#a78bfa' },
  'bg-indigo-100':  { bg: 'rgba(99,102,241,0.18)',   glow: 'rgba(99,102,241,0.25)',  color: '#818cf8' },
  'bg-pink-100':    { bg: 'rgba(236,72,153,0.18)',   glow: 'rgba(236,72,153,0.25)',  color: '#f472b6' },
  'bg-fuchsia-100': { bg: 'rgba(217,70,239,0.18)',   glow: 'rgba(217,70,239,0.25)',  color: '#e879f9' },
}

// Maps Tailwind iconColor text class → hex for inline style fallback
const ICON_COLOR = {
  'text-blue-600':    '#60a5fa',
  'text-blue-500':    '#60a5fa',
  'text-cyan-600':    '#22d3ee',
  'text-teal-600':    '#2dd4bf',
  'text-green-600':   '#4ade80',
  'text-green-500':   '#4ade80',
  'text-emerald-600': '#34d399',
  'text-yellow-600':  '#fde047',
  'text-amber-600':   '#fbbf24',
  'text-orange-600':  '#fb923c',
  'text-red-600':     '#f87171',
  'text-rose-600':    '#fb7185',
  'text-purple-600':  '#c084fc',
  'text-violet-600':  '#a78bfa',
  'text-indigo-600':  '#818cf8',
  'text-pink-600':    '#f472b6',
  'text-fuchsia-600': '#e879f9',
  'text-status-green': '#4ade80',
  'text-status-yellow':'#fde047',
  'text-status-red':   '#fb7185',
}

// ─── Badge ────────────────────────────────────────────────────────────────────
export function Badge({ children, variant = 'default' }) {
  const styleMap = {
    default:      { background: 'rgba(148,163,184,0.1)', color: '#8899bb', border: '1px solid rgba(148,163,184,0.15)' },
    green:        { background: 'rgba(16,185,129,0.12)', color: '#4ade80', border: '1px solid rgba(16,185,129,0.3)', textShadow: '0 0 8px rgba(74,222,128,0.4)' },
    yellow:       { background: 'rgba(234,179,8,0.12)',  color: '#fde047', border: '1px solid rgba(234,179,8,0.3)',  textShadow: '0 0 8px rgba(253,224,71,0.4)' },
    red:          { background: 'rgba(239,68,68,0.12)',  color: '#fb7185', border: '1px solid rgba(239,68,68,0.3)',  textShadow: '0 0 8px rgba(251,113,133,0.4)' },
    blue:         { background: 'rgba(59,130,246,0.12)', color: '#60a5fa', border: '1px solid rgba(59,130,246,0.3)', textShadow: '0 0 8px rgba(96,165,250,0.4)' },
    purple:       { background: 'rgba(168,85,247,0.12)', color: '#c084fc', border: '1px solid rgba(168,85,247,0.3)', textShadow: '0 0 8px rgba(192,132,252,0.4)' },
    cyan:         { background: 'rgba(6,182,212,0.12)',  color: '#22d3ee', border: '1px solid rgba(6,182,212,0.3)',  textShadow: '0 0 8px rgba(34,211,238,0.4)' },
    solid_green:  { background: '#059669', color: '#ffffff', border: '1px solid rgba(16,185,129,0.5)' },
    solid_yellow: { background: '#d97706', color: '#ffffff', border: '1px solid rgba(245,158,11,0.5)' },
    solid_gray:   { background: '#334155', color: '#cbd5e1', border: '1px solid rgba(148,163,184,0.2)' },
    solid_red:    { background: '#dc2626', color: '#ffffff', border: '1px solid rgba(239,68,68,0.5)' },
  }
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 text-xs rounded-md font-semibold"
      style={styleMap[variant] || styleMap.default}
    >
      {children}
    </span>
  )
}

// ─── StatusDot ────────────────────────────────────────────────────────────────
export function StatusDot({ status }) {
  const cfg = {
    berthed:     { color: '#4ade80',  glow: '0 0 6px rgba(74,222,128,0.7)' },
    at_sea:      { color: '#60a5fa',  glow: '0 0 6px rgba(96,165,250,0.7)' },
    approaching: { color: '#c084fc',  glow: '0 0 6px rgba(192,132,252,0.7)' },
    anchored:    { color: '#fbbf24',  glow: '0 0 6px rgba(251,191,36,0.7)' },
    departed:    { color: '#475569',  glow: 'none' },
    in_port:     { color: '#4ade80',  glow: '0 0 6px rgba(74,222,128,0.7)' },
    scheduled:   { color: '#60a5fa',  glow: '0 0 6px rgba(96,165,250,0.7)' },
    completed:   { color: '#475569',  glow: 'none' },
  }
  const c = cfg[status] || { color: '#475569', glow: 'none' }
  return (
    <span
      className="inline-block w-2 h-2 rounded-full mr-1.5 flex-shrink-0"
      style={{ background: c.color, boxShadow: c.glow }}
    />
  )
}

// ─── Button ───────────────────────────────────────────────────────────────────
export function Button({ children, variant = 'primary', size = 'md', className = '', style = {}, ...props }) {
  const base = 'inline-flex items-center gap-2 font-semibold rounded-xl transition-all duration-150 focus:outline-none active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed'
  const sizes = { sm: 'px-3 py-1.5 text-xs', md: 'px-4 py-2 text-sm', lg: 'px-5 py-2.5 text-base' }

  const variantStyles = {
    primary: {
      background: 'linear-gradient(135deg, #1d4ed8 0%, #0891b2 100%)',
      color: '#ffffff',
      border: '1px solid rgba(59,130,246,0.4)',
      boxShadow: '0 0 20px rgba(29,78,216,0.3), inset 0 1px 0 rgba(255,255,255,0.1)',
    },
    secondary: {
      background: '#080f1e',
      color: '#8899bb',
      border: '1px solid rgba(148,163,184,0.14)',
      boxShadow: 'none',
    },
    danger: {
      background: 'rgba(239,68,68,0.12)',
      color: '#fb7185',
      border: '1px solid rgba(239,68,68,0.3)',
      boxShadow: '0 0 12px rgba(239,68,68,0.1)',
    },
    ghost: {
      background: 'transparent',
      color: '#3d5a8a',
      border: '1px solid transparent',
    },
    success: {
      background: 'rgba(16,185,129,0.15)',
      color: '#4ade80',
      border: '1px solid rgba(16,185,129,0.3)',
      boxShadow: '0 0 12px rgba(16,185,129,0.1)',
    },
  }

  return (
    <button
      className={`${base} ${sizes[size]} ${className}`}
      style={{ ...variantStyles[variant], ...style }}
      {...props}
    >
      {children}
    </button>
  )
}

// ─── Input ────────────────────────────────────────────────────────────────────
export function Input({ icon, className = '', style = {}, ...props }) {
  return (
    <div className="relative">
      {icon && (
        <i className={`fa-solid ${icon} absolute left-3 top-1/2 -translate-y-1/2 text-xs pointer-events-none`}
          style={{ color: '#2a3f66' }} />
      )}
      <input
        className={`rounded-xl py-2 text-sm transition-all ${icon ? 'pl-8 pr-4' : 'px-4'} ${className}`}
        style={{
          background: '#080f1e',
          border: '1px solid rgba(148,163,184,0.14)',
          color: '#ccd9f0',
          ...style,
        }}
        {...props}
      />
    </div>
  )
}

// ─── Select ───────────────────────────────────────────────────────────────────
export function Select({ options = [], className = '', style = {}, ...props }) {
  return (
    <select
      className={`rounded-xl px-3 py-2 text-sm transition-all ${className}`}
      style={{
        background: '#080f1e',
        border: '1px solid rgba(148,163,184,0.14)',
        color: '#ccd9f0',
        ...style,
      }}
      {...props}
    >
      {options.map(o => (
        <option key={o.value ?? o} value={o.value ?? o}
          style={{ background: '#080f1e', color: '#ccd9f0' }}>
          {o.label ?? o}
        </option>
      ))}
    </select>
  )
}

// ─── CardContainer ────────────────────────────────────────────────────────────
export function CardContainer({ children, className = '', style = {}, accent }) {
  // accent: 'blue' | 'cyan' | 'green' | 'amber' | 'purple' | 'red'
  const accentMap = {
    blue:   'rgba(59,130,246,0.6)',
    cyan:   'rgba(6,182,212,0.6)',
    green:  'rgba(16,185,129,0.6)',
    emerald:'rgba(16,185,129,0.6)',
    amber:  'rgba(245,158,11,0.6)',
    red:    'rgba(239,68,68,0.6)',
    purple: 'rgba(168,85,247,0.6)',
    violet: 'rgba(139,92,246,0.6)',
    rose:   'rgba(244,63,94,0.6)',
  }
  const topBorder = accent ? `linear-gradient(90deg, ${accentMap[accent] || accentMap.blue}, transparent)` : null

  return (
    <div
      className={`rounded-xl overflow-hidden ${className}`}
      style={{
        background: '#080f1e',
        border: '1px solid rgba(148,163,184,0.09)',
        boxShadow: '0 2px 12px rgba(0,0,0,0.5)',
        ...style,
      }}
    >
      {topBorder && (
        <div style={{ height: '2px', background: topBorder }} />
      )}
      {children}
    </div>
  )
}

// ─── StatCard — premium with glowing icon ─────────────────────────────────────
export function StatCard({ label, value, sub, subColor, icon, iconBg, iconColor }) {
  const bgCfg = ICON_BG[iconBg] || { bg: 'rgba(59,130,246,0.15)', glow: 'rgba(59,130,246,0.2)', color: '#60a5fa' }
  const textColor = ICON_COLOR[iconColor] || bgCfg.color

  return (
    <div
      className="rounded-xl p-5 flex items-start gap-4 relative overflow-hidden"
      style={{
        background: '#080f1e',
        border: '1px solid rgba(148,163,184,0.09)',
        boxShadow: '0 2px 12px rgba(0,0,0,0.5)',
      }}
    >
      {/* Icon */}
      <div
        className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0 relative"
        style={{
          background: bgCfg.bg,
          boxShadow: `0 0 20px ${bgCfg.glow}, inset 0 0 0 1px rgba(255,255,255,0.06)`,
        }}
      >
        <i className={`fa-solid ${icon} text-base`} style={{ color: bgCfg.color }} />
      </div>

      {/* Text */}
      <div className="flex-1 min-w-0 relative">
        <p className="text-xs font-semibold uppercase tracking-widest mb-1" style={{ color: '#3d5a8a' }}>{label}</p>
        <p className="text-2xl font-bold leading-tight" style={{ color: '#f0f6ff' }}>{value}</p>
        {sub && (
          <p className="text-xs mt-1 font-medium" style={{ color: textColor }}>
            {sub}
          </p>
        )}
      </div>
    </div>
  )
}

// ─── SmallStatCard ────────────────────────────────────────────────────────────
export function SmallStatCard({ label, value, icon, iconBg, iconColor }) {
  const bgCfg = ICON_BG[iconBg] || { bg: 'rgba(59,130,246,0.15)', glow: 'rgba(59,130,246,0.2)', color: '#60a5fa' }
  return (
    <CardContainer className="p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs mb-1" style={{ color: '#3d5a8a' }}>{label}</p>
          <p className="text-2xl font-bold" style={{ color: bgCfg.color }}>{value}</p>
        </div>
        <div className="w-11 h-11 rounded-xl flex items-center justify-center"
          style={{ background: bgCfg.bg, boxShadow: `0 0 16px ${bgCfg.glow}` }}>
          <i className={`fa-solid ${icon}`} style={{ color: bgCfg.color }} />
        </div>
      </div>
    </CardContainer>
  )
}

// ─── Modal ────────────────────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children, size = 'md' }) {
  if (!open) return null
  const widths = { sm: 'max-w-sm', md: 'max-w-md', lg: 'max-w-lg', xl: 'max-w-xl', '2xl': 'max-w-2xl' }
  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 p-4"
      style={{ background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(6px)' }}>
      <div className={`w-full ${widths[size] || widths.md} mx-4 rounded-2xl overflow-hidden`}
        style={{
          background: '#080f1e',
          border: '1px solid rgba(148,163,184,0.14)',
          boxShadow: '0 0 0 1px rgba(59,130,246,0.08), 0 32px 72px rgba(0,0,0,0.8)',
        }}>
        {/* Header accent line */}
        <div style={{ height: '2px', background: 'linear-gradient(90deg, rgba(59,130,246,0.7), rgba(6,182,212,0.7), transparent)' }} />
        <div className="flex items-center justify-between px-6 py-4"
          style={{ borderBottom: '1px solid rgba(148,163,184,0.09)' }}>
          <h3 className="font-bold text-base" style={{ color: '#f0f6ff' }}>{title}</h3>
          <button onClick={onClose}
            className="w-7 h-7 flex items-center justify-center rounded-lg transition-all text-xs"
            style={{ color: '#3d5a8a', background: 'transparent' }}
            onMouseEnter={e => { e.currentTarget.style.color = '#f0f6ff'; e.currentTarget.style.background = 'rgba(148,163,184,0.1)' }}
            onMouseLeave={e => { e.currentTarget.style.color = '#3d5a8a'; e.currentTarget.style.background = 'transparent' }}>
            <i className="fa-solid fa-xmark" />
          </button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  )
}

// ─── Tabs ─────────────────────────────────────────────────────────────────────
export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex gap-1 mb-5" style={{ borderBottom: '1px solid rgba(148,163,184,0.09)' }}>
      {tabs.map(t => (
        <button key={t} onClick={() => onChange(t)}
          className="px-4 py-2.5 text-sm font-semibold border-b-2 -mb-px transition-all"
          style={active === t
            ? { borderColor: '#3b82f6', color: '#60a5fa' }
            : { borderColor: 'transparent', color: '#3d5a8a' }}>
          {t}
        </button>
      ))}
    </div>
  )
}

// ─── SectionHeader ────────────────────────────────────────────────────────────
export function SectionHeader({ title, children }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h3 className="font-bold text-sm" style={{ color: '#ccd9f0' }}>{title}</h3>
      <div className="flex items-center gap-2">{children}</div>
    </div>
  )
}

// ─── EmptyState ───────────────────────────────────────────────────────────────
export function EmptyState({ icon = 'fa-inbox', title, subtitle }) {
  return (
    <div className="flex flex-col items-center justify-center py-16">
      <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.15)' }}>
        <i className={`fa-solid ${icon} text-xl`} style={{ color: '#2a3f66' }} />
      </div>
      {title    && <p className="text-sm font-semibold mb-1" style={{ color: '#3d5a8a' }}>{title}</p>}
      {subtitle && <p className="text-xs" style={{ color: '#2a3f66' }}>{subtitle}</p>}
    </div>
  )
}

// ─── LoadingRows — shimmer skeleton ──────────────────────────────────────────
export function LoadingRows({ rows = 4 }) {
  const shimmerStyle = {
    background: 'linear-gradient(90deg, #0c1528 25%, #111d35 50%, #0c1528 75%)',
    backgroundSize: '800px 100%',
    animation: 'shimmer 1.6s infinite',
    borderRadius: '4px',
  }
  return (
    <div className="space-y-3 p-4">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-3 items-center">
          <div style={{ ...shimmerStyle, height: '14px', width: '32px' }} />
          <div style={{ ...shimmerStyle, height: '14px', flex: 1 }} />
          <div style={{ ...shimmerStyle, height: '14px', width: '64px' }} />
          <div style={{ ...shimmerStyle, height: '14px', width: '48px' }} />
        </div>
      ))}
    </div>
  )
}
