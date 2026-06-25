import { useState, useRef, useMemo } from 'react'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { CardContainer, Button, SectionHeader } from '../components/ui'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { useBerths, useVessels, usePorts, useVisits, useCreateVisit } from '../hooks/queries'

const SLOT_COLORS = {
  available:   'bg-status-green text-white',
  occupied:    'bg-blue-600 text-white',
  maintenance: 'bg-status-yellow text-white',
  conflict:    'bg-status-red text-white',
}
const SLOT_LABELS = {
  available: 'Available', maintenance: 'Maintenance', conflict: 'Conflict!',
}

const TERMINAL = new Set(['completed', 'cancelled'])

// ── Time-slot helpers ─────────────────────────────────────────────────────────

function buildSlots(view) {
  const now = new Date()
  const todayStart = new Date(now)
  todayStart.setHours(0, 0, 0, 0)
  const DAY_NAMES = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const MON_NAMES = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
  const fmt = (d) => `${DAY_NAMES[d.getDay()]} ${d.getDate()} ${MON_NAMES[d.getMonth()]}`
  const H4 = 4 * 3600000
  const DAY = 86400000

  if (view === 'Today') {
    const boundaries = Array.from({ length: 6 }, (_, i) => ({
      start: new Date(todayStart.getTime() + i * H4),
      end:   new Date(todayStart.getTime() + (i + 1) * H4),
    }))
    return { boundaries, headers: ['Berth', '00–04', '04–08', '08–12', '12–16', '16–20', '20–24'] }
  }

  if (view === 'Week') {
    const boundaries = Array.from({ length: 7 }, (_, i) => ({
      start: new Date(todayStart.getTime() + i * DAY),
      end:   new Date(todayStart.getTime() + (i + 1) * DAY),
    }))
    return { boundaries, headers: ['Berth', ...boundaries.map(s => fmt(s.start))] }
  }

  // Month — 7 × 4-day buckets (28 days)
  const boundaries = Array.from({ length: 7 }, (_, i) => ({
    start: new Date(todayStart.getTime() + i * 4 * DAY),
    end:   new Date(todayStart.getTime() + (i + 1) * 4 * DAY),
  }))
  const headers = ['Berth', ...boundaries.map(s => {
    const e = new Date(s.end.getTime() - 1)
    return `${s.start.getDate()}/${s.start.getMonth()+1}–${e.getDate()}/${e.getMonth()+1}`
  })]
  return { boundaries, headers }
}

function overlaps(visit, slotStart, slotEnd) {
  const vStart = visit.eta ? new Date(visit.eta) : null
  if (!vStart) return false
  // Default 48-hour window if no ETD provided
  const vEnd = visit.etd ? new Date(visit.etd) : new Date(vStart.getTime() + 48 * 3600000)
  return vStart < slotEnd && vEnd > slotStart
}

