import { useState, useRef, useCallback } from 'react'
import * as XLSX from 'xlsx'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { SmallStatCard, CardContainer, Button, Input, Select, Badge, StatusDot } from '../components/ui'
import { vesselsApi } from '../services/api'
import { useVessels, useCreateVessel, useDeleteVessel } from '../hooks/queries'

// ── Real backend enums ────────────────────────────────────────────────────────
const VESSEL_STATUSES = ['at_sea', 'approaching', 'anchored', 'berthed', 'departed']
const VESSEL_TYPES    = ['container', 'bulk_carrier', 'tanker', 'ro_ro', 'general_cargo', 'other']

function statusLabel(s) {
  const map = {
    at_sea:     'At Sea',
    approaching:'Approaching',
    anchored:   'Anchored',
    berthed:    'Berthed',
    departed:   'Departed',
  }
  return map[s] || s || '—'
}

function statusClass(s) {
  if (s === 'berthed')    return 'bg-green-100 text-green-700 border border-green-200'
  if (s === 'at_sea')     return 'bg-blue-100 text-blue-700 border border-blue-200'
  if (s === 'approaching')return 'bg-purple-100 text-purple-700 border border-purple-200'
  if (s === 'anchored')   return 'bg-yellow-100 text-yellow-700 border border-yellow-200'
  if (s === 'departed')   return 'bg-gray-100 text-gray-600 border border-gray-200'
  return 'bg-gray-100 text-gray-600 border border-gray-200'
}

function statusDotColor(s) {
  if (s === 'berthed')     return 'bg-green-500'
  if (s === 'at_sea')      return 'bg-blue-500'
  if (s === 'approaching') return 'bg-purple-500'
  if (s === 'anchored')    return 'bg-yellow-500'
  if (s === 'departed')    return 'bg-gray-400'
  return 'bg-gray-400'
}

const typeVariant = { container:'blue', bulk_carrier:'purple', tanker:'yellow', ro_ro:'green', general_cargo:'default', other:'default' }
const typeLabel   = t => (t || '').replace(/_/g, ' ').replace(/\bro ro\b/, 'Ro-Ro')

// ── Import: column name normaliser ────────────────────────────────────────────
function mapColumns(headerRow) {
  const result = {}
  headerRow.forEach((h, i) => {
    const k = h.toString().trim().toLowerCase().replace(/[\s\-().]+/g, '_').replace(/_+/g, '_').replace(/^_|_$/g, '')
    // name
    if (/^(name|vessel_name|ship_name)$/.test(k))        result.name              = i
    // imo
    if (/^(imo|imo_number|imo_no)$/.test(k))             result.imo_number        = i
    // mmsi
    if (k === 'mmsi')                                     result.mmsi              = i
    // type
    if (/^(type|vessel_type|ship_type)$/.test(k))        result.vessel_type       = i
    // status
    if (k === 'status')                                   result.status            = i
    // flag / country
    if (/^(flag|country|flag_state)$/.test(k))           result.flag              = i
    // length — loa_m, loa, length_overall, length_m, length
    if (/^(loa|loa_m|length_overall|length_m|length)$/.test(k)) result.length_overall = i
    // beam
    if (/^(beam|beam_m)$/.test(k))                       result.beam              = i
    // draft
    if (/^(draft|draught|draft_m|max_draft)$/.test(k))   result.max_draft         = i
    // gross tonnage
    if (/^(gross_tonnage|grt|gt|grosstonnage)$/.test(k)) result.gross_tonnage     = i
    // deadweight
    if (/^(dwt|deadweight|deadweight_tonnage|dw_tonnage)$/.test(k)) result.deadweight_tonnage = i
    // owner
    if (k === 'owner')                                    result.owner             = i
    // year built
    if (/^(year_built|year|built)$/.test(k))             result.year_built        = i
    // vessel_id — use to derive name if name missing
    if (k === 'vessel_id')                                result._vessel_id        = i
  })
  return result
}

function normaliseType(raw) {
  if (!raw) return ''
  const s = raw.toString().trim().toLowerCase().replace(/[\s\-]+/g, '_')
  const aliases = {
    bulk:'bulk_carrier', bulker:'bulk_carrier', bulk_carrier:'bulk_carrier',
    ro_ro:'ro_ro', roro:'ro_ro', 'ro-ro':'ro_ro',
    general:'general_cargo', cargo:'general_cargo', general_cargo:'general_cargo',
    tanker:'tanker', container:'container', other:'other',
    passenger:'other', offshore:'other', tug:'other',
  }
  return aliases[s] || (['container','bulk_carrier','tanker','ro_ro','general_cargo','other'].includes(s) ? s : '')
}

