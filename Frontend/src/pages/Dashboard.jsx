import { useEffect, useRef, useState } from 'react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import { useNavigate } from 'react-router-dom'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { StatCard, CardContainer, SectionHeader, Badge } from '../components/ui'
import { useAnalyticsMetrics, useAnalyticsCharts, useBerths, useVisits } from '../hooks/queries'

const berthBadge = {
  available:   'solid_green',
  occupied:    'solid_red',
  maintenance: 'solid_yellow',
  unavailable: 'solid_yellow',
}

function LoadingCard({ rows = 1 }) {
  return (
    <div className="animate-pulse space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-4 bg-gray-200 rounded w-3/4" />
      ))}
    </div>
  )
}

function fmt(n, suffix = '') {
  if (n == null) return '—'
  return `${n}${suffix}`
}

function shortDate(ds) {
  if (!ds) return ''
  try { return new Date(ds + 'T12:00:00Z').toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) }
  catch { return ds }
}

const AI_MODELS = [
  {
    to:        '/predictions',
    icon:      'fa-brain',
    name:      'ETA Predictor',
    tag:       'CatBoost ML · 38 features',
    desc:      'Predicts vessel delay & ETA with SHAP explanations',
    statKey:   'total_predictions',
    statLabel: 'predictions made',
    accent:    '#3b82f6',
    iconBg:    'bg-blue-100',
    iconColor: 'text-blue-600',
  },
  {
    to:        '/berth',
    icon:      'fa-warehouse',
    name:      'Berth Optimizer',
    tag:       'Constraint Solver · 6 criteria',
    desc:      'Real-time berth scoring with priority & weather-aware allocation',
    statKey:   'total_berths',
    statLabel: 'berths managed',
    accent:    '#10b981',
    iconBg:    'bg-emerald-100',
    iconColor: 'text-emerald-600',
  },
  {
    to:        '/analytics',
    icon:      'fa-chart-column',
    name:      'Analytics Engine',
    tag:       'Operational Intelligence',
    desc:      'Traffic trends, cargo throughput & AI-generated recommendations',
    statKey:   'total_visits',
    statLabel: 'visits analyzed',
    accent:    '#8b5cf6',
    iconBg:    'bg-purple-100',
    iconColor: 'text-purple-600',
  },
  {
    to:        '/congestion',
    icon:      'fa-cloud-bolt',
    name:      'Congestion Forecast',
    tag:       'Stage 3 · Time-Series Forecaster',
    desc:      'Forecasts port congestion levels and traffic bottlenecks ahead of time',
    statKey:   'total_ports',
    statLabel: 'ports monitored',
    accent:    '#f97316',
    iconBg:    'bg-orange-100',
    iconColor: 'text-orange-600',
  },
]

const BERTH_COLORS = {
  occupied:    { border: '#ef4444', dot: '#ef4444', label: 'text-red-400' },
  available:   { border: '#10b981', dot: '#10b981', label: 'text-emerald-400' },
  maintenance: { border: '#f59e0b', dot: '#f59e0b', label: 'text-yellow-400' },
}

function BerthMiniCard({ b }) {
  const st  = (b.status || '').toLowerCase()
  const c   = BERTH_COLORS[st] || { border: '#475569', dot: '#475569', label: 'text-slate-400' }
  const raw = b.name || b.code || '—'
  const display = raw
    .replace(/^Port of\s+/i, '')
    .replace(/\bPort\b\s+/i, '')
    .replace(/\s+Berth\s+/i, ' #')
  return (
    <div
      className="flex items-center gap-2 rounded-md px-3 py-2 mb-2"
      style={{ borderLeft: `3px solid ${c.border}`, background: `${c.border}18` }}
    >
      <span
        className="flex-shrink-0 w-2 h-2 rounded-full"
        style={{
          background: c.dot,
          boxShadow: `0 0 6px ${c.dot}`,
          color: c.dot,
          animation: st === 'occupied' ? 'berth-glow 1.8s ease-in-out infinite' : 'none',
        }}
      />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-gray-100 truncate leading-tight">{display}</p>
        <p className={`text-[10px] capitalize leading-tight ${c.label}`}>{st || '—'}</p>
      </div>
    </div>
  )
}