export default function BerthAllocation() {
  const [view, setView]             = useState('Week')
  const [showModal, setShowModal]   = useState(false)
  const [saving, setSaving]         = useState(false)
  const [saveError, setSaveError]   = useState('')
  const [saveOk, setSaveOk]         = useState(false)
  const [portSearch, setPortSearch] = useState('')
  const [selectedPortId, setSelectedPortId] = useState('')

  const vesselIdRef = useRef()
  const berthIdRef  = useRef()
  const etaRef      = useRef()
  const etbRef      = useRef()
  const etdRef      = useRef()
  const cargoRef    = useRef()
  const notesRef    = useRef()

  const { data: berthData,  isLoading: berthsLoading  } = useBerths(0, 500)
  const { data: vesselData                            } = useVessels(0, 500)
  const { data: portData                              } = usePorts()
  const { data: visitData,  isLoading: visitsLoading  } = useVisits({ limit: 500 })
  const createVisit = useCreateVisit()

  const berthList  = berthData  || []
  const vesselList = vesselData || []
  const portList   = portData   || []
  const visitList  = visitData  || []

  // ── Derived data ──────────────────────────────────────────────────────────

  const vesselMap = useMemo(() => {
    const m = {}
    vesselList.forEach(v => { m[v.id] = v.name })
    return m
  }, [vesselList])

  const activeVisits = useMemo(
    () => visitList.filter(v => !TERMINAL.has(v.status)),
    [visitList]
  )

  const visitsByBerth = useMemo(() => {
    const m = {}
    activeVisits.forEach(v => {
      if (v.berth_id != null) {
        if (!m[v.berth_id]) m[v.berth_id] = []
        m[v.berth_id].push(v)
      }
    })
    return m
  }, [activeVisits])

  const { boundaries: slotBoundaries, headers: timeHeaders } = useMemo(
    () => buildSlots(view),
    [view]
  )

  const filteredPorts = useMemo(() => {
    if (!portSearch.trim()) return portList.slice(0, 50)
    const q = portSearch.toLowerCase()
    return portList.filter(p =>
      p.name?.toLowerCase().includes(q) ||
      p.country?.toLowerCase().includes(q) ||
      p.code?.toLowerCase().includes(q)
    ).slice(0, 50)
  }, [portList, portSearch])

  const occupied    = berthList.filter(b => b.status === 'occupied').length
  const available   = berthList.filter(b => b.status === 'available').length
  const maintenance = berthList.filter(b => b.status === 'maintenance').length
  const total       = berthList.length || 1

  const pieData = [
    { name: 'Occupied',    value: Math.round(occupied    / total * 100), color: '#3b82f6' },
    { name: 'Available',   value: Math.round(available   / total * 100), color: '#22c55e' },
    { name: 'Maintenance', value: Math.round(maintenance / total * 100), color: '#eab308' },
  ].filter(d => d.value > 0)

  // ── Per-berth slot computation ────────────────────────────────────────────
  // berth.status IS the single source of truth for current occupancy.
  // Visits are used only to enrich vessel names and show future bookings.

  function getSlotsForBerth(berth) {
    if (berth.status === 'maintenance') {
      return slotBoundaries.map(() => ({ state: 'maintenance', label: null }))
    }

    const visits = visitsByBerth[berth.id] || []

    if (berth.status === 'occupied') {
      // Find vessel name from the most recent non-terminal visit for this berth
      const enrichVisit = visits[0]   // visitsByBerth already filtered to active visits
      const rawName     = enrichVisit ? (vesselMap[enrichVisit.vessel_id] || null) : null
      const label       = rawName ? rawName.replace(/^(MV|SS|MT|MS)\s+/i, '') : 'Occupied'

      // Mark every slot occupied — we don't know the ETD without visit data
      // Future visits for this berth will show as conflict if they overlap
      return slotBoundaries.map(({ start, end }) => {
        const futureHits = visits.filter(v => overlaps(v, start, end))
        if (futureHits.length > 1) return { state: 'conflict', label: `${futureHits.length} visits` }
        return { state: 'occupied', label }
      })
    }

    // Available berth — check visits API for scheduled future windows
    return slotBoundaries.map(({ start, end }) => {
      const hits = visits.filter(v => overlaps(v, start, end))
      if (hits.length === 0) return { state: 'available', label: null }
      if (hits.length > 1)   return { state: 'conflict',  label: `${hits.length} visits` }
      const name = vesselMap[hits[0].vessel_id] || `Vessel #${hits[0].vessel_id}`
      return { state: 'occupied', label: name.replace(/^(MV|SS|MT|MS)\s+/i, '') }
    })
  }

  // ── Modal handlers ────────────────────────────────────────────────────────

  function openModal() {
    setSaveError(''); setSaveOk(false); setPortSearch(''); setSelectedPortId('')
    setShowModal(true)
  }

  async function handleCreate(e) {
    e.preventDefault()
    setSaveError('')
    setSaving(true)
    try {
      await createVisit.mutateAsync({
        vessel_id:  Number(vesselIdRef.current.value),
        berth_id:   berthIdRef.current.value   ? Number(berthIdRef.current.value)   : undefined,
        port_id:    selectedPortId              ? Number(selectedPortId)              : undefined,
        eta:        etaRef.current.value       || undefined,
        etb:        etbRef.current.value       || undefined,
        etd:        etdRef.current.value       || undefined,
        cargo_type: cargoRef.current.value     || undefined,
        notes:      notesRef.current.value     || undefined,
      })
      setSaveOk(true)
      setTimeout(() => setShowModal(false), 1200)
    } catch (err) {
      setSaveError(err.message || 'Failed to create assignment.')
    } finally {
      setSaving(false)
    }
  }

  const loading  = berthsLoading || visitsLoading
  const colStyle = { gridTemplateColumns: `1.5fr repeat(${slotBoundaries.length}, 1fr)` }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <MainLayout>
      <Navbar title="Berth Management Board" subtitle="AI-powered berth allocation and scheduling optimization">
        <Button variant="primary" onClick={openModal}>
          <i className="fa-solid fa-plus" /> New Assignment
        </Button>
      </Navbar>

      {/* Control Panel */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option>All Terminals</option>
            </select>
          </div>
          <div className="flex items-center space-x-4 text-sm">
            {[['bg-status-green','Available'],['bg-blue-600','Occupied'],['bg-status-yellow','Maintenance'],['bg-status-red','Conflict']].map(([c,l]) => (
              <div key={l} className="flex items-center space-x-2">
                <div className={`w-3 h-3 ${c} rounded-full`} />
                <span className="text-gray-600">{l}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 p-6 overflow-auto">
        <div className="grid grid-cols-4 gap-6">

          {/* Left panel */}
          <div className="col-span-1 space-y-6">
            <CardContainer className="p-6">
              <SectionHeader title="Berth Utilization" />
              {pieData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} dataKey="value">
                        {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                      </Pie>
                      <Tooltip formatter={(v, n) => [`${v}%`, n]} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="mt-2 space-y-1.5">
                    {pieData.map(d => (
                      <div key={d.name} className="flex justify-between text-sm">
                        <span className="text-gray-600">{d.name}</span>
                        <span className="font-medium">{d.value}%</span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-gray-400">
                  <i className="fa-solid fa-anchor text-3xl mb-2 opacity-30" />
                  <p className="text-xs">No berths yet</p>
                </div>
              )}
            </CardContainer>

            <CardContainer className="p-4">
              <SectionHeader title="Summary" />
              <div className="space-y-2">
                {[
                  { label: 'Total Berths',  value: berthList.length,    color: 'text-gray-900' },
                  { label: 'Occupied',      value: occupied,             color: 'text-blue-600' },
                  { label: 'Available',     value: available,            color: 'text-status-green' },
                  { label: 'Maintenance',   value: maintenance,          color: 'text-status-yellow' },
                  { label: 'Active Visits', value: occupied,             color: 'text-blue-600' },
                ].map(s => (
                  <div key={s.label} className="flex justify-between text-sm">
                    <span className="text-gray-600">{s.label}</span>
                    <span className={`font-bold ${s.color}`}>{loading ? '…' : s.value}</span>
                  </div>
                ))}
              </div>
            </CardContainer>
          </div>

          {/* Berth Grid */}
          <div className="col-span-3">
            <CardContainer className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h3 className="text-lg font-semibold text-gray-900">Berth Assignment Board</h3>
                <div className="flex items-center space-x-2">
                  {['Today', 'Week', 'Month'].map(v => (
                    <button key={v} onClick={() => setView(v)}
                      className={`px-3 py-1 text-sm rounded ${view === v ? 'bg-blue-600 text-white' : 'border border-gray-300 hover:bg-gray-50'}`}>
                      {v}
                    </button>
                  ))}
                </div>
              </div>

              {/* Column headers */}
              <div className="grid gap-1 mb-2" style={colStyle}>
                {timeHeaders.map(h => (
                  <div key={h} className="text-xs font-medium text-gray-500 p-2 text-center first:text-left truncate">{h}</div>
                ))}
              </div>

              {/* Rows */}
              <div className="space-y-1">
                {loading && (
                  <div className="py-6 text-center text-gray-500">
                    <i className="fa-solid fa-spinner fa-spin mr-2" />Loading…
                  </div>
                )}
                {!loading && berthList.length === 0 && (
                  <div className="py-12 text-center text-gray-400">
                    <i className="fa-solid fa-anchor text-3xl mb-3 opacity-30 block" />
                    <p className="text-sm">No berths found. <button onClick={openModal} className="text-blue-600 underline">Create an assignment</button> to get started.</p>
                  </div>
                )}
                {berthList.map(b => {
                  const slots = getSlotsForBerth(b)
                  return (
                    <div key={b.id} className="grid gap-1" style={colStyle}>
                      <div className="bg-gray-50 p-2 rounded-lg flex items-center min-w-0">
                        <div className="min-w-0">
                          <p className="font-medium text-gray-900 text-xs truncate" title={b.name || b.code}>{b.name || b.code}</p>
                          <p className="text-xs text-gray-500 truncate">{(b.berth_type || '').replace(/_/g, ' ')}</p>
                        </div>
                      </div>
                      {slots.map((slot, i) => (
                        <div
                          key={i}
                          title={slot.label || SLOT_LABELS[slot.state] || slot.state}
                          className={`p-1 rounded text-xs font-medium flex items-center justify-center min-h-[40px] text-center ${SLOT_COLORS[slot.state]}`}
                        >
                          <span className="truncate leading-tight">
                            {slot.state === 'occupied' || slot.state === 'conflict'
                              ? slot.label
                              : SLOT_LABELS[slot.state] || ''}
                          </span>
                        </div>
                      ))}
                    </div>
                  )
                })}
              </div>
            </CardContainer>
          </div>
        </div>
      </div>

      {/* New Assignment Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-semibold text-gray-900">New Berth Assignment</h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <i className="fa-solid fa-times" />
              </button>
            </div>

            {saveOk ? (
              <div className="py-8 text-center text-status-green">
                <i className="fa-solid fa-circle-check text-4xl mb-3 block" />
                <p className="font-medium">Assignment created successfully!</p>
              </div>
            ) : (
              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Vessel <span className="text-red-500">*</span></label>
                  <select ref={vesselIdRef} required
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="">— Select vessel —</option>
                    {vesselList.map(v => <option key={v.id} value={v.id}>{v.name} {v.imo_number ? `(IMO ${v.imo_number})` : ''}</option>)}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Berth</label>
                  <select ref={berthIdRef}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="">— None —</option>
                    {berthList.map(b => (
                      <option key={b.id} value={b.id}>{b.code || b.name} ({b.status})</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Port <span className="text-gray-400 font-normal text-xs">({portList.length.toLocaleString()} available)</span>
                  </label>
                  <input
                    type="text"
                    placeholder="Type port name or country to search…"
                    value={portSearch}
                    onChange={e => { setPortSearch(e.target.value); setSelectedPortId('') }}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 mb-1"
                  />
                  {portSearch.trim() && (
                    <select
                      size={Math.min(filteredPorts.length + 1, 6)}
                      value={selectedPortId}
                      onChange={e => {
                        setSelectedPortId(e.target.value)
                        const p = portList.find(x => String(x.id) === e.target.value)
                        if (p) setPortSearch(`${p.name}${p.country ? ` (${p.country})` : ''}`)
                      }}
                      className="w-full border border-blue-300 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                    >
                      <option value="">— No port —</option>
                      {filteredPorts.map(p => (
                        <option key={p.id} value={p.id}>
                          {p.name}{p.country ? ` · ${p.country}` : ''}{p.code ? ` [${p.code}]` : ''}
                        </option>
                      ))}
                      {filteredPorts.length === 50 && <option disabled>… refine search to see more</option>}
                    </select>
                  )}
                  {selectedPortId && (
                    <p className="text-xs text-status-green mt-1">
                      <i className="fa-solid fa-check-circle mr-1" />Port selected (ID: {selectedPortId})
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {[['ETA', etaRef], ['ETB', etbRef], ['ETD', etdRef]].map(([label, ref]) => (
                    <div key={label}>
                      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
                      <input ref={ref} type="datetime-local"
                        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                  ))}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Cargo Type</label>
                  <select ref={cargoRef}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="">— Select —</option>
                    {['containers','bulk_dry','bulk_liquid','crude_oil','lng','lpg','ro_ro','general_cargo','breakbulk','project_cargo','refrigerated','vehicles'].map(t => (
                      <option key={t} value={t}>{t.replace(/_/g,' ').replace(/\b\w/g,c=>c.toUpperCase())}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                  <textarea ref={notesRef} rows={2} placeholder="Optional notes…"
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>

                {saveError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                    <i className="fa-solid fa-circle-exclamation mr-2" />{saveError}
                  </div>
                )}

                <div className="flex space-x-3 pt-2">
                  <button type="button" onClick={() => setShowModal(false)}
                    className="flex-1 py-2 px-4 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 text-sm font-medium">
                    Cancel
                  </button>
                  <button type="submit" disabled={saving}
                    className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-60">
                    {saving ? <><i className="fa-solid fa-spinner fa-spin mr-2" />Saving…</> : 'Create Assignment'}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </MainLayout>
  )
}
