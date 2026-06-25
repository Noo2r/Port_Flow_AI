import { useState, useRef, useCallback } from 'react'
import {
  AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { CardContainer, SectionHeader, Badge } from '../components/ui'
import { useAnalyticsMetrics, useAnalyticsCharts } from '../hooks/queries'

// ── File parsers ──────────────────────────────────────────────────────────────
function parseCSV(text) {
  const lines = text.trim().split(/\r?\n/)
  if (lines.length < 2) return { headers: [], rows: [] }
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  const rows = lines.slice(1)
    .map(line => {
      const vals = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''))
      const row = {}
      headers.forEach((h, i) => {
        const raw = vals[i] ?? ''
        // Use Number() not parseFloat — Number("2026-06-01") is NaN (keeps dates as strings)
        const n = raw !== '' ? Number(raw) : NaN
        row[h] = !isNaN(n) ? n : raw
      })
      return row
    })
    .filter(r => Object.values(r).some(v => v !== ''))
  return { headers, rows }
}

function parseTSV(text) {
  const csv = text.replace(/\t/g, ',')
  return parseCSV(csv)
}

function parseJSON(text) {
  const data = JSON.parse(text)
  const arr = Array.isArray(data) ? data
    : data.data ?? data.rows ?? data.records ?? Object.values(data).find(Array.isArray) ?? []
  if (arr.length === 0) return { headers: [], rows: [] }
  const headers = Object.keys(arr[0])
  const rows = arr.map(item => {
    const row = {}
    headers.forEach(h => {
      const v = item[h]
      if (typeof v === 'number') { row[h] = v; return }
      const n = v !== '' && v != null ? Number(v) : NaN
      row[h] = !isNaN(n) ? n : (v ?? '')
    })
    return row
  })
  return { headers, rows }
}

function detectColumns(headers, rows) {
  if (!rows.length) return { labelCol: null, numericCols: [] }
  const labelCol   = headers.find(h => typeof rows[0][h] === 'string') ?? null
  const numericCols = headers.filter(h => h !== labelCol && typeof rows[0][h] === 'number')
  return { labelCol, numericCols }
}

const CHART_COLORS = ['#3b82f6','#10b981','#f59e0b','#8b5cf6','#ef4444','#06b6d4','#f97316','#6366f1']

// ── Port colour palette (consistent across charts) ───────────────────────────
const PORT_COLORS = {
  PORT_A: '#3b82f6', PORT_B: '#10b981', PORT_C: '#f59e0b',
  PORT_D: '#8b5cf6', PORT_E: '#ef4444', PORT_F: '#06b6d4',
  PORT_G: '#f97316', PORT_H: '#6366f1',
}
const PORT_LABELS = {
  PORT_A: 'Alexandria', PORT_B: 'Port Said', PORT_C: 'Damietta',
  PORT_D: 'Sokhna',     PORT_E: 'Suez',      PORT_F: 'Safaga',
  PORT_G: 'Adabiya',   PORT_H: 'Nuweiba',
}

function fmt(v, suffix = '') {
  if (v == null) return '—'
  return `${typeof v === 'number' ? v.toLocaleString() : v}${suffix}`
}

// Short date label for X axis: "May 04"
function shortDate(ds) {
  if (!ds) return ''
  try {
    return new Date(ds + 'T12:00:00Z').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  } catch { return ds }
}

// Ticker: only show every Nth label to avoid overlap
function everyN(data, n = 2) {
  return data.map((d, i) => ({ ...d, _label: i % n === 0 ? shortDate(d.date) : '' }))
}

