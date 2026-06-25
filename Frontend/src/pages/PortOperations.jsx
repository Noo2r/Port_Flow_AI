/**
 * Port Operations Dashboard
 * =========================
 * All data sourced from real DB via:
 *   GET /api/v1/port-ops/port-kpis      → aggregate KPIs
 *   GET /api/v1/port-ops/berth-status   → per-berth occupancy + port info
 *   GET /api/v1/port-ops/allocations    → visits with vessel + berth + port names
 *   GET /api/v1/port-ops/health         → engine health
 */
import { useState } from 'react'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { CardContainer, Badge, Button } from '../components/ui'
import { usePortKpis, useBerthStatus, usePortAllocations, usePortOpsHealth } from '../hooks/queries'

// ── Display helpers ───────────────────────────────────────────────────────────

// Short label for tight spaces (Gantt bars, heatmap tiles)
// "PORT_A_B06" → "B06"   "EGALX-A1" → "A1"   "BC-7EDBFD" → "7EDBFD"
function berthShortLabel(code) {
  if (!code) return '—'
  const parts = code.split(/[-_]/)
  return parts[parts.length - 1] || code
}

// Group items by their port_id / port_name (from API response fields directly)
function groupByPort(items, getPortFn) {
  const map = new Map()
  for (const item of items) {
    const { portId, portName } = getPortFn(item)
    const key = portId || 'OTHER'
    if (!map.has(key)) map.set(key, { portId: key, portName: portName || portId || 'Other', items: [] })
    map.get(key).items.push(item)
  }
  return [...map.values()].sort((a, b) => a.portName.localeCompare(b.portName))
}

function fmtDt(v) {
  if (!v) return '—'
  try { return new Date(v).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) }
  catch { return v }
}
function fmtMin(v) {
  if (v == null) return '—'
  if (v >= 60) return `${(v / 60).toFixed(1)} h`
  return `${Math.round(v)} min`
}
function pct(v) { return v != null ? `${Math.round(v * 100)}%` : '—' }

function UtilBar({ util }) {
  const p = Math.round((util || 0) * 100)
  const col = p > 85 ? 'bg-red-500' : p > 65 ? 'bg-yellow-400' : 'bg-green-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full min-w-[60px]">
        <div className={`${col} h-2 rounded-full transition-all`} style={{ width: `${p}%` }} />
      </div>
      <span className="text-xs tabular-nums text-gray-500 w-8">{p}%</span>
    </div>
  )
}