// Continuous, very-slow vertical auto-scroll for the demo — drives
// `scrollTop` directly via rAF rather than a CSS transform, so native wheel/
// drag scrolling (the user "taking over") and the auto-scroll never fight
// each other: a manual scroll just changes the same scrollTop the rAF loop
// reads from next frame. The list is rendered twice back-to-back so that
// once we've scrolled past the first copy's height, resetting scrollTop by
// that same amount lands on pixel-identical content — a seamless loop with
// no jump or flicker.
function BerthTicker({ berths }) {
  const containerRef = useRef(null)
  const pausedRef = useRef(false)
  const [hovered, setHovered] = useState(false)

  useEffect(() => { pausedRef.current = hovered }, [hovered])

  useEffect(() => {
    const el = containerRef.current
    if (!el || !berths?.length) return
    let raf
    let last = performance.now()
    const PIXELS_PER_SECOND = 14   // slow, professional showcase speed

    function tick(now) {
      const dt = now - last
      last = now
      if (!pausedRef.current) {
        const loopAt = el.scrollHeight / 2
        let next = el.scrollTop + (PIXELS_PER_SECOND * dt) / 1000
        if (loopAt > 0 && next >= loopAt) next -= loopAt
        el.scrollTop = next
      }
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [berths])

  if (!berths?.length) return <p className="text-sm text-gray-500">No berths configured yet.</p>

  return (
    <div
      ref={containerRef}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className="overflow-y-auto"
      style={{ maxHeight: '360px', scrollbarWidth: 'thin', willChange: 'scroll-position' }}
    >
      {[...berths, ...berths].map((b, i) => <BerthMiniCard key={i} b={b} />)}
    </div>
  )
}

export default function Dashboard() {
  const navigate = useNavigate()
  const { data: metrics, isLoading: metricsLoading } = useAnalyticsMetrics()
  const { data: berths,  isLoading: berthsLoading  } = useBerths(0, 120)
  const { data: visits,  isLoading: visitsLoading  } = useVisits({ limit: 5, skip: 0 })
  const { data: charts,  isLoading: chartsLoading  } = useAnalyticsCharts(14)

  const trafficData = (charts?.vessel_traffic || []).map((d, i) => ({
    ...d, _label: i % 2 === 0 ? shortDate(d.date) : '',
  }))

  // ── KPIs — mapped to real backend field names ─────────────────────────────
  const kpis = [
    {
      label:     'Active Vessels',
      value:     metricsLoading ? '…' : fmt(metrics?.total_vessels),
      sub:       metricsLoading ? '' : `${metrics?.active_visits ?? 0} currently in port`,
      subColor:  'text-blue-600',
      icon:      'fa-ship',
      iconBg:    'bg-blue-100',
      iconColor: 'text-blue-600',
    },
    {
      label:     'Berth Utilization',
      value:     metricsLoading ? '…' : fmt(metrics?.berth_utilization_percent, '%'),
      sub:       metricsLoading ? '' : `${metrics?.occupied_berths ?? 0} / ${metrics?.total_berths ?? 0} berths occupied`,
      subColor:  'text-status-green',
      icon:      'fa-anchor',
      iconBg:    'bg-green-100',
      iconColor: 'text-status-green',
    },
    {
      label:     'Avg Turnaround',
      value:     metricsLoading ? '…' :
                 metrics?.avg_turnaround_minutes != null
                   ? metrics.avg_turnaround_minutes < 60
                     ? `${Math.round(metrics.avg_turnaround_minutes)} min`
                     : `${(metrics.avg_turnaround_minutes / 60).toFixed(1)} h`
                   : '—',
      sub:       'Per vessel visit',
      subColor:  'text-yellow-600',
      icon:      'fa-clock',
      iconBg:    'bg-yellow-100',
      iconColor: 'text-yellow-600',
    },
    {
      label:     'Total Ports',
      value:     metricsLoading ? '…' : fmt(metrics?.total_ports),
      sub:       metricsLoading ? '' : `${metrics?.total_predictions?.toLocaleString() ?? 0} predictions made`,
      subColor:  'text-purple-600',
      icon:      'fa-chart-line',
      iconBg:    'bg-purple-100',
      iconColor: 'text-purple-600',
    },
  ]

  // ── Berth status cards ─────────────────────────────────────────────────────
  const berthStatusCards = berthsLoading || !berths ? [] : berths.map(b => ({
    name:   b.name || b.code,
    vessel: b.status === 'occupied'
      ? 'Occupied'
      : b.status === 'available'
        ? 'Available'
        : b.status ?? '—',
    status: b.status ? b.status.charAt(0).toUpperCase() + b.status.slice(1) : '—',
    color:  b.status === 'available'
      ? 'gray'
      : b.status === 'occupied'
        ? 'green'
        : 'yellow',
  }))

  // ── Recent visits ──────────────────────────────────────────────────────────
  const recentVisits = visitsLoading || !visits ? [] : visits.slice(0, 5)

  function visitStatusColor(s) {
    if (s === 'in_port')   return 'bg-green-50 border-status-green text-status-green'
    if (s === 'scheduled') return 'bg-blue-50 border-blue-400 text-blue-700'
    if (s === 'completed') return 'bg-gray-50 border-gray-300 text-gray-500'
    if (s === 'departed')  return 'bg-gray-50 border-gray-300 text-gray-500'
    return 'bg-yellow-50 border-status-yellow text-status-yellow'
  }
  function visitIcon(s) {
    if (s === 'in_port')   return 'fa-anchor'
    if (s === 'scheduled') return 'fa-clock'
    if (s === 'completed') return 'fa-check-circle'
    if (s === 'departed')  return 'fa-ship'
    return 'fa-exclamation-circle'
  }
  function formatDt(dt) {
    if (!dt) return '—'
    try { return new Date(dt).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) }
    catch { return dt }
  }

  return (
    <MainLayout>
      <Navbar
        title="Port Operations Dashboard"
        subtitle="Real-time overview of port activities and performance"
      />
      <div className="flex-1 p-6 overflow-auto">

        {/* KPIs */}
        <div className="grid grid-cols-4 gap-6 mb-6">
          {kpis.map(k => <StatCard key={k.label} {...k} />)}
        </div>

        {/* ── AI Model shortcuts ───────────────────────────────────────── */}
        <div className="mb-6">
          <div className="flex items-center gap-2 mb-3">
            <i className="fa-solid fa-robot text-sm" style={{ color: '#8b5cf6' }} />
            <span className="text-sm font-semibold" style={{ color: '#ccd9f0' }}>AI Models</span>
            <div className="flex-1 h-px" style={{ background: 'rgba(148,163,184,0.08)' }} />
            <span className="text-xs" style={{ color: '#3d5a8a' }}>Click to open</span>
          </div>
          <div className="grid grid-cols-4 gap-4">
            {AI_MODELS.map(m => (
              <button
                key={m.to}
                onClick={() => navigate(m.to)}
                className="text-left focus:outline-none w-full"
                onMouseEnter={e => {
                  const card = e.currentTarget.querySelector('.ai-card')
                  card.style.borderColor = m.accent + '50'
                  card.style.boxShadow = `0 0 24px ${m.accent}14`
                  e.currentTarget.querySelector('.ai-arrow').style.color = m.accent
                }}
                onMouseLeave={e => {
                  const card = e.currentTarget.querySelector('.ai-card')
                  card.style.borderColor = 'rgba(148,163,184,0.09)'
                  card.style.boxShadow = '0 2px 12px rgba(0,0,0,0.5)'
                  e.currentTarget.querySelector('.ai-arrow').style.color = '#1e2e4a'
                }}
              >
                <div className="ai-card rounded-xl p-5 h-full transition-all duration-200 cursor-pointer"
                  style={{ background: '#080f1e', border: '1px solid rgba(148,163,184,0.09)', boxShadow: '0 2px 12px rgba(0,0,0,0.5)' }}>

                  <div className="flex items-start justify-between mb-4">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                      style={{ background: m.accent + '18', border: `1px solid ${m.accent}30` }}>
                      <i className={`fa-solid ${m.icon} text-base`} style={{ color: m.accent }} />
                    </div>
                    <i className="ai-arrow fa-solid fa-arrow-up-right-from-square text-xs mt-1 transition-colors"
                      style={{ color: '#1e2e4a' }} />
                  </div>

                  <p className="font-bold text-sm mb-0.5" style={{ color: '#f0f6ff' }}>{m.name}</p>
                  <p className="text-[11px] font-semibold mb-2" style={{ color: m.accent }}>{m.tag}</p>
                  <p className="text-xs leading-relaxed mb-4" style={{ color: '#3d5a8a' }}>{m.desc}</p>

                  <div className="flex items-baseline gap-1.5 pt-3"
                    style={{ borderTop: '1px solid rgba(148,163,184,0.08)' }}>
                    <span className="text-xl font-bold tabular-nums" style={{ color: m.accent }}>
                      {metricsLoading ? '…' : (metrics?.[m.statKey]?.toLocaleString() ?? '—')}
                    </span>
                    <span className="text-xs" style={{ color: '#3d5a8a' }}>{m.statLabel}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-3 gap-6 mb-6">

          {/* Vessel Traffic Trend — live area chart */}
          <CardContainer className="col-span-2 p-6">
            <div className="flex items-center justify-between mb-3">
              <SectionHeader title="Vessel Traffic Trend" />
              <span className="text-xs text-gray-400">Last 14 days</span>
            </div>
            {chartsLoading ? (
              <div className="flex items-center justify-center h-64 text-gray-400 text-sm">
                <i className="fa-solid fa-spinner fa-spin mr-2" />Loading…
              </div>
            ) : trafficData.length === 0 ? (
              <div className="flex items-center justify-center h-64 text-gray-400">
                <div className="text-center">
                  <i className="fa-solid fa-chart-line text-4xl mb-3 opacity-30" />
                  <p className="text-sm">Traffic history will appear here over time.</p>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={trafficData} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="dashGradArrivals" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.03} />
                    </linearGradient>
                    <linearGradient id="dashGradWait" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.03} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="_label" tick={{ fontSize: 11 }} interval={0} />
                  <YAxis yAxisId="left"  tick={{ fontSize: 11 }} allowDecimals={false} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} unit=" min" />
                  <Tooltip labelFormatter={(_, p) => p?.[0]?.payload?.date || ''} />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  <Area yAxisId="left"  type="monotone" dataKey="arrivals"     name="Arrivals"
                    stroke="#3b82f6" fill="url(#dashGradArrivals)" strokeWidth={2} dot={{ r: 3 }} />
                  <Area yAxisId="right" type="monotone" dataKey="avg_wait_min" name="Avg Wait (min)"
                    stroke="#f59e0b" fill="url(#dashGradWait)"     strokeWidth={2} dot={{ r: 3 }} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </CardContainer>

          {/* Berth Status — animated ticker */}
          <CardContainer className="p-6">
            <div className="flex items-center justify-between mb-3">
              <SectionHeader title="Berth Status" />
              <div className="flex items-center gap-3 text-[10px] text-gray-400">
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />available
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" />occupied
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 inline-block" />maintenance
                </span>
              </div>
            </div>
            {berthsLoading ? (
              <LoadingCard rows={4} />
            ) : (
              <BerthTicker berths={berths || []} />
            )}
          </CardContainer>
        </div>

        {/* Bottom row */}
        <div className="grid grid-cols-2 gap-6">

          {/* Live metrics summary */}
          <CardContainer className="p-6">
            <SectionHeader title="System Overview">
              <Badge variant="solid_green">Live</Badge>
            </SectionHeader>
            {metricsLoading ? (
              <LoadingCard rows={6} />
            ) : (
              <div className="space-y-3">
                {[
                  { label: 'Total Vessels',     value: metrics?.total_vessels?.toLocaleString() ?? '—',       icon: 'fa-ship',      color: 'text-blue-600' },
                  { label: 'Total Ports (WPI)', value: metrics?.total_ports?.toLocaleString() ?? '—',         icon: 'fa-map-pin',   color: 'text-purple-600' },
                  { label: 'Total Berths',      value: metrics?.total_berths?.toLocaleString() ?? '—',        icon: 'fa-anchor',    color: 'text-green-600' },
                  { label: 'Scheduled Visits',  value: metrics?.scheduled_visits?.toLocaleString() ?? '—',   icon: 'fa-calendar',  color: 'text-yellow-600' },
                  { label: 'Completed Visits',  value: metrics?.completed_visits?.toLocaleString() ?? '—',   icon: 'fa-check',     color: 'text-status-green' },
                  { label: 'AI Predictions',    value: metrics?.total_predictions?.toLocaleString() ?? '—',  icon: 'fa-brain',     color: 'text-pink-600' },
                ].map(row => (
                  <div key={row.label} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <div className="flex items-center space-x-2">
                      <i className={`fa-solid ${row.icon} ${row.color} w-4`} />
                      <span className="text-sm text-gray-700">{row.label}</span>
                    </div>
                    <span className="font-semibold text-gray-900">{row.value}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContainer>

          {/* Recent Visits — live */}
          <CardContainer className="p-6">
            <SectionHeader title="Recent Visits" />
            {visitsLoading ? (
              <LoadingCard rows={5} />
            ) : recentVisits.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-10 text-gray-400">
                <i className="fa-solid fa-clock-rotate-left text-3xl mb-3 opacity-30" />
                <p className="text-sm">No recent visits yet.</p>
                <p className="text-xs mt-1">Vessel arrivals and berth assignments will appear here.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentVisits.map(v => (
                  <div
                    key={v.id}
                    className={`flex items-start space-x-3 p-3 rounded-lg border-l-4 ${visitStatusColor(v.status)}`}
                  >
                    <i className={`fa-solid ${visitIcon(v.status)} mt-0.5 flex-shrink-0`} />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 text-sm">
                        Visit #{v.id}
                        {v.voyage_number ? ` — ${v.voyage_number}` : ''}
                      </p>
                      <p className="text-xs text-gray-600 mt-0.5">
                        Status: <span className="font-medium capitalize">{v.status?.replace('_', ' ') ?? '—'}</span>
                        {v.eta ? ` · ETA: ${formatDt(v.eta)}` : ''}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContainer>

        </div>
      </div>
    </MainLayout>
  )
}