export default function AIAnalytics() {
  const { data: metrics, isLoading: metricsLoading } = useAnalyticsMetrics()
  const { data: charts,  isLoading: chartsLoading  } = useAnalyticsCharts(14)

  // ── Imported data state ───────────────────────────────────────────────────
  const [imported, setImported] = useState(null)   // { fileName, headers, rows, labelCol, numericCols }
  const [importErr, setImportErr] = useState('')
  const [importing, setImporting] = useState(false)
  const [chartType, setChartType] = useState('bar')
  const [dragOver, setDragOver]   = useState(false)
  const fileInputRef = useRef()

  const processFile = useCallback((file) => {
    if (!file) return
    setImportErr('')
    setImporting(true)
    const ext = file.name.split('.').pop().toLowerCase()
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const text = e.target.result
        let parsed
        if (ext === 'json') {
          parsed = parseJSON(text)
        } else if (ext === 'tsv' || ext === 'txt') {
          parsed = parseTSV(text)
        } else {
          parsed = parseCSV(text)
        }
        if (!parsed.rows.length) {
          setImportErr('File parsed but contains no data rows.')
          setImporting(false)
          return
        }
        const { labelCol, numericCols } = detectColumns(parsed.headers, parsed.rows)
        if (!numericCols.length) {
          setImportErr('No numeric columns detected. Ensure your file has numeric data columns.')
          setImporting(false)
          return
        }
        setImported({ fileName: file.name, ...parsed, labelCol, numericCols })
      } catch (err) {
        setImportErr(`Parse error: ${err.message}`)
      } finally {
        setImporting(false)
      }
    }
    reader.onerror = () => { setImportErr('Failed to read file.'); setImporting(false) }
    reader.readAsText(file)
  }, [])

  function handleFileChange(e) { processFile(e.target.files?.[0]) }

  function handleDrop(e) {
    e.preventDefault(); setDragOver(false)
    processFile(e.dataTransfer.files?.[0])
  }

  // ── Derived KPI values ────────────────────────────────────────────────────
  const avgTurnaround = (() => {
    const m = metrics?.avg_turnaround_minutes
    if (m == null) return '—'
    return m < 60 ? `${Math.round(m)} min` : `${(m / 60).toFixed(1)} h`
  })()

  const visitCompletionRate = (() => {
    const total = metrics?.total_visits
    const done  = metrics?.completed_visits
    if (!total) return '—'
    return `${Math.round((done / total) * 100)}%`
  })()

  const kpis = [
    { label: 'Total Vessels',        value: metricsLoading ? '…' : fmt(metrics?.total_vessels),
      sub: `${metrics?.active_visits ?? 0} currently active`,
      icon: 'fa-ship',        bg: 'bg-purple-100', color: 'text-purple-600' },
    { label: 'Berth Utilization',    value: metricsLoading ? '…' : fmt(metrics?.berth_utilization_percent, '%'),
      sub: `${metrics?.occupied_berths ?? 0} / ${metrics?.total_berths ?? 0} occupied`,
      icon: 'fa-anchor',      bg: 'bg-blue-100',   color: 'text-blue-600' },
    { label: 'Avg Turnaround',       value: metricsLoading ? '…' : avgTurnaround,
      sub: 'Per vessel visit',
      icon: 'fa-clock',       bg: 'bg-green-100',  color: 'text-status-green' },
    { label: 'Visit Completion Rate',value: metricsLoading ? '…' : visitCompletionRate,
      sub: `${fmt(metrics?.completed_visits)} of ${fmt(metrics?.total_visits)} visits`,
      icon: 'fa-chart-line',  bg: 'bg-yellow-100', color: 'text-yellow-600' },
  ]

  // ── Chart data ────────────────────────────────────────────────────────────
  const trafficData   = everyN(charts?.vessel_traffic   || [], 2)
  const portData      = everyN(charts?.port_traffic     || [], 2)
  const cargoData     = everyN(charts?.cargo_throughput || [], 2)
  const portCodes     = charts?.port_codes || []
  const recs          = charts?.recommendations || []

  const loading = metricsLoading || chartsLoading

  const ChartComponent = chartType === 'line' ? LineChart : BarChart

  return (
    <MainLayout>
      <Navbar
        title="AI-Powered Analytics"
        subtitle="Predictive insights and operational intelligence for smart decision-making"
      >
        {/* Import button lives in the navbar slot */}
        <div className="flex items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.tsv,.txt,.json"
            className="hidden"
            onChange={handleFileChange}
          />
          {imported ? (
            <button
              onClick={() => { setImported(null); setImportErr('') }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
              style={{ background: 'rgba(239,68,68,0.08)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}>
              <i className="fa-solid fa-xmark" />Clear Import
            </button>
          ) : null}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={importing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
            style={{
              background: 'linear-gradient(135deg,#3b82f6,#0891b2)',
              color: 'white', border: '1px solid rgba(59,130,246,0.4)',
              boxShadow: '0 0 12px rgba(59,130,246,0.25)',
            }}>
            <i className={`fa-solid ${importing ? 'fa-spinner fa-spin' : 'fa-file-import'}`} />
            {importing ? 'Reading…' : 'Import Data'}
          </button>
        </div>
      </Navbar>
      <div className="flex-1 p-6 overflow-auto">

        {/* ── Import drop zone (shown when no data yet) ─────────────────── */}
        {!imported && (
          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className="mb-6 rounded-2xl border-2 border-dashed flex flex-col items-center justify-center py-8 cursor-pointer transition-all"
            style={{
              borderColor: dragOver ? '#3b82f6' : 'rgba(148,163,184,0.15)',
              background:  dragOver ? 'rgba(59,130,246,0.06)' : 'rgba(8,15,30,0.6)',
            }}>
            <div className="w-12 h-12 rounded-xl flex items-center justify-center mb-3"
              style={{ background: 'rgba(59,130,246,0.12)', border: '1px solid rgba(59,130,246,0.2)' }}>
              <i className="fa-solid fa-file-arrow-up text-xl" style={{ color: '#60a5fa' }} />
            </div>
            <p className="text-sm font-medium mb-1" style={{ color: '#ccd9f0' }}>
              Drop a file or <span style={{ color: '#3b82f6' }}>click to browse</span>
            </p>
            <p className="text-xs" style={{ color: '#3d5a8a' }}>Supports CSV · TSV · JSON · TXT</p>
            {importErr && (
              <p className="mt-3 text-xs flex items-center gap-1" style={{ color: '#f87171' }}>
                <i className="fa-solid fa-circle-exclamation" />{importErr}
              </p>
            )}
          </div>
        )}

        {/* ── Imported data visualisation ──────────────────────────────── */}
        {imported && (
          <div className="mb-6 space-y-4">
            {/* File info bar */}
            <div className="flex items-center gap-3 p-3 rounded-xl"
              style={{ background: 'rgba(59,130,246,0.08)', border: '1px solid rgba(59,130,246,0.2)' }}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                style={{ background: 'rgba(59,130,246,0.15)' }}>
                <i className="fa-solid fa-file-csv text-sm" style={{ color: '#60a5fa' }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate" style={{ color: '#f0f6ff' }}>{imported.fileName}</p>
                <p className="text-xs" style={{ color: '#3d5a8a' }}>
                  {imported.rows.length} rows · {imported.headers.length} columns ·{' '}
                  {imported.numericCols.length} numeric series
                </p>
              </div>
              {/* Chart type switcher */}
              <div className="flex items-center gap-1 p-1 rounded-lg bg-white border border-gray-200">
                {[
                  { type: 'bar',  icon: 'fa-chart-column' },
                  { type: 'line', icon: 'fa-chart-line'   },
                ].map(c => (
                  <button key={c.type} onClick={() => setChartType(c.type)}
                    className="w-7 h-7 rounded flex items-center justify-center text-xs transition-all"
                    style={{
                      background: chartType === c.type ? '#3b82f6' : 'transparent',
                      color:      chartType === c.type ? 'white'    : '#6b7280',
                    }}>
                    <i className={`fa-solid ${c.icon}`} />
                  </button>
                ))}
              </div>
            </div>

            {/* Chart */}
            <CardContainer className="p-6">
              <div className="flex items-center justify-between mb-4">
                <SectionHeader title={`Imported: ${imported.fileName}`} />
                <Badge variant="blue">{imported.rows.length} rows</Badge>
              </div>
              <ResponsiveContainer width="100%" height={260}>
                <ChartComponent data={imported.rows} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis
                    dataKey={imported.labelCol ?? undefined}
                    tick={{ fontSize: 11 }}
                    tickFormatter={v => String(v).slice(0, 10)}
                    interval="preserveStartEnd"
                  />
                  <YAxis tick={{ fontSize: 11 }} allowDecimals />
                  <Tooltip />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {imported.numericCols.slice(0, 6).map((col, i) =>
                    chartType === 'line'
                      ? <Line key={col} type="monotone" dataKey={col} stroke={CHART_COLORS[i % CHART_COLORS.length]} strokeWidth={2} dot={{ r: 2 }} name={col} />
                      : <Bar    key={col} dataKey={col} fill={CHART_COLORS[i % CHART_COLORS.length]} name={col} radius={[3,3,0,0]} />
                  )}
                </ChartComponent>
              </ResponsiveContainer>
            </CardContainer>

            {/* Data preview table */}
            <CardContainer className="p-6">
              <div className="flex items-center justify-between mb-3">
                <SectionHeader title="Data Preview" />
                <span className="text-xs" style={{ color: '#3d5a8a' }}>First 10 rows</span>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr style={{ borderBottom: '1px solid rgba(148,163,184,0.1)' }}>
                      {imported.headers.map(h => (
                        <th key={h} className="text-left py-2 pr-4 font-semibold whitespace-nowrap"
                          style={{ color: '#3d5a8a' }}>
                          {h}
                          {imported.numericCols.includes(h) && (
                            <span className="ml-1 font-normal" style={{ color: '#60a5fa' }}>#</span>
                          )}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {imported.rows.slice(0, 10).map((row, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid rgba(148,163,184,0.05)' }}>
                        {imported.headers.map(h => (
                          <td key={h} className="py-2 pr-4 whitespace-nowrap" style={{ color: '#ccd9f0' }}>
                            {typeof row[h] === 'number'
                              ? row[h].toLocaleString(undefined, { maximumFractionDigits: 2 })
                              : (row[h] ?? '—')}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContainer>

            {importErr && (
              <p className="text-xs text-red-500 flex items-center gap-1">
                <i className="fa-solid fa-circle-exclamation" />{importErr}
              </p>
            )}
          </div>
        )}

        {/* ── KPI row ───────────────────────────────────────────────────── */}
        <div className="grid grid-cols-4 gap-6 mb-6">
          {kpis.map(k => (
            <CardContainer key={k.label} className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">{k.label}</p>
                  <p className="text-2xl font-bold text-gray-900">{k.value}</p>
                  {k.sub && <p className="text-xs text-gray-500 mt-1">{k.sub}</p>}
                </div>
                <div className={`w-12 h-12 ${k.bg} rounded-lg flex items-center justify-center`}>
                  <i className={`fa-solid ${k.icon} ${k.color} text-lg`} />
                </div>
              </div>
            </CardContainer>
          ))}
        </div>

        {/* ── Visit Breakdown + Port Traffic + Cargo Throughput ─────────── */}
        <div className="grid grid-cols-3 gap-6 mb-6">

          {/* Visit Breakdown */}
          <CardContainer className="p-6">
            <SectionHeader title="Visit Breakdown" />
            <div className="mt-4 space-y-3">
              {[
                { label: 'Scheduled', value: metrics?.scheduled_visits, color: 'bg-blue-500' },
                { label: 'Active',    value: metrics?.active_visits,    color: 'bg-green-500' },
                { label: 'Completed', value: metrics?.completed_visits, color: 'bg-gray-400' },
              ].map(row => {
                const pct = metrics?.total_visits
                  ? Math.round(((row.value ?? 0) / metrics.total_visits) * 100) : 0
                return (
                  <div key={row.label}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-600">{row.label}</span>
                      <span className="font-semibold">{loading ? '…' : fmt(row.value)} ({pct}%)</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                      <div className={`${row.color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContainer>

          {/* Port Traffic Trend — stacked bar */}
          <CardContainer className="p-6">
            <SectionHeader title="Port Traffic Trend" />
            {chartsLoading ? (
              <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
                <i className="fa-solid fa-spinner fa-spin mr-2" />Loading…
              </div>
            ) : portData.length === 0 || portCodes.length === 0 ? (
              <div className="flex items-center justify-center h-40 text-gray-400">
                <div className="text-center">
                  <i className="fa-solid fa-chart-bar text-3xl mb-2 opacity-30" />
                  <p className="text-xs">No traffic data yet</p>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={portData} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="_label" tick={{ fontSize: 10 }} interval={0} />
                  <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                  <Tooltip
                    labelFormatter={(_, payload) => payload?.[0]?.payload?.date || ''}
                    formatter={(v, name) => [v, PORT_LABELS[name] || name]}
                  />
                  {portCodes.slice(0, 6).map(pc => (
                    <Bar key={pc} dataKey={pc} stackId="a"
                      fill={PORT_COLORS[pc] || '#94a3b8'} name={pc} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContainer>

          {/* Cargo Throughput — grouped bar */}
          <CardContainer className="p-6">
            <SectionHeader title="Cargo Throughput" />
            {chartsLoading ? (
              <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
                <i className="fa-solid fa-spinner fa-spin mr-2" />Loading…
              </div>
            ) : cargoData.length === 0 ? (
              <div className="flex items-center justify-center h-40 text-gray-400">
                <div className="text-center">
                  <i className="fa-solid fa-boxes-stacked text-3xl mb-2 opacity-30" />
                  <p className="text-xs">No throughput data yet</p>
                </div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={cargoData} margin={{ top: 4, right: 4, left: -28, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="_label" tick={{ fontSize: 10 }} interval={0} />
                  <YAxis tick={{ fontSize: 10 }} allowDecimals={false} />
                  <Tooltip labelFormatter={(_, p) => p?.[0]?.payload?.date || ''} />
                  <Bar dataKey="completed" fill="#22c55e" name="Completed" radius={[2,2,0,0]} />
                  <Bar dataKey="active"    fill="#3b82f6" name="Active"    radius={[2,2,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContainer>
        </div>

        {/* ── Vessel Traffic Trend — full-width area chart ──────────────── */}
        <CardContainer className="p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <SectionHeader title="Vessel Traffic Trend — Last 14 Days" />
            <span className="text-xs text-gray-400">Daily arrivals &amp; avg wait time</span>
          </div>
          {chartsLoading ? (
            <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
              <i className="fa-solid fa-spinner fa-spin mr-2" />Loading…
            </div>
          ) : trafficData.length === 0 ? (
            <div className="flex items-center justify-center h-48 text-gray-400">
              <div className="text-center">
                <i className="fa-solid fa-chart-area text-4xl mb-3 opacity-30" />
                <p className="text-sm">No traffic data available yet</p>
              </div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={trafficData} margin={{ top: 4, right: 16, left: -10, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradArrivals" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#3b82f6" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.03} />
                  </linearGradient>
                  <linearGradient id="gradWait" x1="0" y1="0" x2="0" y2="1">
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
                  stroke="#3b82f6" fill="url(#gradArrivals)" strokeWidth={2} dot={{ r: 3 }} />
                <Area yAxisId="right" type="monotone" dataKey="avg_wait_min" name="Avg Wait (min)"
                  stroke="#f59e0b" fill="url(#gradWait)"     strokeWidth={2} dot={{ r: 3 }} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContainer>

        {/* ── Database Overview ─────────────────────────────────────────── */}
        <CardContainer className="p-6 mb-6">
          <SectionHeader title="Database Overview" />
          <div className="grid grid-cols-5 gap-4 mt-4">
            {[
              { label: 'Ports (WPI)',    value: metrics?.total_ports,       icon: 'fa-map-pin',   color: 'text-purple-600', bg: 'bg-purple-50' },
              { label: 'Vessels',        value: metrics?.total_vessels,     icon: 'fa-ship',      color: 'text-blue-600',   bg: 'bg-blue-50' },
              { label: 'Berths',         value: metrics?.total_berths,      icon: 'fa-anchor',    color: 'text-green-600',  bg: 'bg-green-50' },
              { label: 'Total Visits',   value: metrics?.total_visits,      icon: 'fa-calendar',  color: 'text-yellow-600', bg: 'bg-yellow-50' },
              { label: 'AI Predictions', value: metrics?.total_predictions, icon: 'fa-brain',     color: 'text-pink-600',   bg: 'bg-pink-50' },
            ].map(s => (
              <div key={s.label} className={`${s.bg} rounded-xl p-4 text-center`}>
                <i className={`fa-solid ${s.icon} ${s.color} text-xl mb-2 block`} />
                <p className="text-xl font-bold text-gray-900">
                  {metricsLoading ? '…' : (s.value?.toLocaleString() ?? '—')}
                </p>
                <p className="text-xs text-gray-500 mt-1">{s.label}</p>
              </div>
            ))}
          </div>
        </CardContainer>

        {/* ── AI Recommendations ────────────────────────────────────────── */}
        <CardContainer className="p-6">
          <div className="flex items-center space-x-2 mb-4">
            <i className="fa-solid fa-robot text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">AI Recommendations</h3>
            <Badge variant="blue">Live</Badge>
          </div>
          {chartsLoading ? (
            <div className="grid grid-cols-2 gap-4">
              {[1,2,3,4].map(i => (
                <div key={i} className="animate-pulse h-20 bg-gray-100 rounded-lg" />
              ))}
            </div>
          ) : recs.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-6">Generating recommendations…</p>
          ) : (
            <div className="grid grid-cols-2 gap-4">
              {recs.map((ins, idx) => (
                <div key={idx} className={`p-4 ${ins.bg} rounded-lg border-l-4 ${ins.border}`}>
                  <div className="flex items-start space-x-3">
                    <i className={`fa-solid ${ins.icon} ${ins.color} mt-0.5 flex-shrink-0`} />
                    <div>
                      <p className="font-medium text-gray-900 text-sm">{ins.title}</p>
                      <p className="text-xs text-gray-600 mt-1 leading-relaxed">{ins.desc}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContainer>

      </div>
    </MainLayout>
  )
}