function StatusChip({ flag, trueLabel, falseLabel, trueColor = 'red', falseColor = 'green' }) {
  const colors = {
    red:    'bg-red-50 text-red-700 border-red-100',
    orange: 'bg-orange-50 text-orange-700 border-orange-100',
    green:  'bg-green-50 text-green-700 border-green-100',
    gray:   'bg-gray-50 text-gray-500 border-gray-100',
  }
  const col = flag ? colors[trueColor] : colors[falseColor]
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${col}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${flag ? `bg-${trueColor}-500` : `bg-${falseColor}-500`}`} />
      {flag ? trueLabel : falseLabel}
    </span>
  )
}

// ── Berth Board ───────────────────────────────────────────────────────────────
function BerthBoard({ berths, allocations }) {
  if (!berths || berths.length === 0) return (
    <div className="py-10 text-center text-gray-400 text-sm">
      <i className="fa-solid fa-anchor text-4xl block mb-3 opacity-20" />
      No berths loaded.
    </div>
  )

  const allocationByBerth = {}
  for (const a of (allocations || [])) {
    if (!allocationByBerth[a.assigned_berth] ||
        new Date(a.berthing_start_time) > new Date(allocationByBerth[a.assigned_berth].berthing_start_time)) {
      allocationByBerth[a.assigned_berth] = a
    }
  }

  const portGroups = groupByPort(berths, b => ({ portId: b.port_id, portName: b.port_name }))

  return (
    <div className="space-y-8">
      {portGroups.map(({ portId, portName, items: portBerths }) => {
        const avgUtil = portBerths.reduce((s, b) => s + (b.berth_utilization || 0), 0) / portBerths.length
        const occupied = portBerths.filter(b => (b.berth_utilization || 0) > 0.1).length
        return (
          <div key={portId}>
            <div className="flex items-center gap-3 mb-3 pb-2 border-b border-gray-100">
              <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center flex-shrink-0">
                <i className="fa-solid fa-anchor text-white text-sm" />
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-gray-900 text-base">{portName}</h3>
                <p className="text-xs text-gray-400">
                  {portBerths.length} berths · {occupied} occupied · avg {Math.round(avgUtil * 100)}% utilization
                </p>
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
              {portBerths.map(b => {
                const alloc = allocationByBerth[b.berth_id]
                const util = b.berth_utilization || 0
                const isOccupied = util > 0.1
                return (
                  <div key={b.berth_id}
                    className={`p-4 rounded-xl border-2 transition-all ${
                      isOccupied
                        ? util > 0.85 ? 'border-red-200 bg-red-50/40' : 'border-blue-200 bg-blue-50/30'
                        : 'border-gray-100 bg-white'
                    }`}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isOccupied ? 'bg-blue-600' : 'bg-gray-200'}`}>
                          <i className={`fa-solid fa-anchor text-xs ${isOccupied ? 'text-white' : 'text-gray-400'}`} />
                        </div>
                        <div>
                          <p className="font-bold text-gray-900 text-sm truncate max-w-[140px]" title={b.berth_name}>{b.berth_name || b.berth_id}</p>
                          <p className="text-[10px] text-gray-400">Max {b.berth_max_length || '—'}m · {(b.berth_type || '').replace(/_/g,' ')}</p>
                        </div>
                      </div>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${isOccupied ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-500'}`}>
                        {isOccupied ? 'Occupied' : 'Available'}
                      </span>
                    </div>
                    <UtilBar util={util} />
                    {alloc ? (
                      <div className="mt-3 text-xs space-y-1">
                        <div className="flex justify-between text-gray-500">
                          <span>Vessel</span>
                          <span className="font-medium text-gray-800 truncate ml-2 text-right max-w-[120px]" title={alloc.vessel_id}>{alloc.vessel_id}</span>
                        </div>
                        <div className="flex justify-between text-gray-500">
                          <span>Departure</span>
                          <span className="font-medium text-gray-800">{fmtDt(alloc.departure_time)}</span>
                        </div>
                        {alloc.conflict_flag && (
                          <div className="mt-1"><StatusChip flag={true} trueLabel="Schedule Conflict" falseLabel="" trueColor="red" /></div>
                        )}
                      </div>
                    ) : (
                      <p className="mt-2 text-xs text-gray-400 text-center">No active allocation</p>
                    )}
                    {b.berth_queue_length > 0 && (
                      <div className="mt-2 flex items-center gap-1 text-xs text-amber-600">
                        <i className="fa-solid fa-clock text-[10px]" />
                        {b.berth_queue_length} vessel{b.berth_queue_length > 1 ? 's' : ''} queued
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Allocations Table ─────────────────────────────────────────────────────────
function AllocationsTable({ allocations }) {
  const [search, setSearch] = useState('')
  const filtered = (allocations || []).filter(a => {
    if (!search) return true
    const q = search.toLowerCase()
    return (
      a.vessel_id?.toLowerCase().includes(q) ||
      a.assigned_berth?.toLowerCase().includes(q) ||
      a.berth_name?.toLowerCase().includes(q) ||
      a.port_name?.toLowerCase().includes(q)
    )
  })

  const portGroups = groupByPort(filtered, a => ({ portId: a.port_id, portName: a.port_name }))

  return (
    <>
      <div className="flex items-center gap-3 p-4 border-b border-gray-50">
        <div className="relative flex-1 max-w-xs">
          <i className="fa-solid fa-search absolute left-3 top-1/2 -translate-y-1/2 text-gray-300 text-xs" />
          <input type="text" placeholder="Search vessel, berth or port…" value={search} onChange={e => setSearch(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-400" />
        </div>
        <span className="text-xs text-gray-400">{filtered.length} records</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-xs text-gray-500 uppercase tracking-wide border-b border-gray-100">
              {['Vessel', 'Berth', 'Berthing Start', 'Departure', 'Wait', 'Utilization', 'Flags', 'ETA'].map(h => (
                <th key={h} className="px-4 py-3 text-left font-semibold whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {portGroups.length === 0 ? null : portGroups.map(({ portId, portName, items: portAllocs }) => (
              <>
                <tr key={`hdr-${portId}`} className="bg-blue-50/60 border-t border-b border-blue-100">
                  <td colSpan={8} className="px-4 py-2">
                    <div className="flex items-center gap-2">
                      <i className="fa-solid fa-anchor text-blue-500 text-xs" />
                      <span className="text-xs font-bold text-blue-700 uppercase tracking-wide">{portName}</span>
                      <span className="text-[10px] text-blue-400 font-normal">{portAllocs.length} allocation{portAllocs.length !== 1 ? 's' : ''}</span>
                    </div>
                  </td>
                </tr>
                {portAllocs.map((a, i) => (
                  <tr key={a.visit_id || `${portId}-${i}`} className="hover:bg-blue-50/20 transition-colors border-b border-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900 text-xs truncate max-w-[160px]" title={a.vessel_id}>{a.vessel_id}</td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1.5 px-2 py-1 bg-blue-50 text-blue-700 rounded-md text-xs font-medium" title={a.berth_name}>
                        <i className="fa-solid fa-anchor text-[10px]" />
                        {a.berth_name || a.assigned_berth || '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs whitespace-nowrap">{fmtDt(a.berthing_start_time)}</td>
                    <td className="px-4 py-3 text-gray-600 text-xs whitespace-nowrap">{fmtDt(a.departure_time)}</td>
                    <td className="px-4 py-3 text-xs">
                      <span className={`font-semibold ${a.waiting_time_minutes > 60 ? 'text-red-600' : a.waiting_time_minutes > 30 ? 'text-amber-600' : 'text-green-600'}`}>
                        {fmtMin(a.waiting_time_minutes)}
                      </span>
                    </td>
                    <td className="px-4 py-3 min-w-[100px]"><UtilBar util={a.berth_utilization} /></td>
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        {a.conflict_flag   && <StatusChip flag={true} trueLabel="Conflict"  falseLabel="" trueColor="red" />}
                        {a.congestion_flag && <StatusChip flag={true} trueLabel="Congested" falseLabel="" trueColor="orange" />}
                        {!a.conflict_flag && !a.congestion_flag && <StatusChip flag={false} trueLabel="" falseLabel="Clear" falseColor="green" />}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-400 text-xs whitespace-nowrap">{fmtDt(a.eta)}</td>
                  </tr>
                ))}
              </>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="py-12 text-center text-gray-400 text-sm">
            <i className="fa-solid fa-anchor text-3xl block mb-3 opacity-20" />
            {search ? 'No matches found.' : 'No active allocations yet.'}
          </div>
        )}
      </div>
    </>
  )
}

// ── Berth Heatmap ─────────────────────────────────────────────────────────────
function BerthHeatmap({ berths }) {
  if (!berths || berths.length === 0) return (
    <div className="py-16 text-center text-gray-400 text-sm">
      <i className="fa-solid fa-border-all text-4xl block mb-3 opacity-20" />
      No berths loaded.
    </div>
  )
  const portGroups = groupByPort(berths, b => ({ portId: b.port_id, portName: b.port_name }))
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-5 text-xs text-gray-500 flex-wrap">
        <span className="flex items-center gap-1.5"><span className="w-4 h-4 rounded bg-gray-200 inline-block" />Empty (0%)</span>
        <span className="flex items-center gap-1.5"><span className="w-4 h-4 rounded bg-emerald-400 inline-block" />Low (1–65%)</span>
        <span className="flex items-center gap-1.5"><span className="w-4 h-4 rounded bg-yellow-400 inline-block" />Medium (65–85%)</span>
        <span className="flex items-center gap-1.5"><span className="w-4 h-4 rounded bg-red-500 inline-block" />High (&gt;85%)</span>
        <span className="flex items-center gap-1.5"><span className="w-4 h-4 rounded bg-amber-300 inline-block ring-2 ring-amber-500" />Queued</span>
      </div>
      {portGroups.map(({ portId, portName, items: portBerths }) => {
        const avgUtil = portBerths.reduce((s, b) => s + (b.berth_utilization || 0), 0) / portBerths.length
        const occupied = portBerths.filter(b => (b.berth_utilization || 0) > 0.1).length
        const available = portBerths.length - occupied
        return (
          <CardContainer key={portId} className="p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-bold text-gray-900 text-base">{portName}</h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  {portBerths.length} berths · <span className="text-blue-600 font-medium">{occupied} occupied</span> · <span className="text-emerald-600 font-medium">{available} available</span>
                </p>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-400 mb-1">Avg utilization</p>
                <div className="w-32"><UtilBar util={avgUtil} /></div>
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {portBerths.map(b => {
                const util = b.berth_utilization || 0
                const p = Math.round(util * 100)
                const hasQueue = b.berth_queue_length > 0
                const colClass = p === 0 ? 'bg-gray-200 hover:bg-gray-300'
                  : p > 85 ? 'bg-red-500 hover:bg-red-600'
                  : p > 65 ? 'bg-yellow-400 hover:bg-yellow-500'
                  : 'bg-emerald-400 hover:bg-emerald-500'
                return (
                  <div key={b.berth_id} className="relative group">
                    <div
                      className={`w-8 h-8 rounded-md cursor-default transition-all duration-150 ${colClass} ${hasQueue ? 'ring-2 ring-amber-400' : ''}`}
                      title={`${b.berth_name || b.berth_id} — ${p}%${hasQueue ? ` · ${b.berth_queue_length} queued` : ''}`}
                    >
                      <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 px-1.5 py-0.5 bg-gray-900 text-white text-[10px] rounded whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-20 font-mono">
                        {berthShortLabel(b.berth_id)} {p}%
                      </span>
                    </div>
                    {hasQueue && <span className="absolute -top-1 -right-1 w-3 h-3 bg-amber-400 rounded-full border border-white" />}
                  </div>
                )
              })}
            </div>
          </CardContainer>
        )
      })}
    </div>
  )
}

// ── Gantt Chart ───────────────────────────────────────────────────────────────
function GanttChart({ allocations }) {
  if (!allocations || allocations.length === 0) return (
    <div className="py-16 text-center text-gray-400 text-sm">
      <i className="fa-solid fa-chart-gantt text-4xl block mb-3 opacity-20" />No allocations yet.
    </div>
  )
  const validAllocs = allocations.filter(a => a.berthing_start_time && a.departure_time)
  if (validAllocs.length === 0) return (
    <div className="py-16 text-center text-gray-400 text-sm">
      <i className="fa-solid fa-chart-gantt text-4xl block mb-3 opacity-20" />Allocations have no timing data yet.
    </div>
  )
  const now = new Date()
  const starts = validAllocs.map(a => new Date(a.berthing_start_time).getTime())
  const ends   = validAllocs.map(a => new Date(a.departure_time).getTime())
  const rawMin = Math.min(...starts), rawMax = Math.max(...ends)
  const span   = rawMax - rawMin || 3_600_000
  const viewStart = rawMin - span * 0.04, viewEnd = rawMax + span * 0.04, viewSpan = viewEnd - viewStart
  function toPct(ts) { return Math.max(0, Math.min(100, ((new Date(ts).getTime() - viewStart) / viewSpan) * 100)) }
  const NUM_TICKS = 6
  const ticks = Array.from({ length: NUM_TICKS }, (_, i) => new Date(viewStart + (viewSpan * i) / (NUM_TICKS - 1)))
  const sameDay = ticks[0].toDateString() === ticks[NUM_TICKS - 1].toDateString()
  function fmtTick(d) {
    return sameDay
      ? d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }
  const nowPct = toPct(now), nowVisible = nowPct > 0 && nowPct < 100
  const portGroups = groupByPort(validAllocs, a => ({ portId: a.port_id, portName: a.port_name }))

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-5 text-xs text-gray-500 flex-wrap">
        <span className="flex items-center gap-1.5"><span className="w-4 h-2 rounded bg-blue-500 inline-block" />Normal</span>
        <span className="flex items-center gap-1.5"><span className="w-4 h-2 rounded bg-red-500 inline-block" />Conflict</span>
        <span className="flex items-center gap-1.5"><span className="w-4 h-2 rounded bg-orange-400 inline-block" />Congested</span>
        {nowVisible && <span className="flex items-center gap-1.5"><span className="w-px h-4 bg-red-400 inline-block" />Now</span>}
      </div>
      {portGroups.map(({ portId, portName, items: portAllocs }) => (
        <CardContainer key={portId} className="p-5">
          <h3 className="font-bold text-gray-900 mb-4">{portName}
            <span className="ml-2 text-xs font-normal text-gray-400">{portAllocs.length} vessel{portAllocs.length !== 1 ? 's' : ''}</span>
          </h3>
          <div className="flex pl-32 mb-1 pr-2">
            {ticks.map((t, i) => (
              <div key={i} className="flex-1 text-[10px] text-gray-400 text-center first:text-left last:text-right whitespace-nowrap">{fmtTick(t)}</div>
            ))}
          </div>
          <div className="space-y-1.5">
            {portAllocs.map((a, i) => {
              const leftPct  = toPct(a.berthing_start_time)
              const rightPct = toPct(a.departure_time)
              const widthPct = Math.max(0.8, rightPct - leftPct)
              const barCol = a.conflict_flag ? 'bg-red-500' : a.congestion_flag ? 'bg-orange-400' : 'bg-blue-500'
              return (
                <div key={a.visit_id || i} className="flex items-center gap-2">
                  <span className="text-xs text-gray-700 font-medium w-28 flex-shrink-0 truncate" title={a.vessel_id}>{a.vessel_id}</span>
                  <div className="flex-1 relative h-7 bg-gray-100 rounded-lg overflow-hidden">
                    {ticks.slice(1, -1).map((_, ti) => (
                      <div key={ti} className="absolute top-0 bottom-0 w-px bg-gray-200"
                        style={{ left: `${(ti + 1) * (100 / (NUM_TICKS - 1))}%` }} />
                    ))}
                    {nowVisible && <div className="absolute top-0 bottom-0 w-0.5 bg-red-400 z-10" style={{ left: `${nowPct}%` }} />}
                    <div
                      className={`absolute top-1 bottom-1 ${barCol} rounded flex items-center px-1.5 overflow-hidden cursor-default`}
                      style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                      title={`${a.vessel_id} · ${a.berth_name || a.assigned_berth} · ${fmtDt(a.berthing_start_time)} → ${fmtDt(a.departure_time)} · wait ${fmtMin(a.waiting_time_minutes)}`}
                    >
                      <span className="text-white text-[10px] font-mono truncate leading-none">{berthShortLabel(a.assigned_berth)}</span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </CardContainer>
      ))}
    </div>
  )
}

// ── Vessel Pipeline ───────────────────────────────────────────────────────────
function VesselPipeline({ allocations }) {
  const now = new Date()
  function categorize(a) {
    const start = new Date(a.berthing_start_time)
    const end   = new Date(a.departure_time)
    if (isNaN(start.getTime()) || start > now) return 'incoming'
    if (!isNaN(end.getTime()) && end < now)    return 'departed'
    return 'berthing'
  }
  const incoming = [...allocations].filter(a => categorize(a) === 'incoming')
    .sort((a, b) => new Date(a.berthing_start_time) - new Date(b.berthing_start_time))
  const berthing = allocations.filter(a => categorize(a) === 'berthing')
  const departed = allocations.filter(a => categorize(a) === 'departed')
    .sort((a, b) => new Date(b.departure_time) - new Date(a.departure_time))

  const COLS = [
    { key:'incoming', label:'Incoming', count:incoming.length, items:incoming, icon:'fa-ship',         header:'bg-blue-50 border-blue-100 text-blue-700',         badge:'bg-blue-100 text-blue-700',       dot:'bg-blue-500 animate-pulse',     card:'border-blue-100'    },
    { key:'berthing', label:'At Berth', count:berthing.length, items:berthing, icon:'fa-anchor',       header:'bg-emerald-50 border-emerald-100 text-emerald-700', badge:'bg-emerald-100 text-emerald-700', dot:'bg-emerald-500 animate-pulse',  card:'border-emerald-100' },
    { key:'departed', label:'Departed', count:departed.length, items:departed, icon:'fa-circle-check', header:'bg-gray-50 border-gray-200 text-gray-500',         badge:'bg-gray-100 text-gray-500',       dot:'bg-gray-300',                   card:'border-gray-100'    },
  ]

  if (allocations.length === 0) return (
    <div className="py-16 text-center text-gray-400 text-sm">
      <i className="fa-solid fa-ship text-4xl block mb-3 opacity-20" />No vessels tracked yet.
    </div>
  )

  return (
    <div className="space-y-5">
      <CardContainer className="p-5">
        <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">
          <i className="fa-solid fa-stopwatch mr-1.5 text-amber-500" />Wait Time Ranking
        </p>
        <div className="space-y-2">
          {[...allocations]
            .filter(a => a.waiting_time_minutes != null)
            .sort((a, b) => b.waiting_time_minutes - a.waiting_time_minutes)
            .slice(0, 8)
            .map((a, i) => {
              const maxWait = Math.max(...allocations.map(x => x.waiting_time_minutes || 0))
              const p = maxWait > 0 ? (a.waiting_time_minutes / maxWait) * 100 : 0
              const barCol = a.waiting_time_minutes > 60 ? 'bg-red-500' : a.waiting_time_minutes > 30 ? 'bg-amber-400' : 'bg-emerald-400'
              return (
                <div key={a.visit_id || i} className="flex items-center gap-3">
                  <span className="text-[10px] font-bold text-gray-400 w-4 text-right flex-shrink-0">#{i + 1}</span>
                  <span className="text-xs font-medium text-gray-700 w-28 flex-shrink-0 truncate" title={a.vessel_id}>{a.vessel_id}</span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className={`${barCol} h-2 rounded-full transition-all`} style={{ width: `${p}%` }} />
                  </div>
                  <span className={`text-xs font-semibold w-14 text-right flex-shrink-0 ${a.waiting_time_minutes > 60 ? 'text-red-600' : a.waiting_time_minutes > 30 ? 'text-amber-600' : 'text-emerald-600'}`}>
                    {fmtMin(a.waiting_time_minutes)}
                  </span>
                  <span className="text-[10px] text-gray-400 w-32 flex-shrink-0 truncate" title={a.berth_name}>{a.berth_name || a.assigned_berth || '—'}</span>
                </div>
              )
            })}
        </div>
      </CardContainer>

      <div className="grid grid-cols-3 gap-4">
        {COLS.map(col => (
          <div key={col.key} className="flex flex-col gap-3">
            <div className={`flex items-center gap-2 p-3 rounded-xl border ${col.header}`}>
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${col.dot}`} />
              <i className={`fa-solid ${col.icon} text-sm`} />
              <span className="font-bold text-sm">{col.label}</span>
              <span className={`ml-auto text-xs px-2 py-0.5 rounded-full font-semibold ${col.badge}`}>{col.count}</span>
            </div>
            <div className="space-y-2 max-h-[620px] overflow-y-auto pr-0.5">
              {col.items.length === 0 ? (
                <div className="text-center py-10 text-gray-400 text-xs">
                  <i className={`fa-solid ${col.icon} text-2xl block mb-2 opacity-20`} />None
                </div>
              ) : col.items.map((a, i) => (
                <div key={a.visit_id || i}
                  className={`p-3.5 rounded-xl border bg-white shadow-sm hover:shadow-md transition-shadow ${a.conflict_flag ? 'border-red-200' : col.card}`}>
                  <div className="flex items-start justify-between mb-2.5">
                    <div className="min-w-0 flex-1">
                      <p className="font-bold text-gray-900 text-sm leading-tight truncate" title={a.vessel_id}>{a.vessel_id}</p>
                      <p className="text-[11px] text-gray-400 mt-0.5 truncate">{a.berth_name || a.assigned_berth || '—'} · {a.port_name || '—'}</p>
                    </div>
                    {a.conflict_flag && <span className="flex-shrink-0 ml-1 text-[10px] px-1.5 py-0.5 bg-red-50 text-red-600 border border-red-100 rounded-full font-medium">⚡ Conflict</span>}
                    {a.congestion_flag && !a.conflict_flag && <span className="flex-shrink-0 ml-1 text-[10px] px-1.5 py-0.5 bg-orange-50 text-orange-600 border border-orange-100 rounded-full font-medium">🔶 Congested</span>}
                  </div>
                  <div className="space-y-1 text-xs mb-2.5">
                    <div className="flex justify-between"><span className="text-gray-400">Berth start</span><span className="font-medium text-gray-700">{fmtDt(a.berthing_start_time)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Departure</span><span className="font-medium text-gray-700">{fmtDt(a.departure_time)}</span></div>
                    <div className="flex justify-between"><span className="text-gray-400">Wait</span>
                      <span className={`font-semibold ${a.waiting_time_minutes > 60 ? 'text-red-600' : a.waiting_time_minutes > 30 ? 'text-amber-500' : 'text-emerald-600'}`}>
                        {fmtMin(a.waiting_time_minutes)}
                      </span>
                    </div>
                  </div>
                  <UtilBar util={a.berth_utilization} />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────
const VIEWS = ['Overview', 'Heatmap', 'Gantt', 'Vessel Pipeline', 'Berth Board', 'Vessel Queue']

export default function PortOperations() {
  const [view, setView] = useState('Overview')

  const { data: kpisRaw,   isLoading: kpisLoading,   refetch: refetchKpis   } = usePortKpis()
  const { data: statusRaw, isLoading: statusLoading, refetch: refetchStatus } = useBerthStatus()
  const { data: allocRaw,  isLoading: allocLoading,  refetch: refetchAlloc  } = usePortAllocations()
  const { data: healthRaw                                                    } = usePortOpsHealth()

  function refetchAll() { refetchKpis(); refetchStatus(); refetchAlloc() }

  const kpis        = kpisRaw   || {}
  const berths      = statusRaw?.berths || []
  const allocations = allocRaw?.allocations || []
  const health      = healthRaw || {}

  const conflictCount   = allocations.filter(a => a.conflict_flag).length
  const congestionCount = allocations.filter(a => a.congestion_flag).length
  const isHistorical    = kpis.kpi_mode === 'recent'

  const kpiCards = [
    {
      label: isHistorical ? 'Recent Vessels' : 'Active Vessels',
      value: isHistorical ? allocations.length : (kpis.active_vessels ?? allocations.length),
      icon: 'fa-ship', bg: 'bg-blue-50', color: 'text-blue-600',
      sub: isHistorical ? 'last 100 completed visits' : `${allocations.length} tracked allocations`,
    },
    {
      label: 'Avg Wait Time',
      value: kpis.avg_waiting_time_minutes != null ? fmtMin(kpis.avg_waiting_time_minutes) : '—',
      icon: 'fa-clock', bg: 'bg-yellow-50', color: 'text-yellow-600',
      sub: isHistorical ? 'recent 500 visits avg' : 'across active vessels',
    },
    {
      label: 'Avg Berth Utilization',
      value: kpis.avg_berth_utilization != null ? pct(kpis.avg_berth_utilization) : '—',
      icon: 'fa-anchor', bg: 'bg-green-50', color: 'text-green-600',
      sub: `${berths.length} berths · ${isHistorical ? 'historical' : 'live'}`,
    },
    {
      label: 'Conflicts / Congestion',
      value: `${conflictCount} / ${congestionCount}`,
      icon: 'fa-triangle-exclamation',
      bg: conflictCount > 0 ? 'bg-red-50' : 'bg-gray-50',
      color: conflictCount > 0 ? 'text-red-600' : 'text-gray-400',
      sub: isHistorical ? 'in recent sample' : 'conflict / congestion flags',
    },
    {
      label: 'Completed Visits',
      value: (kpis.completed_visits ?? kpis.total_allocations ?? allocations.length).toLocaleString(),
      icon: 'fa-clipboard-list', bg: 'bg-purple-50', color: 'text-purple-600',
      sub: 'total historical operations',
    },
    {
      label: 'Conflict Rate',
      value: kpis.conflict_rate != null ? pct(kpis.conflict_rate) : '—',
      icon: 'fa-chart-pie', bg: 'bg-orange-50', color: 'text-orange-600',
      sub: isHistorical ? 'recent sample rate' : 'of all allocations',
    },
  ]

  const loading = kpisLoading || statusLoading || allocLoading

  return (
    <MainLayout>
      <Navbar
        title="Port Operations"
        subtitle={`${berths.length} berths · ${isHistorical ? `${(kpis.completed_visits ?? 0).toLocaleString()} historical ops` : `${allocations.length} active allocations`}`}
      >
        <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border ${
          health.status === 'healthy' ? 'bg-green-50 text-green-700 border-green-100' : 'bg-gray-50 text-gray-500 border-gray-100'
        }`}>
          <span className={`w-1.5 h-1.5 rounded-full ${health.status === 'healthy' ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} />
          {health.status === 'healthy' ? 'DB Connected' : 'Connecting…'}
        </span>
        <Button variant="secondary" size="sm" onClick={refetchAll} disabled={loading}>
          <i className={`fa-solid fa-rotate-right mr-1 ${loading ? 'fa-spin' : ''}`} />Refresh
        </Button>
      </Navbar>

      <div className="flex-1 p-6 overflow-auto space-y-5">

        {isHistorical && (
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-blue-100 bg-blue-50/60 text-sm text-blue-700">
            <i className="fa-solid fa-circle-info text-blue-400 flex-shrink-0" />
            <span>
              <strong>Historical mode</strong> — no vessels currently active at port.
              KPIs sourced from the <strong>{(kpis.completed_visits ?? 0).toLocaleString()}-visit dataset</strong>.
            </span>
          </div>
        )}

        <div className="flex gap-1 border-b border-gray-200">
          {VIEWS.map(v => (
            <button key={v} onClick={() => setView(v)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-all whitespace-nowrap ${
                view === v ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}>
              {v === 'Overview'        && <><i className="fa-solid fa-gauge-high mr-1.5" />{v}</>}
              {v === 'Heatmap'         && <><i className="fa-solid fa-border-all mr-1.5" />{v}</>}
              {v === 'Gantt'           && <><i className="fa-solid fa-chart-gantt mr-1.5" />{v}</>}
              {v === 'Vessel Pipeline' && <><i className="fa-solid fa-ship mr-1.5" />{v}</>}
              {v === 'Berth Board'     && <><i className="fa-solid fa-anchor mr-1.5" />{v}</>}
              {v === 'Vessel Queue'    && <><i className="fa-solid fa-list mr-1.5" />{v}</>}
            </button>
          ))}
        </div>

        {/* ══ OVERVIEW ══════════════════════════════════════════════════════════ */}
        {view === 'Overview' && (
          <>
            <div className="grid grid-cols-3 gap-4">
              {kpiCards.map(k => (
                <CardContainer key={k.label} className="p-4">
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 ${k.bg} rounded-xl flex items-center justify-center flex-shrink-0`}>
                      <i className={`fa-solid ${k.icon} ${k.color} text-sm`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-gray-500">{k.label}</p>
                      <p className="text-2xl font-bold text-gray-900 leading-tight">{k.value}</p>
                      <p className="text-[11px] text-gray-400 mt-0.5">{k.sub}</p>
                    </div>
                  </div>
                </CardContainer>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-5">
              <CardContainer>
                <div className="p-4 border-b border-gray-50 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900 text-sm"><i className="fa-solid fa-anchor mr-1.5 text-blue-500" />Berth Status</h3>
                  <span className="text-xs text-gray-400">{berths.length} berths</span>
                </div>
                {statusLoading ? (
                  <div className="p-8 text-center text-gray-400 text-sm"><i className="fa-solid fa-spinner fa-spin mr-2" />Loading…</div>
                ) : (
                  <div className="p-4 space-y-4 max-h-96 overflow-y-auto">
                    {berths.length === 0 ? (
                      <p className="text-sm text-gray-400 text-center py-6">No berths loaded.</p>
                    ) : groupByPort(berths, b => ({ portId: b.port_id, portName: b.port_name })).map(({ portId, portName, items: portBerths }) => (
                      <div key={portId}>
                        <div className="flex items-center gap-2 mb-2">
                          <span className="text-[11px] font-bold text-blue-600 uppercase tracking-wide whitespace-nowrap">{portName}</span>
                          <div className="flex-1 h-px bg-gray-100" />
                          <span className="text-[10px] text-gray-400 whitespace-nowrap">{portBerths.length} berths</span>
                        </div>
                        <div className="space-y-1.5 pl-1">
                          {portBerths.map(b => (
                            <div key={b.berth_id} className="flex items-center gap-3">
                              <span className="text-xs text-gray-600 w-36 flex-shrink-0 truncate" title={b.berth_name}>{b.berth_name || b.berth_id}</span>
                              <div className="flex-1"><UtilBar util={b.berth_utilization ?? 0} /></div>
                              {b.berth_queue_length > 0 && (
                                <span className="text-[10px] bg-amber-50 text-amber-600 px-1.5 py-0.5 rounded border border-amber-100 flex-shrink-0">Q:{b.berth_queue_length}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContainer>

              <CardContainer>
                <div className="p-4 border-b border-gray-50 flex items-center justify-between">
                  <h3 className="font-semibold text-gray-900 text-sm"><i className="fa-solid fa-bell mr-1.5 text-orange-500" />Conflicts & Alerts</h3>
                  <span className="text-xs text-gray-400">{allocations.length} allocations</span>
                </div>
                <div className="p-4 space-y-2 max-h-80 overflow-y-auto">
                  {allocations.filter(a => a.conflict_flag || a.congestion_flag).length === 0 ? (
                    <div className="text-center py-8">
                      <i className="fa-solid fa-circle-check text-3xl text-green-400 block mb-2 opacity-60" />
                      <p className="text-sm text-gray-500 font-medium">All clear</p>
                      <p className="text-xs text-gray-400">No conflicts or alerts detected</p>
                    </div>
                  ) : allocations.filter(a => a.conflict_flag || a.congestion_flag).map(a => (
                    <div key={a.visit_id} className="p-3 rounded-lg border border-gray-100 bg-gray-50">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-gray-800 truncate" title={a.vessel_id}>{a.vessel_id}</span>
                        <span className="text-xs text-gray-400 ml-2 flex-shrink-0">{a.berth_name || a.assigned_berth}</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {a.conflict_flag   && <StatusChip flag={true} trueLabel="Conflict"  falseLabel="" trueColor="red" />}
                        {a.congestion_flag && <StatusChip flag={true} trueLabel="Congested" falseLabel="" trueColor="orange" />}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContainer>
            </div>

            <CardContainer className="p-5">
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-4">
                <i className="fa-solid fa-lightbulb mr-1.5 text-amber-400" />AI Operational Insights
              </p>
              <div className="grid grid-cols-3 gap-4">
                <div className={`p-4 rounded-xl border ${(kpis.avg_waiting_time_minutes || 0) > 60 ? 'border-red-100 bg-red-50' : 'border-green-100 bg-green-50'}`}>
                  <p className="text-xs font-semibold text-gray-700 mb-1">Waiting Time Status</p>
                  <p className={`text-sm ${(kpis.avg_waiting_time_minutes || 0) > 60 ? 'text-red-700' : 'text-green-700'}`}>
                    {(kpis.avg_waiting_time_minutes || 0) > 60
                      ? `High wait times detected (avg ${fmtMin(kpis.avg_waiting_time_minutes)}). Consider pre-emptive berth reallocation.`
                      : `Wait times within normal range (avg ${fmtMin(kpis.avg_waiting_time_minutes || 0)}). Port operating efficiently.`}
                  </p>
                </div>
                <div className={`p-4 rounded-xl border ${(kpis.avg_berth_utilization || 0) > 0.85 ? 'border-orange-100 bg-orange-50' : 'border-blue-100 bg-blue-50'}`}>
                  <p className="text-xs font-semibold text-gray-700 mb-1">Berth Utilization</p>
                  <p className={`text-sm ${(kpis.avg_berth_utilization || 0) > 0.85 ? 'text-orange-700' : 'text-blue-700'}`}>
                    {(kpis.avg_berth_utilization || 0) > 0.85
                      ? `Critical utilization (${pct(kpis.avg_berth_utilization)}). Berths near capacity — delay risk is high.`
                      : `Utilization healthy at ${pct(kpis.avg_berth_utilization || 0)}. Adequate capacity available.`}
                  </p>
                </div>
                <div className={`p-4 rounded-xl border ${conflictCount > 0 ? 'border-red-100 bg-red-50' : 'border-green-100 bg-green-50'}`}>
                  <p className="text-xs font-semibold text-gray-700 mb-1">Schedule Health</p>
                  <p className={`text-sm ${conflictCount > 0 ? 'text-red-700' : 'text-green-700'}`}>
                    {conflictCount > 0
                      ? `${conflictCount} scheduling conflict${conflictCount > 1 ? 's' : ''} active. Review vessel queue for overlap.`
                      : 'No scheduling conflicts. Berth assignments are clean.'}
                  </p>
                </div>
              </div>
            </CardContainer>
          </>
        )}

        {view === 'Heatmap' && (
          <>
            <p className="text-sm text-gray-500">Color-coded occupancy for all <strong>{berths.length}</strong> berths across every port</p>
            {statusLoading ? <div className="py-12 text-center text-gray-400"><i className="fa-solid fa-spinner fa-spin mr-2" />Loading berth data…</div>
              : <BerthHeatmap berths={berths} />}
          </>
        )}

        {view === 'Gantt' && (
          <>
            <p className="text-sm text-gray-500">Vessel berthing windows across all ports — hover bars for detail</p>
            {allocLoading ? <div className="py-12 text-center text-gray-400"><i className="fa-solid fa-spinner fa-spin mr-2" />Loading timeline…</div>
              : <GanttChart allocations={allocations} />}
          </>
        )}

        {view === 'Vessel Pipeline' && (
          <>
            <p className="text-sm text-gray-500">Live vessel status — <strong>{allocations.length}</strong> tracked vessels</p>
            {allocLoading ? <div className="py-12 text-center text-gray-400"><i className="fa-solid fa-spinner fa-spin mr-2" />Loading vessel data…</div>
              : <VesselPipeline allocations={allocations} />}
          </>
        )}

        {view === 'Berth Board' && (
          <>
            <p className="text-sm text-gray-500">Live occupancy for <strong>{berths.length}</strong> registered berths</p>
            {statusLoading ? <div className="py-12 text-center text-gray-400"><i className="fa-solid fa-spinner fa-spin mr-2" />Loading berth status…</div>
              : <BerthBoard berths={berths} allocations={allocations} />}
          </>
        )}

        {view === 'Vessel Queue' && (
          <CardContainer>
            {allocLoading
              ? <div className="p-8 text-center text-gray-400"><i className="fa-solid fa-spinner fa-spin mr-2" />Loading allocations…</div>
              : <AllocationsTable allocations={allocations} />}
          </CardContainer>
        )}

      </div>
    </MainLayout>
  )
}