function normaliseStatus(raw) {
  if (!raw) return ''
  const s = raw.toString().trim().toLowerCase().replace(/[\s\-]+/g, '_')
  const aliases = {
    at_sea:'at_sea', sea:'at_sea', underway:'at_sea', en_route:'at_sea', sailing:'at_sea',
    approaching:'approaching', inbound:'approaching',
    anchored:'anchored', at_anchor:'anchored', anchor:'anchored',
    berthed:'berthed', docked:'berthed', in_port:'berthed', moored:'berthed',
    departed:'departed', left:'departed', outbound:'departed',
  }
  return aliases[s] || (VESSEL_STATUSES.includes(s) ? s : '')
}

function parseNum(v) {
  if (v === null || v === undefined || v === '') return undefined
  const n = Number(v)
  return isNaN(n) || n < 0 ? null : n
}

function validateRow(raw, colMap, rowIdx, imosSeen) {
  const get = field => {
    const ci = colMap[field]
    if (ci === undefined) return ''
    const v = raw[ci]
    return v !== null && v !== undefined ? v.toString().trim() : ''
  }

  const issues = []
  const vessel = {}

  // Name — optional if vessel_id present
  const name = get('name')
  const vid  = get('_vessel_id')
  if (!name && !vid) {
    issues.push('No vessel name or vessel_id found')
  } else {
    vessel.name = name || `Vessel-${vid}`
  }

  // IMO — required by backend; generate from vessel_id if missing
  const rawImo = get('imo_number').replace(/\D/g, '')
  if (rawImo) {
    if (!/^\d{7}$/.test(rawImo)) issues.push(`IMO "${rawImo}" must be 7 digits`)
    else vessel.imo_number = rawImo
  } else if (vid) {
    // Synthesise a unique IMO-like key from vessel_id
    const synth = `SIM${vid.padStart(4,'0')}`.slice(0, 20)
    vessel.imo_number = synth
  } else {
    issues.push('IMO number is required (7 digits)')
  }

  // MMSI
  const mmsi = get('mmsi').replace(/\D/g, '')
  if (mmsi) {
    if (!/^\d{9}$/.test(mmsi)) issues.push(`MMSI "${mmsi}" must be 9 digits`)
    else vessel.mmsi = mmsi
  }

  // Type
  const rawType = get('vessel_type')
  if (rawType) {
    const vtype = normaliseType(rawType)
    if (!vtype) issues.push(`Unknown type "${rawType}"`)
    else vessel.vessel_type = vtype
  }
  if (!vessel.vessel_type) vessel.vessel_type = 'other'

  // Status
  const rawStatus = get('status')
  if (rawStatus) {
    const vstatus = normaliseStatus(rawStatus)
    if (!vstatus) issues.push(`Unknown status "${rawStatus}"`)
    else vessel.status = vstatus
  }

  // Flag
  const flag = get('flag'); if (flag) vessel.flag = flag

  // Dimensions — correct backend field names
  const lo = parseNum(get('length_overall'))
  if (lo === null) issues.push('Length is not a valid positive number')
  else if (lo !== undefined) vessel.length_overall = lo

  const bm = parseNum(get('beam'))
  if (bm === null) issues.push('Beam is not a valid positive number')
  else if (bm !== undefined) vessel.beam = bm

  const dr = parseNum(get('max_draft'))
  if (dr === null) issues.push('Draft is not a valid positive number')
  else if (dr !== undefined) vessel.max_draft = dr

  const gt = parseNum(get('gross_tonnage'))
  if (gt === null) issues.push('Gross tonnage is not a valid positive number')
  else if (gt !== undefined) vessel.gross_tonnage = gt

  const dwt = parseNum(get('deadweight_tonnage'))
  if (dwt !== null && dwt !== undefined) vessel.deadweight_tonnage = dwt

  const yb = parseNum(get('year_built'))
  if (yb !== null && yb !== undefined) vessel.year_built = Math.round(yb)

  const owner = get('owner'); if (owner) vessel.owner = owner

  // Within-file IMO duplicate check
  let dupInFile = false
  if (vessel.imo_number) {
    if (imosSeen.has(vessel.imo_number)) { issues.push(`Duplicate IMO within file`); dupInFile = true }
    else imosSeen.add(vessel.imo_number)
  }

  return { vessel, issues, dupInFile, rowIdx }
}

