// ─── Badge ────────────────────────────────────────────────────────
export function Badge({ children, variant = 'default' }) {
  const variants = {
    default:    'bg-gray-100 text-gray-700',
    green:      'bg-green-100 text-green-700',
    yellow:     'bg-yellow-100 text-yellow-700',
    red:        'bg-red-100 text-red-600',
    blue:       'bg-blue-100 text-blue-700',
    purple:     'bg-purple-100 text-purple-700',
    solid_green:'bg-status-green text-white',
    solid_yellow:'bg-status-yellow text-white',
    solid_gray: 'bg-gray-400 text-white',
    solid_red:  'bg-status-red text-white',
  }
  return (
    <span className={`px-2 py-1 text-xs rounded-full font-medium ${variants[variant] || variants.default}`}>
      {children}
    </span>
  )
}

// ─── StatusDot ───────────────────────────────────────────────────
export function StatusDot({ status }) {
  const colors = {
    Docked:    'bg-status-green',
    'En Route':'bg-blue-500',
    Anchored:  'bg-status-yellow',
    Delayed:   'bg-status-red',
    Departed:  'bg-gray-400',
  }
  return <span className={`inline-block w-2 h-2 rounded-full ${colors[status] || 'bg-gray-400'} mr-1.5`} />
}

// ─── Button ──────────────────────────────────────────────────────
export function Button({ children, variant = 'primary', size = 'md', className = '', ...props }) {
  const base = 'inline-flex items-center gap-2 font-medium rounded-lg transition-colors focus:outline-none'
  const variants = {
    primary:  'bg-blue-600 text-white hover:bg-blue-700',
    secondary:'border border-gray-300 text-gray-700 hover:bg-gray-50',
    danger:   'bg-red-600 text-white hover:bg-red-700',
    ghost:    'text-gray-600 hover:bg-gray-100',
  }
  const sizes = { sm: 'px-3 py-1.5 text-sm', md: 'px-4 py-2 text-sm', lg: 'px-5 py-2.5 text-base' }
  return (
    <button className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props}>
      {children}
    </button>
  )
}

// ─── Input ───────────────────────────────────────────────────────
export function Input({ icon, className = '', ...props }) {
  return (
    <div className="relative">
      {icon && <i className={`fa-solid ${icon} absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm`} />}
      <input
        className={`border border-gray-300 rounded-lg py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${icon ? 'pl-9 pr-4' : 'px-4'} ${className}`}
        {...props}
      />
    </div>
  )
}

// ─── Select ──────────────────────────────────────────────────────
export function Select({ options = [], className = '', ...props }) {
  return (
    <select className={`border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 ${className}`} {...props}>
      {options.map(o => (
        <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>
      ))}
    </select>
  )
}

// ─── CardContainer ───────────────────────────────────────────────
export function CardContainer({ children, className = '' }) {
  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 ${className}`}>
      {children}
    </div>
  )
}

// ─── StatCard ────────────────────────────────────────────────────
export function StatCard({ label, value, sub, subColor, icon, iconBg, iconColor }) {
  return (
    <CardContainer className="p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          {sub && <p className={`text-xs ${subColor || 'text-gray-500'}`}>{sub}</p>}
        </div>
        <div className={`w-12 h-12 ${iconBg} rounded-lg flex items-center justify-center`}>
          <i className={`fa-solid ${icon} ${iconColor} text-lg`} />
        </div>
      </div>
    </CardContainer>
  )
}

// ─── SmallStatCard ───────────────────────────────────────────────
export function SmallStatCard({ label, value, icon, iconBg, iconColor }) {
  return (
    <CardContainer className="p-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-600 mb-1">{label}</p>
          <p className={`text-2xl font-bold ${iconColor}`}>{value}</p>
        </div>
        <div className={`w-10 h-10 ${iconBg} rounded-lg flex items-center justify-center`}>
          <i className={`fa-solid ${icon} ${iconColor}`} />
        </div>
      </div>
    </CardContainer>
  )
}

// ─── Modal ───────────────────────────────────────────────────────
export function Modal({ open, onClose, title, children }) {
  if (!open) return null
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <i className="fa-solid fa-times" />
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

// ─── Tabs ────────────────────────────────────────────────────────
export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="flex space-x-1 border-b border-gray-200 mb-4">
      {tabs.map(t => (
        <button
          key={t}
          onClick={() => onChange(t)}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            active === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          {t}
        </button>
      ))}
    </div>
  )
}

// ─── SectionHeader ───────────────────────────────────────────────
export function SectionHeader({ title, children }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      <div className="flex items-center gap-2">{children}</div>
    </div>
  )
}