async function parseFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = e => {
      try {
        const wb = XLSX.read(new Uint8Array(e.target.result), { type: 'array' })
        resolve(XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]], { header: 1, defval: '' }))
      } catch (err) { reject(err) }
    }
    reader.onerror = reject
    reader.readAsArrayBuffer(file)
  })
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function VesselMonitoring() {
  const [search, setSearch]             = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [typeFilter, setTypeFilter]     = useState('all')

  // Add vessel modal
  const [showAdd, setShowAdd]   = useState(false)
  const [saving, setSaving]     = useState(false)
  const [saveErr, setSaveErr]   = useState('')
  const [saveOk, setSaveOk]     = useState(false)
  const nameRef   = useRef(); const imoRef    = useRef()
  const mmsiRef   = useRef(); const typeRef   = useRef()
  const statusRef = useRef(); const flagRef   = useRef()
  const lenRef    = useRef(); const beamRef   = useRef()
  const draftRef  = useRef(); const gtRef     = useRef()
  const ownerRef  = useRef(); const yearRef   = useRef()

  // Import modal
  const [showImport, setShowImport]         = useState(false)
  const [dragging, setDragging]             = useState(false)
  const [importLoading, setImportLoading]   = useState(false)
  const [importErr, setImportErr]           = useState('')
  const [analysis, setAnalysis]             = useState(null)
  const [progress, setProgress]             = useState(null)
  const [importDone, setImportDone]         = useState(false)
  const fileRef = useRef()

  const { data: vessels, isLoading: loading, error, refetch } = useVessels(0, 2000)
  const createVessel = useCreateVessel()
  const deleteVessel = useDeleteVessel()
  const list = vessels || []

  const filtered = list.filter(v => {
    const q = search.toLowerCase()
    const nameOk   = !search || (v.name || '').toLowerCase().includes(q) || (v.imo_number || '').toLowerCase().includes(q)
    const statusOk = statusFilter === 'all' || v.status === statusFilter
    const typeOk   = typeFilter   === 'all' || v.vessel_type === typeFilter
    return nameOk && statusOk && typeOk
  })

  const stats = {
    at_sea:     list.filter(v => v.status === 'at_sea').length,
    approaching:list.filter(v => v.status === 'approaching').length,
    anchored:   list.filter(v => v.status === 'anchored').length,
    berthed:    list.filter(v => v.status === 'berthed').length,
    departed:   list.filter(v => v.status === 'departed').length,
  }

  // ── Add Vessel ─────────────────────────────────────────────────────────────
  async function handleCreate(e) {
    e.preventDefault(); setSaveErr(''); setSaving(true)
    try {
      await createVessel.mutateAsync({
        name:                 nameRef.current.value.trim(),
        imo_number:           imoRef.current.value.trim(),
        mmsi:                 mmsiRef.current.value.trim()  || undefined,
        vessel_type:          typeRef.current.value,
        status:               statusRef.current.value,
        flag:                 flagRef.current.value.trim()  || undefined,
        length_overall:       lenRef.current.value          ? Number(lenRef.current.value)   : undefined,
        beam:                 beamRef.current.value         ? Number(beamRef.current.value)   : undefined,
        max_draft:            draftRef.current.value        ? Number(draftRef.current.value)  : undefined,
        gross_tonnage:        gtRef.current.value           ? Number(gtRef.current.value)     : undefined,
        owner:                ownerRef.current.value.trim() || undefined,
        year_built:           yearRef.current.value         ? Number(yearRef.current.value)   : undefined,
      })
      setSaveOk(true)
      setTimeout(() => { setShowAdd(false); setSaveOk(false) }, 1400)
    } catch (err) { setSaveErr(err.message || 'Failed to add vessel.') }
    finally { setSaving(false) }
  }

  // ── Import ─────────────────────────────────────────────────────────────────
  function openImport() { setImportErr(''); setAnalysis(null); setProgress(null); setImportDone(false); setShowImport(true) }

  const processFile = useCallback(async file => {
    setImportErr(''); setAnalysis(null); setProgress(null); setImportDone(false)
    const ext = file.name.split('.').pop().toLowerCase()
    if (!['xlsx','xls','csv'].includes(ext)) {
      setImportErr(`".${ext}" is not supported. Use Excel (.xlsx/.xls) or CSV. Convert PDF to Excel first.`)
      return
    }
    setImportLoading(true)
    try {
      const rows = await parseFile(file)
      if (rows.length < 2) { setImportErr('File is empty or has no data rows.'); return }
      const colMap = mapColumns(rows[0])
      if (colMap.name === undefined && colMap._vessel_id === undefined) {
        setImportErr(
          `No "Name" or "vessel_id" column found.\n` +
          `Columns detected: ${rows[0].map(c => `"${c}"`).join(', ')}\n\n` +
          `Expected at least one of: Name, Vessel Name, vessel_id`
        )
        return
      }

      const existingImos  = new Set(list.filter(v => v.imo_number).map(v => v.imo_number))
      const existingNames = new Set(list.map(v => (v.name || '').toLowerCase()))
      const imosSeen = new Set()
      const results  = []

      for (let i = 1; i < rows.length; i++) {
        const row = rows[i]
        if (row.every(c => c === '' || c == null)) continue
        const r = validateRow(row, colMap, i + 1, imosSeen)
        r.dupInDb = false
        if (r.vessel.imo_number && existingImos.has(r.vessel.imo_number)) {
          r.issues.push(`IMO already exists in database`); r.dupInDb = true
        } else if (!r.dupInDb && r.vessel.name && existingNames.has(r.vessel.name.toLowerCase())) {
          r.issues.push(`Name "${r.vessel.name}" already exists in database`); r.dupInDb = true
        }
        r.isValid = r.issues.length === 0
        results.push(r)
      }

      setAnalysis({
        fileName:  file.name,
        totalRows: results.length,
        valid:     results.filter(r => r.isValid),
        dupFile:   results.filter(r => r.dupInFile && !r.dupInDb),
        dupDb:     results.filter(r => r.dupInDb),
        corrupt:   results.filter(r => !r.isValid && !r.dupInFile && !r.dupInDb),
        colsFound: Object.keys(colMap).filter(k => !k.startsWith('_')),
      })
    } catch (err) { setImportErr(`Parse error: ${err.message}`) }
    finally { setImportLoading(false) }
  }, [list])

  async function confirmImport() {
    if (!analysis) return
    const toImport = analysis.valid
    setProgress({ done: 0, total: toImport.length, errors: [] })
    let done = 0; const errors = []
    for (const r of toImport) {
      try { await vesselsApi.create(r.vessel) }
      catch (err) { errors.push({ name: r.vessel.name, msg: err.message }) }
      done++
      setProgress({ done, total: toImport.length, errors: [...errors] })
    }
    setImportDone(true); refetch()
  }

  const successCount = progress ? progress.done - progress.errors.length : 0

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <MainLayout>
      <Navbar title="Vessel Management" subtitle="Monitor all vessels — status, registry, and live import">
        <div className="flex gap-2">
          <Button variant="secondary" onClick={openImport}>
            <i className="fa-solid fa-file-import" /> Import File
          </Button>
          <Button variant="primary" onClick={() => { setSaveErr(''); setSaveOk(false); setShowAdd(true) }}>
            <i className="fa-solid fa-plus" /> Add Vessel
          </Button>
        </div>
      </Navbar>

      <div className="flex-1 p-6 overflow-auto space-y-5">

        {/* ── Status cards ── */}
        <div className="grid grid-cols-5 gap-4">
          {[
            { key:'at_sea',      label:'At Sea',      icon:'fa-water',   bg:'bg-blue-50',   ring:'ring-blue-200',   txt:'text-blue-700' },
            { key:'approaching', label:'Approaching', icon:'fa-location-arrow', bg:'bg-purple-50', ring:'ring-purple-200', txt:'text-purple-700' },
            { key:'anchored',    label:'Anchored',    icon:'fa-anchor',  bg:'bg-yellow-50', ring:'ring-yellow-200', txt:'text-yellow-700' },
            { key:'berthed',     label:'Berthed',     icon:'fa-ship',    bg:'bg-green-50',  ring:'ring-green-200',  txt:'text-green-700' },
            { key:'departed',    label:'Departed',    icon:'fa-circle-arrow-right', bg:'bg-gray-50', ring:'ring-gray-200', txt:'text-gray-600' },
          ].map(s => (
            <button
              key={s.key}
              onClick={() => setStatusFilter(statusFilter === s.key ? 'all' : s.key)}
              className={`rounded-xl p-4 text-left border ring-1 transition-all ${s.bg} ${s.ring} ${statusFilter === s.key ? 'shadow-md scale-[1.02]' : 'hover:shadow-sm'}`}
            >
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${s.bg.replace('50','100')}`}>
                <i className={`fa-solid ${s.icon} ${s.txt} text-sm`} />
              </div>
              <p className={`text-2xl font-bold ${s.txt}`}>{loading ? '…' : stats[s.key]}</p>
              <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
            </button>
          ))}
        </div>

        {/* ── Controls ── */}
        <CardContainer className="p-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3 flex-wrap">
              <Input icon="fa-magnifying-glass" placeholder="Search name or IMO…" className="w-72"
                value={search} onChange={e => setSearch(e.target.value)} />
              <Select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                options={[
                  { value:'all',        label:'All Statuses' },
                  { value:'at_sea',     label:'At Sea' },
                  { value:'approaching',label:'Approaching' },
                  { value:'anchored',   label:'Anchored' },
                  { value:'berthed',    label:'Berthed' },
                  { value:'departed',   label:'Departed' },
                ]} />
              <Select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
                options={[
                  { value:'all',          label:'All Types' },
                  { value:'container',    label:'Container' },
                  { value:'bulk_carrier', label:'Bulk Carrier' },
                  { value:'tanker',       label:'Tanker' },
                  { value:'ro_ro',        label:'Ro-Ro' },
                  { value:'general_cargo',label:'General Cargo' },
                  { value:'other',        label:'Other' },
                ]} />
            </div>
            <Button variant="ghost" onClick={refetch} size="sm">
              <i className="fa-solid fa-rotate-right" /> Refresh
            </Button>
          </div>
        </CardContainer>

        {/* ── Table ── */}
        <CardContainer>
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <h3 className="font-semibold text-gray-900">Vessel Registry</h3>
            <span className="text-sm text-gray-400">{filtered.length} of {list.length} vessel{list.length !== 1 ? 's' : ''}</span>
          </div>

          {error && <div className="p-6 text-center text-red-500 text-sm"><i className="fa-solid fa-circle-exclamation mr-2" />{error.message}</div>}
          {loading && <div className="p-6 text-center text-gray-400 text-sm"><i className="fa-solid fa-spinner fa-spin mr-2" />Loading…</div>}

          {!loading && !error && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-gray-50 border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                    {['Vessel','IMO / MMSI','Type','Status','Flag','Owner','Actions'].map(h => (
                      <th key={h} className="px-5 py-3 text-left font-semibold">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {filtered.map(v => (
                    <tr key={v.id} className="hover:bg-blue-50/30 transition-colors">
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${typeVariant[v.vessel_type] === 'blue' ? 'bg-blue-100' : typeVariant[v.vessel_type] === 'purple' ? 'bg-purple-100' : typeVariant[v.vessel_type] === 'yellow' ? 'bg-yellow-100' : 'bg-green-100'}`}>
                            <i className="fa-solid fa-ship text-xs text-gray-600" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{v.name}</p>
                            {v.year_built && <p className="text-xs text-gray-400">Built {v.year_built}</p>}
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-gray-700">
                        <p>{v.imo_number || '—'}</p>
                        {v.mmsi && <p className="text-xs text-gray-400">{v.mmsi}</p>}
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge variant={typeVariant[v.vessel_type] || 'default'}>{typeLabel(v.vessel_type)}</Badge>
                      </td>
                      <td className="px-5 py-3.5">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusClass(v.status)}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${statusDotColor(v.status)}`} />
                          {statusLabel(v.status)}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-gray-600">{v.flag || '—'}</td>
                      <td className="px-5 py-3.5 text-gray-600 max-w-[140px] truncate">{v.owner || '—'}</td>
                      <td className="px-5 py-3.5">
                        <div className="flex gap-2">
                          <button className="w-7 h-7 rounded flex items-center justify-center text-blue-500 hover:bg-blue-50" title="View">
                            <i className="fa-solid fa-eye text-xs" />
                          </button>
                          <button className="w-7 h-7 rounded flex items-center justify-center text-red-400 hover:bg-red-50" title="Delete"
                            onClick={async () => { if (window.confirm(`Delete "${v.name}"?`)) { await deleteVessel.mutateAsync(v.id) } }}>
                            <i className="fa-solid fa-trash text-xs" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filtered.length === 0 && (
                <div className="py-16 text-center text-gray-400">
                  <i className="fa-solid fa-ship text-4xl mb-3 opacity-20 block" />
                  <p className="text-sm">{list.length === 0 ? 'No vessels yet. Add one manually or import a file.' : 'No vessels match the current filters.'}</p>
                </div>
              )}
            </div>
          )}
        </CardContainer>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          Add Vessel Modal
      ═══════════════════════════════════════════════════════════════════════ */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-900">Add New Vessel</h3>
              <button onClick={() => setShowAdd(false)} className="text-gray-400 hover:text-gray-600 w-7 h-7 flex items-center justify-center rounded hover:bg-gray-100">
                <i className="fa-solid fa-xmark" />
              </button>
            </div>
            <div className="p-6">
              {saveOk ? (
                <div className="py-10 text-center text-green-600">
                  <i className="fa-solid fa-circle-check text-4xl mb-3 block" />
                  <p className="font-medium">Vessel added successfully!</p>
                </div>
              ) : (
                <form onSubmit={handleCreate} className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                      <label className="block text-xs font-medium text-gray-600 mb-1">Vessel Name <span className="text-red-500">*</span></label>
                      <input ref={nameRef} name="name" required placeholder="e.g. MV Ocean Star"
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">IMO Number <span className="text-red-500">*</span></label>
                      <input ref={imoRef} name="imo_number" required placeholder="7 digits, e.g. 9876543"
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">MMSI</label>
                      <input ref={mmsiRef} name="mmsi" placeholder="9 digits"
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Vessel Type <span className="text-red-500">*</span></label>
                      <select ref={typeRef} required className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                        {VESSEL_TYPES.map(t => <option key={t} value={t}>{typeLabel(t)}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
                      <select ref={statusRef} className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                        {VESSEL_STATUSES.map(s => <option key={s} value={s}>{statusLabel(s)}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Flag</label>
                      <input ref={flagRef} name="flag" placeholder="e.g. Egypt"
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Owner</label>
                      <input ref={ownerRef} name="owner" placeholder="Company name"
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-600 mb-1">Year Built</label>
                      <input ref={yearRef} name="year_built" type="number" min="1900" max="2030" placeholder="e.g. 2015"
                        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-600 mb-2">Dimensions (optional)</p>
                    <div className="grid grid-cols-4 gap-3">
                      {[
                        { label:'Length (m)', ref: lenRef },
                        { label:'Beam (m)',   ref: beamRef },
                        { label:'Draft (m)',  ref: draftRef },
                        { label:'Gross Ton.', ref: gtRef },
                      ].map(f => (
                        <div key={f.label}>
                          <label className="block text-xs text-gray-400 mb-1">{f.label}</label>
                          <input ref={f.ref} type="number" min="0" step="0.1"
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                      ))}
                    </div>
                  </div>
                  {saveErr && (
                    <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-xs text-red-600">
                      <i className="fa-solid fa-circle-exclamation mr-1" />{saveErr}
                    </div>
                  )}
                  <div className="flex gap-3 pt-1">
                    <button type="button" onClick={() => setShowAdd(false)}
                      className="flex-1 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
                    <button type="submit" disabled={saving}
                      className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60">
                      {saving ? <><i className="fa-solid fa-spinner fa-spin mr-1" />Adding…</> : 'Add Vessel'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          Import Modal
      ═══════════════════════════════════════════════════════════════════════ */}
      {showImport && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-blue-100 rounded-lg flex items-center justify-center">
                  <i className="fa-solid fa-file-import text-blue-600 text-sm" />
                </div>
                <div>
                  <h3 className="font-semibold text-gray-900">Import Vessels from File</h3>
                  <p className="text-xs text-gray-400">Excel (.xlsx, .xls) or CSV — auto analysis before import</p>
                </div>
              </div>
              <button onClick={() => setShowImport(false)} className="text-gray-400 hover:text-gray-600 w-7 h-7 flex items-center justify-center rounded hover:bg-gray-100">
                <i className="fa-solid fa-xmark" />
              </button>
            </div>

            <div className="p-6 space-y-5">
              {/* Done */}
              {importDone && (
                <div className="text-center py-8">
                  <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <i className="fa-solid fa-circle-check text-green-600 text-3xl" />
                  </div>
                  <p className="text-lg font-semibold text-gray-900">Import Complete</p>
                  <p className="text-gray-500 text-sm mt-1">{successCount} vessel{successCount !== 1 ? 's' : ''} added{progress.errors.length > 0 ? `, ${progress.errors.length} failed` : ''}</p>
                  {progress.errors.length > 0 && (
                    <div className="mt-3 text-left bg-red-50 border border-red-100 rounded-lg p-3 max-h-32 overflow-y-auto">
                      {progress.errors.map((e, i) => <p key={i} className="text-xs text-red-600"><b>{e.name}</b>: {e.msg}</p>)}
                    </div>
                  )}
                  <button onClick={() => setShowImport(false)} className="mt-5 px-6 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">Close</button>
                </div>
              )}

              {/* Progress */}
              {!importDone && progress && (
                <div className="text-center py-8">
                  <i className="fa-solid fa-spinner fa-spin text-blue-600 text-3xl mb-4 block" />
                  <p className="font-medium text-gray-700 mb-2">Importing {progress.done} / {progress.total}</p>
                  <div className="w-full bg-gray-100 rounded-full h-2.5">
                    <div className="bg-blue-600 h-2.5 rounded-full transition-all" style={{ width: `${Math.round(progress.done / progress.total * 100)}%` }} />
                  </div>
                </div>
              )}

              {/* Upload zone */}
              {!importDone && !progress && !analysis && (
                <>
                  <div
                    onDragOver={e => { e.preventDefault(); setDragging(true) }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={e => { e.preventDefault(); setDragging(false); processFile(e.dataTransfer.files[0]) }}
                    onClick={() => fileRef.current?.click()}
                    className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${dragging ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-blue-300 hover:bg-gray-50'}`}
                  >
                    {importLoading ? (
                      <><i className="fa-solid fa-spinner fa-spin text-blue-500 text-4xl mb-3 block" /><p className="text-gray-600">Analysing file…</p></>
                    ) : (
                      <>
                        <i className="fa-solid fa-cloud-arrow-up text-gray-300 text-5xl mb-4 block" />
                        <p className="font-medium text-gray-700 mb-1">Drop file here or click to browse</p>
                        <p className="text-sm text-gray-400">Excel (.xlsx, .xls) · CSV (.csv)</p>
                        <p className="text-xs text-gray-300 mt-1">PDF → convert to Excel first</p>
                      </>
                    )}
                    <input ref={fileRef} type="file" accept=".xlsx,.xls,.csv" className="hidden" onChange={e => processFile(e.target.files[0])} />
                  </div>

                  {importErr && (
                    <div className="p-4 bg-red-50 border border-red-100 rounded-lg flex gap-2">
                      <i className="fa-solid fa-circle-exclamation text-red-400 mt-0.5 flex-shrink-0" />
                      <p className="text-sm text-red-600 whitespace-pre-wrap">{importErr}</p>
                    </div>
                  )}

                  {/* Column guide */}
                  <div className="bg-gray-50 rounded-xl p-4 border border-gray-100">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Recognised Column Names</p>
                    <div className="grid grid-cols-2 gap-y-1.5 gap-x-6 text-xs">
                      {[
                        ['Name *',           'Required'],
                        ['IMO Number',        '7-digit IMO'],
                        ['MMSI',             '9-digit MMSI'],
                        ['Vessel Type',       'container, tanker, bulk_carrier…'],
                        ['Status',            'at_sea, approaching, berthed…'],
                        ['Flag',              'Country name'],
                        ['LOA / loa_m',       'Length overall (m)'],
                        ['Beam / beam_m',     'Beam (m)'],
                        ['Draft / draft_m',   'Max draft (m)'],
                        ['Gross Tonnage',     'GT'],
                        ['Owner',             'Vessel owner'],
                        ['Year Built',        'Year (4 digits)'],
                      ].map(([col, hint]) => (
                        <div key={col} className="flex gap-2">
                          <span className="font-mono text-blue-600 min-w-[110px]">{col}</span>
                          <span className="text-gray-400">{hint}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {/* Analysis report */}
              {!importDone && !progress && analysis && (
                <>
                  <div className="grid grid-cols-4 gap-3">
                    {[
                      { label:'Total Rows',  val: analysis.totalRows,                              bg:'bg-gray-50',   txt:'text-gray-700',   icon:'fa-table' },
                      { label:'Ready',       val: analysis.valid.length,                           bg:'bg-green-50',  txt:'text-green-700',  icon:'fa-circle-check' },
                      { label:'Duplicates',  val: analysis.dupDb.length+analysis.dupFile.length,  bg:'bg-yellow-50', txt:'text-yellow-700', icon:'fa-copy' },
                      { label:'Invalid',     val: analysis.corrupt.length,                         bg:'bg-red-50',    txt:'text-red-600',    icon:'fa-triangle-exclamation' },
                    ].map(t => (
                      <div key={t.label} className={`${t.bg} rounded-xl p-4 text-center border border-white`}>
                        <i className={`fa-solid ${t.icon} ${t.txt} text-lg mb-1 block`} />
                        <p className={`text-2xl font-bold ${t.txt}`}>{t.val}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{t.label}</p>
                      </div>
                    ))}
                  </div>

                  <p className="text-xs text-gray-400"><b className="text-gray-600">File:</b> {analysis.fileName} · <b className="text-gray-600">Columns:</b> {analysis.colsFound.join(', ')}</p>

                  {(analysis.dupDb.length + analysis.dupFile.length) > 0 && (
                    <div>
                      <p className="text-sm font-semibold text-yellow-700 mb-2"><i className="fa-solid fa-copy mr-1" />Duplicates — skipped</p>
                      <div className="border border-yellow-100 rounded-lg overflow-hidden max-h-36 overflow-y-auto">
                        <table className="w-full text-xs"><thead><tr className="bg-yellow-50">
                          <th className="px-3 py-2 text-left text-yellow-700">Row</th><th className="px-3 py-2 text-left text-yellow-700">Name</th><th className="px-3 py-2 text-left text-yellow-700">Reason</th>
                        </tr></thead><tbody>
                          {[...analysis.dupDb,...analysis.dupFile].map(r => (
                            <tr key={r.rowIdx} className="border-t border-yellow-50">
                              <td className="px-3 py-1.5 text-yellow-600">{r.rowIdx}</td>
                              <td className="px-3 py-1.5 font-medium text-gray-900">{r.vessel.name||'—'}</td>
                              <td className="px-3 py-1.5 text-yellow-700">{r.issues.slice(-1)[0]}</td>
                            </tr>
                          ))}
                        </tbody></table>
                      </div>
                    </div>
                  )}

                  {analysis.corrupt.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold text-red-600 mb-2"><i className="fa-solid fa-triangle-exclamation mr-1" />Invalid rows — skipped</p>
                      <div className="border border-red-100 rounded-lg overflow-hidden max-h-44 overflow-y-auto">
                        <table className="w-full text-xs"><thead><tr className="bg-red-50">
                          <th className="px-3 py-2 text-left text-red-700">Row</th><th className="px-3 py-2 text-left text-red-700">Name</th><th className="px-3 py-2 text-left text-red-700">Issues</th>
                        </tr></thead><tbody>
                          {analysis.corrupt.map(r => (
                            <tr key={r.rowIdx} className="border-t border-red-50">
                              <td className="px-3 py-1.5 text-red-500">{r.rowIdx}</td>
                              <td className="px-3 py-1.5 font-medium text-gray-900">{r.vessel.name||<em className="text-gray-400">no name</em>}</td>
                              <td className="px-3 py-1.5 text-red-600">{r.issues.join(' · ')}</td>
                            </tr>
                          ))}
                        </tbody></table>
                      </div>
                    </div>
                  )}

                  {analysis.valid.length > 0 && (
                    <div>
                      <p className="text-sm font-semibold text-green-700 mb-2"><i className="fa-solid fa-circle-check mr-1" />Ready to import ({analysis.valid.length})</p>
                      <div className="border border-green-100 rounded-lg overflow-hidden max-h-44 overflow-y-auto">
                        <table className="w-full text-xs"><thead><tr className="bg-green-50">
                          <th className="px-3 py-2 text-left text-green-700">Name</th><th className="px-3 py-2 text-left text-green-700">IMO</th><th className="px-3 py-2 text-left text-green-700">Type</th><th className="px-3 py-2 text-left text-green-700">Flag</th>
                        </tr></thead><tbody>
                          {analysis.valid.map(r => (
                            <tr key={r.rowIdx} className="border-t border-green-50">
                              <td className="px-3 py-1.5 font-medium text-gray-900">{r.vessel.name}</td>
                              <td className="px-3 py-1.5 text-gray-600">{r.vessel.imo_number||'—'}</td>
                              <td className="px-3 py-1.5 text-gray-600">{r.vessel.vessel_type||'—'}</td>
                              <td className="px-3 py-1.5 text-gray-600">{r.vessel.flag||'—'}</td>
                            </tr>
                          ))}
                        </tbody></table>
                      </div>
                    </div>
                  )}

                  <div className="flex gap-3 pt-1 border-t border-gray-100">
                    <button onClick={() => { setAnalysis(null); setImportErr('') }}
                      className="px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
                      <i className="fa-solid fa-arrow-left mr-1" /> Choose Another
                    </button>
                    <div className="flex-1" />
                    <button onClick={() => setShowImport(false)} className="px-4 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
                    <button disabled={analysis.valid.length === 0} onClick={confirmImport}
                      className="px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50">
                      <i className="fa-solid fa-file-import mr-1" />Import {analysis.valid.length} Vessel{analysis.valid.length !== 1 ? 's' : ''}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  )
}
