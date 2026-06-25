import { useState } from 'react'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { CardContainer, Badge, Button, SectionHeader } from '../components/ui'
import {
  usePredictions, useEtaModelInfo, useVessels,
  usePredictEtaAndBerth, useSetActiveEtaModel,
} from '../hooks/queries'

// ── Egyptian port display names (model uses PORT_A–PORT_H internally) ─────────
export const EGYPT_PORTS = [
  { id: 'PORT_A', name: 'Alexandria',        ar: 'ميناء الإسكندرية' },
  { id: 'PORT_B', name: 'Port Said',         ar: 'ميناء بور سعيد'   },
  { id: 'PORT_C', name: 'Damietta',          ar: 'ميناء دمياط'       },
  { id: 'PORT_D', name: 'Sokhna',            ar: 'ميناء السخنة'      },
  { id: 'PORT_E', name: 'Suez',              ar: 'ميناء السويس'      },
  { id: 'PORT_F', name: 'Safaga',            ar: 'ميناء سفاجا'       },
  { id: 'PORT_G', name: 'Adabiya',           ar: 'ميناء العدبية'     },
  { id: 'PORT_H', name: 'Nuweiba',           ar: 'ميناء نويبع'       },
]
export const PORT_LABEL = Object.fromEntries(EGYPT_PORTS.map(p => [p.id, p.name]))

// ── Constants ─────────────────────────────────────────────────────────────────
const statusVariant = {
  pending: 'yellow', completed: 'green', failed: 'red', superseded: 'default',
}
const typeInfo = {
  eta:              { label:'ETA',              icon:'fa-clock',          color:'text-blue-600',   bg:'bg-blue-50'   },
  etb:              { label:'ETB',              icon:'fa-anchor',         color:'text-green-600',  bg:'bg-green-50'  },
  berth_congestion: { label:'Berth Congestion', icon:'fa-traffic-light',  color:'text-orange-600', bg:'bg-orange-50' },
  waiting_time:     { label:'Waiting Time',     icon:'fa-hourglass-half', color:'text-yellow-600', bg:'bg-yellow-50' },
  berth_assignment: { label:'Berth Assignment', icon:'fa-warehouse',      color:'text-purple-600', bg:'bg-purple-50' },
}

const PAGE_SIZE_OPTIONS = [20, 50, 100, 200]

function fmtDt(v) {
  if (!v) return '—'
  try { return new Date(v).toLocaleString(undefined, { dateStyle:'short', timeStyle:'short' }) }
  catch { return v }
}
function fmtPred(type, val, dt) {
  const t = (type || '').toLowerCase()
  if (val != null) {
    if (['eta','etb'].includes(t))       return `+${val.toFixed(1)} min delay`
    if (t === 'waiting_time')             return `${val.toFixed(1)} h`
    if (t === 'berth_congestion')         return `${Math.round(val * 100)}%`
    if (t === 'berth_assignment')         return `Berth ${Math.round(val)}`
  }
  return dt ? fmtDt(dt) : '—'
}
// ETA = Scheduled ETA + predicted delay minutes (computed in backend)
// predicted_datetime is always set for ETA predictions; never use created_at as base
function fmtETA(predictedDatetime) {
  if (predictedDatetime) return { text: fmtDt(predictedDatetime), est: false }
  return { text: '—', est: false }
}
function ConfBar({ score }) {
  if (score == null) return <span className="text-xs text-gray-400">—</span>
  const pct = Math.round(score * 100)
  const col  = pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-yellow-400' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-1.5 min-w-[60px]">
        <div className={`${col} h-1.5 rounded-full`} style={{ width:`${pct}%` }} />
      </div>
      <span className="text-xs text-gray-500 tabular-nums w-8">{pct}%</span>
    </div>
  )
}

// Tooltip component
function Tip({ text }) {
  const [show, setShow] = useState(false)
  return (
    <span className="relative inline-flex ml-1">
      <button type="button"
        onMouseEnter={() => setShow(true)} onMouseLeave={() => setShow(false)}
        onFocus={() => setShow(true)} onBlur={() => setShow(false)}
        className="w-4 h-4 rounded-full bg-gray-200 text-gray-500 text-[10px] font-bold inline-flex items-center justify-center hover:bg-blue-100 hover:text-blue-600 transition-colors">
        ?
      </button>
      {show && (
        <div className="absolute z-50 bottom-full mb-1 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 w-52 shadow-xl pointer-events-none leading-relaxed">
          {text}
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-gray-900" />
        </div>
      )}
    </span>
  )
}


const TABS = ['Live Predictions', 'Run ETA Prediction', 'Model Info']

export default function Predictions() {
  const [tab,        setTab]        = useState('Live Predictions')
  const [filterType, setFilterType] = useState('all')
  const [page,       setPage]       = useState(0)
  const [pageSize,   setPageSize]   = useState(100)

  // ── Data ──────────────────────────────────────────────────────────────────
  const { data: predsRaw, isLoading: predsLoading, refetch: refetchPreds } =
    usePredictions({ skip: page * pageSize, limit: pageSize })
  const { data: modelInfo, isLoading: modelLoading } = useEtaModelInfo()
  const predictEtaAndBerth = usePredictEtaAndBerth()
  const setActiveModel = useSetActiveEtaModel()
  const [activating, setActivating] = useState(null)
  const { data: vesselsList } = useVessels(0, 200)

  const preds   = predsRaw   || []
  const vessels = vesselsList || []

  const filtered = filterType === 'all' ? preds : preds.filter(p => p.prediction_type === filterType)

  // ── ETA form state ────────────────────────────────────────────────────────
  const nowStr = () => new Date().toISOString().slice(0, 16)
  const futureStr = (hoursAhead = 6) => {
    const d = new Date(); d.setHours(d.getHours() + hoursAhead)
    return d.toISOString().slice(0, 16)
  }

  const [etaForm, setEtaForm] = useState({
    vessel_id: '', scheduled_eta: '', timestamp: '',
    latitude: '', longitude: '', speed_knots: '', heading: '180',
    distance_to_port_nm: '', port_id: 'PORT_A', traffic_density: 'Medium',
    berth_max_length: '', berth_queue_length: '',
    crane_availability_ratio: '', port_congestion_index: '',
    port_avg_delay_last_24h: '', wave_height_m: '', wind_speed_knots: '',
    visibility_km: '', precipitation_mm: '0', temperature_c: '',
  })
  const [etaResult,  setEtaResult]  = useState(null)
  const [etaRunning, setEtaRunning] = useState(false)
  const [etaError,   setEtaError]   = useState('')

  function setField(k, v) { setEtaForm(f => ({ ...f, [k]: v })) }

  function autoTimestamp() {
    if (!etaForm.timestamp) setField('timestamp', nowStr())
  }

  async function runETA(e) {
    e.preventDefault()
    setEtaError('')
    setEtaResult(null)
    setEtaRunning(true)
    try {
      const payload = {
        vessel_id:                parseInt(etaForm.vessel_id),
        scheduled_eta:            new Date(etaForm.scheduled_eta).toISOString(),
        timestamp:                new Date(etaForm.timestamp || new Date()).toISOString(),
        latitude:                 parseFloat(etaForm.latitude),
        longitude:                parseFloat(etaForm.longitude),
        speed_knots:              parseFloat(etaForm.speed_knots),
        heading:                  parseInt(etaForm.heading),
        distance_to_port_nm:      parseFloat(etaForm.distance_to_port_nm),
        port_id:                  etaForm.port_id,
        traffic_density:          etaForm.traffic_density,
        berth_max_length:         parseInt(etaForm.berth_max_length),
        berth_queue_length:       parseInt(etaForm.berth_queue_length),
        crane_availability_ratio: parseFloat(etaForm.crane_availability_ratio),
        port_congestion_index:    parseFloat(etaForm.port_congestion_index),
        port_avg_delay_last_24h:  parseFloat(etaForm.port_avg_delay_last_24h),
        wave_height_m:            parseFloat(etaForm.wave_height_m),
        wind_speed_knots:         parseFloat(etaForm.wind_speed_knots),
        visibility_km:            parseFloat(etaForm.visibility_km),
        precipitation_mm:         parseFloat(etaForm.precipitation_mm),
        temperature_c:            parseFloat(etaForm.temperature_c),
      }
      // Use combined endpoint: ETA → Berth allocation in one shot
      const res = await predictEtaAndBerth.mutateAsync(payload)
      setEtaResult(res)
    } catch (err) {
      setEtaError(err.message || 'Prediction failed')
    } finally {
      setEtaRunning(false)
    }
  }

  const typeCounts = preds.reduce((acc, p) => {
    acc[p.prediction_type] = (acc[p.prediction_type] || 0) + 1
    return acc
  }, {})

  const completedCount = preds.filter(p => p.status === 'completed').length
  const pendingCount   = preds.filter(p => p.status === 'pending').length
  const confPreds  = preds.filter(p => p.confidence_score != null)
  const avgConfNum = confPreds.length ? confPreds.reduce((a, p) => a + p.confidence_score, 0) / confPreds.length : 0
  const avgConf    = confPreds.length ? Math.round(avgConfNum * 100) + '%' : '—'
  const maxConf    = confPreds.length ? Math.max(...confPreds.map(p => p.confidence_score)) : 0
  const minConf    = confPreds.length ? Math.min(...confPreds.map(p => p.confidence_score)) : 0
  const highConf   = confPreds.filter(p => p.confidence_score >= 0.80).length
  const medConf    = confPreds.filter(p => p.confidence_score >= 0.60 && p.confidence_score < 0.80).length
  const lowConf    = confPreds.filter(p => p.confidence_score < 0.60).length

  const confByType = Object.entries(typeInfo).map(([type, ti]) => {
    const tp = confPreds.filter(p => p.prediction_type === type)
    return { type, ti, avg: tp.length ? tp.reduce((s, p) => s + p.confidence_score, 0) / tp.length : null, count: tp.length }
  }).filter(t => t.count > 0)

  function confReason(avg) {
    if (!confPreds.length) return null
    if (avg >= 0.88) return {
      level: 'Excellent Confidence', icon: 'fa-circle-check',
      color: 'text-green-700', bg: 'bg-green-50', border: 'border-green-200',
      text: 'Excellent model certainty. Inputs are firmly within well-trained ranges — predictions are highly reliable for real-time operational decisions.',
    }
    if (avg >= 0.78) return {
      level: 'Good Confidence', icon: 'fa-circle-check',
      color: 'text-blue-700', bg: 'bg-blue-50', border: 'border-blue-200',
      text: 'Good overall certainty. The model has strong signal from port state and weather conditions. Most predictions fall well within the ±15 min accuracy band.',
    }
    if (avg >= 0.65) return {
      level: 'Moderate Confidence', icon: 'fa-triangle-exclamation',
      color: 'text-yellow-700', bg: 'bg-yellow-50', border: 'border-yellow-200',
      text: 'Mixed certainty. Some predictions involve borderline congestion values or partial weather inputs. Cross-check medium-confidence entries before critical decisions.',
    }
    return {
      level: 'Low Confidence', icon: 'fa-circle-exclamation',
      color: 'text-red-700', bg: 'bg-red-50', border: 'border-red-200',
      text: 'Below-average certainty. Likely causes: extreme weather, high congestion variability, or incomplete input fields. Review individual prediction inputs for data quality.',
    }
  }
  const reason = confReason(avgConfNum)

  const kpis = [
    { label:'Loaded',        value: preds.length,    icon:'fa-brain',        bg:'bg-blue-50',   color:'text-blue-600'   },
    { label:'Completed',     value: completedCount,  icon:'fa-circle-check', bg:'bg-green-50',  color:'text-green-600'  },
    { label:'Pending',       value: pendingCount,    icon:'fa-spinner',      bg:'bg-yellow-50', color:'text-yellow-600' },
    { label:'Avg Confidence',value: avgConf,         icon:'fa-gauge',        bg:'bg-purple-50', color:'text-purple-600' },
  ]

  const hasMore = preds.length === pageSize

  return (
    <MainLayout>
      <Navbar title="AI Predictions" subtitle={modelInfo ? `ETA model: ${modelInfo.model_name} · MAE ≈ ${modelInfo.metrics?.[modelInfo.model_name]?.MAE ?? '—'} min · R² ≈ ${modelInfo.metrics?.[modelInfo.model_name]?.R2 ?? '—'}` : 'ETA model: loading…'}>
        <Button variant="secondary" size="sm" onClick={() => { setTab('Model Info') }}>
          <i className="fa-solid fa-chart-bar mr-1" /> Model Info
        </Button>
        <Button variant="primary" onClick={() => setTab('Run ETA Prediction')}>
          <i className="fa-solid fa-bolt mr-1" /> Run ETA Prediction
        </Button>
      </Navbar>

      <div className="flex-1 p-6 overflow-auto space-y-5">

        {/* ── Tabs ── */}
        <div className="flex gap-1 border-b border-gray-200">
          {TABS.map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-all ${
                tab === t ? 'border-blue-600 text-blue-600' : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}>
              {t === 'Run ETA Prediction' && <i className="fa-solid fa-bolt mr-1.5 text-orange-400" />}
              {t}
            </button>
          ))}
        </div>

        {/* ════════════════════════════ LIVE PREDICTIONS ═══════════════════ */}
        {tab === 'Live Predictions' && (
          <>
            {/* KPI row */}
            <div className="grid grid-cols-4 gap-4">
              {kpis.map(k => (
                <CardContainer key={k.label} className="p-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 ${k.bg} rounded-xl flex items-center justify-center flex-shrink-0`}>
                      <i className={`fa-solid ${k.icon} ${k.color} text-sm`} />
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">{k.label}</p>
                      <p className="text-xl font-bold text-gray-900">{k.value}</p>
                    </div>
                  </div>
                </CardContainer>
              ))}
            </div>

            {/* ── Confidence Intelligence Panel ── */}
            {reason && confPreds.length > 0 && (
              <div className="rounded-xl border border-gray-100 bg-white p-5 space-y-4 shadow-sm">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
                    <i className="fa-solid fa-gauge text-purple-500" />
                    Confidence Analysis
                  </h3>
                  <span className="text-xs text-gray-400">{confPreds.length} predictions scored</span>
                </div>

                <div className="grid grid-cols-3 gap-5">

                  {/* Left: reasoning + min/avg/max */}
                  <div className="space-y-3">
                    <div className={`p-3 rounded-xl border ${reason.border} ${reason.bg}`}>
                      <p className={`text-xs font-semibold flex items-center gap-1.5 ${reason.color}`}>
                        <i className={`fa-solid ${reason.icon}`} />{reason.level}
                      </p>
                      <p className={`text-xs mt-1.5 leading-relaxed ${reason.color} opacity-90`}>{reason.text}</p>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-center text-xs">
                      {[
                        { label: 'Min',  val: Math.round(minConf * 100), color: 'text-red-600'    },
                        { label: 'Avg',  val: Math.round(avgConfNum * 100), color: 'text-purple-600' },
                        { label: 'Max',  val: Math.round(maxConf * 100), color: 'text-green-600'  },
                      ].map(({ label, val, color }) => (
                        <div key={label} className="bg-gray-50 rounded-lg p-2 border border-gray-100">
                          <div className="text-gray-400 mb-0.5">{label}</div>
                          <div className={`font-bold text-sm ${color}`}>{val}%</div>
                        </div>
                      ))}
                    </div>
                    {/* Overall bar */}
                    <div>
                      <div className="flex justify-between text-[10px] text-gray-400 mb-1">
                        <span>Overall confidence</span>
                        <span className="font-semibold text-purple-600">{Math.round(avgConfNum * 100)}%</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-2 rounded-full transition-all ${avgConfNum >= 0.80 ? 'bg-green-500' : avgConfNum >= 0.60 ? 'bg-yellow-400' : 'bg-red-500'}`}
                          style={{ width: `${Math.round(avgConfNum * 100)}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Middle: High / Medium / Low distribution */}
                  <div className="space-y-3">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Score Distribution</p>
                    {[
                      { label: 'High  ≥ 80%', count: highConf, color: 'bg-green-500',  text: 'text-green-700'  },
                      { label: 'Med   60–79%', count: medConf,  color: 'bg-yellow-400', text: 'text-yellow-700' },
                      { label: 'Low   < 60%',  count: lowConf,  color: 'bg-red-500',    text: 'text-red-700'    },
                    ].map(({ label, count, color, text }) => {
                      const pct = confPreds.length ? Math.round(count / confPreds.length * 100) : 0
                      return (
                        <div key={label} className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className={`font-medium ${text}`}>{label}</span>
                            <span className="text-gray-500 font-semibold">{count} <span className="text-gray-300">({pct}%)</span></span>
                          </div>
                          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                            <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                      )
                    })}
                    <p className="text-[10px] text-gray-400 leading-relaxed pt-1">
                      {highConf > medConf + lowConf
                        ? 'Most predictions are high-confidence — the model input quality is good.'
                        : lowConf > highConf
                        ? 'Many low-confidence predictions — check input completeness and data quality.'
                        : 'Spread across confidence tiers — review medium and low entries individually.'}
                    </p>
                  </div>

                  {/* Right: per-type breakdown */}
                  <div className="space-y-3">
                    <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">By Prediction Type</p>
                    {confByType.length === 0 && (
                      <p className="text-xs text-gray-400">No type breakdown available.</p>
                    )}
                    {confByType.map(({ type, ti, avg, count }) => {
                      const pct = Math.round(avg * 100)
                      return (
                        <div key={type} className="space-y-1">
                          <div className="flex items-center justify-between text-xs">
                            <span className={`flex items-center gap-1.5 font-medium ${ti.color}`}>
                              <i className={`fa-solid ${ti.icon} text-[10px]`} />{ti.label}
                            </span>
                            <span className="text-gray-500">{pct}% <span className="text-gray-300">({count})</span></span>
                          </div>
                          <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                            <div
                              className={`h-1.5 rounded-full ${pct >= 80 ? 'bg-green-500' : pct >= 60 ? 'bg-yellow-400' : 'bg-red-500'}`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                        </div>
                      )
                    })}
                    <div className="pt-2 p-2.5 bg-purple-50 border border-purple-100 rounded-lg text-[11px] text-purple-700">
                      <i className="fa-solid fa-lightbulb mr-1" />
                      <strong>What drives confidence:</strong> distance from port congestion thresholds, weather severity, and how close the predicted delay is to historical averages for that vessel type.
                    </div>
                  </div>

                </div>
              </div>
            )}

            {/* Controls row: filters + page-size */}
            <div className="flex flex-wrap items-center gap-2 justify-between">
              <div className="flex flex-wrap gap-2">
                <button onClick={() => { setFilterType('all'); setPage(0) }}
                  className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                    filterType === 'all' ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                  }`}>
                  All ({preds.length}{hasMore ? '+' : ''})
                </button>
                {Object.entries(typeInfo).map(([k, v]) => (
                  <button key={k} onClick={() => { setFilterType(k); setPage(0) }}
                    className={`px-3 py-1.5 rounded-full text-xs font-medium border transition-all ${
                      filterType === k ? `${v.bg} ${v.color} border-current` : 'bg-white text-gray-600 border-gray-200 hover:border-gray-300'
                    }`}>
                    <i className={`fa-solid ${v.icon} mr-1`} />{v.label} ({typeCounts[k] || 0})
                  </button>
                ))}
              </div>
              {/* Per-page selector */}
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <span>Show</span>
                <div className="flex rounded-lg border border-gray-200 overflow-hidden">
                  {PAGE_SIZE_OPTIONS.map(n => (
                    <button key={n}
                      onClick={() => { setPageSize(n); setPage(0) }}
                      className={`px-2.5 py-1.5 text-xs font-medium transition-all ${
                        pageSize === n ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'
                      }`}>
                      {n}
                    </button>
                  ))}
                </div>
                <span>per page</span>
                <button onClick={() => refetchPreds()}
                  className="ml-1 w-7 h-7 rounded-lg border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 flex items-center justify-center transition-all"
                  title="Refresh">
                  <i className="fa-solid fa-rotate-right text-xs" />
                </button>
              </div>
            </div>

            {/* Table */}
            <CardContainer>
              {predsLoading ? (
                <div className="p-8 text-center text-gray-400 text-sm">
                  <i className="fa-solid fa-spinner fa-spin mr-2" />Loading predictions…
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="bg-gray-50 border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                          {['ID','Type','Status','Vessel','Predicted Value','Confidence','ETA','Created'].map(h => (
                            <th key={h} className="px-4 py-3 text-left font-semibold">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-50">
                        {filtered.map(p => {
                          const ti = typeInfo[p.prediction_type] || typeInfo.eta
                          return (
                            <tr key={p.id} className="hover:bg-blue-50/20 transition-colors">
                              <td className="px-4 py-3 font-mono text-xs text-gray-400">#{p.id}</td>
                              <td className="px-4 py-3">
                                <span className={`inline-flex items-center gap-1.5 text-xs font-medium px-2 py-1 rounded-md ${ti.bg} ${ti.color}`}>
                                  <i className={`fa-solid ${ti.icon} text-[10px]`} />{ti.label}
                                </span>
                              </td>
                              <td className="px-4 py-3">
                                <Badge variant={statusVariant[p.status] || 'default'}>{p.status}</Badge>
                              </td>
                              <td className="px-4 py-3 text-gray-600 text-xs">#{p.vessel_id}</td>
                              <td className="px-4 py-3 font-medium text-gray-900">
                                {fmtPred(p.prediction_type, p.predicted_value, p.predicted_datetime)}
                              </td>
                              <td className="px-4 py-3 min-w-[120px]"><ConfBar score={p.confidence_score} /></td>
                              <td className="px-4 py-3 text-xs">
                                {(() => {
                                  const { text, est } = fmtETA(p.predicted_datetime)
                                  return text === '—'
                                    ? <span className="text-gray-400">—</span>
                                    : <span className={est ? 'text-gray-400' : 'text-gray-600'}>
                                        {text}
                                        {est && <span className="ml-1 text-[10px] text-gray-300 italic">est.</span>}
                                      </span>
                                })()}
                              </td>
                              <td className="px-4 py-3 text-gray-400 text-xs">{fmtDt(p.created_at)}</td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                    {filtered.length === 0 && (
                      <div className="py-12 text-center text-gray-400 text-sm">
                        <i className="fa-solid fa-brain text-3xl mb-3 block opacity-20" />
                        No predictions in this view.
                        <div className="mt-3">
                          <button onClick={() => setTab('Run ETA Prediction')}
                            className="text-blue-600 underline text-xs hover:text-blue-700">
                            Run your first ETA prediction →
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Pagination footer */}
                  <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between" style={{ background: '#080f1e' }}>
                    <div className="text-xs text-gray-500 flex items-center gap-2">
                      <span className="font-medium text-gray-700">{filtered.length}</span> records shown
                      {hasMore && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-50 border border-amber-100 text-amber-600 rounded-full text-[11px] font-medium">
                          <i className="fa-solid fa-triangle-exclamation text-[9px]" />
                          More records exist — increase "per page" or use Next
                        </span>
                      )}
                      · Page {page + 1}
                      · Offset {page * pageSize}–{page * pageSize + preds.length - 1}
                    </div>
                    <div className="flex gap-2">
                      <Button variant="secondary" size="sm" onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}>
                        <i className="fa-solid fa-chevron-left mr-1" />Prev
                      </Button>
                      <Button variant="secondary" size="sm" onClick={() => setPage(p => p + 1)} disabled={!hasMore}>
                        Next<i className="fa-solid fa-chevron-right ml-1" />
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContainer>

            {/* How-to banner */}
            <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl flex items-start gap-3 text-sm">
              <i className="fa-solid fa-circle-info text-blue-500 mt-0.5 flex-shrink-0" />
              <div className="text-blue-700">
                <strong>Tip:</strong> The table shows <strong>{pageSize} records per page</strong>. The database may contain thousands of predictions.
                Use <strong>Show 200</strong> to load more at once, or page through using Prev / Next.
                To add a new prediction, click the <strong className="text-orange-600">⚡ Run ETA Prediction</strong> tab above.
              </div>
            </div>
          </>
        )}

        {/* ════════════════════════════ RUN ETA ════════════════════════════ */}
        {tab === 'Run ETA Prediction' && (
          <>
            {/* Steps banner */}
            <div className="flex items-stretch gap-1 text-xs rounded-xl overflow-hidden border border-blue-100">
              {[
                { n:'1', text:'Select a vessel', icon:'fa-ship' },
                { n:'2', text:'Set scheduled ETA & timestamp', icon:'fa-calendar' },
                { n:'3', text:'Enter port & weather data', icon:'fa-anchor' },
                { n:'4', text:'Click Predict ETA Delay', icon:'fa-bolt' },
                { n:'5', text:'View result on the right', icon:'fa-chart-bar' },
              ].map((s, i, arr) => (
                <div key={s.n} className={`flex-1 flex flex-col items-center justify-center gap-1 py-3 px-2 text-center
                  ${i === 3 ? 'bg-blue-600 text-white' : 'bg-blue-50 text-blue-700'}`}>
                  <i className={`fa-solid ${s.icon} text-sm`} />
                  <span className="font-semibold">Step {s.n}</span>
                  <span className="opacity-80 leading-tight">{s.text}</span>
                </div>
              ))}
            </div>

            <div className="grid grid-cols-5 gap-5">

              {/* Form — left 3 cols */}
              <div className="col-span-3">
                <CardContainer className="p-6">
                  <div className="mb-4">
                    <h3 className="text-base font-semibold text-gray-900">ETA Prediction Inputs</h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {modelInfo
                        ? `${modelInfo.model_name} · ${modelInfo.feature_count} features · MAE ${modelInfo.metrics?.[modelInfo.model_name]?.MAE ?? '—'} min`
                        : 'CatBoost · loading…'}
                    </p>
                  </div>

                  <form onSubmit={runETA} className="space-y-6">

                    {/* ── Vessel & Schedule ── */}
                    <div className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 space-y-3">
                      <p className="text-xs font-bold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
                        <i className="fa-solid fa-ship text-blue-500" />Vessel &amp; Schedule
                      </p>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="col-span-2">
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Vessel <span className="text-red-500">*</span>
                            <Tip text="Select the vessel you want to predict ETA for. The model auto-fills physical specs (length, draft, tonnage) from the database." />
                          </label>
                          <select required value={etaForm.vessel_id} onChange={e => setField('vessel_id', e.target.value)}
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="">— Select vessel —</option>
                            {vessels.map(v => (
                              <option key={v.id} value={v.id}>{v.name} ({v.imo_number})</option>
                            ))}
                          </select>
                          {vessels.length === 0 && (
                            <p className="text-xs text-amber-500 mt-1">
                              <i className="fa-solid fa-triangle-exclamation mr-1" />No vessels loaded — add vessels in the Vessels module first.
                            </p>
                          )}
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Scheduled ETA <span className="text-red-500">*</span>
                            <Tip text="The originally scheduled arrival time of the vessel. The model predicts how many minutes of delay to add to this." />
                          </label>
                          <input required type="datetime-local" value={etaForm.scheduled_eta}
                            onChange={e => setField('scheduled_eta', e.target.value)}
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Observation Time
                            <Tip text="When this prediction is being made — usually 'now'. Defaults to current time if left empty." />
                          </label>
                          <input type="datetime-local" value={etaForm.timestamp}
                            onFocus={autoTimestamp}
                            onChange={e => setField('timestamp', e.target.value)}
                            placeholder="Now"
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
                          <p className="text-[10px] text-gray-400 mt-0.5">Defaults to current time</p>
                        </div>
                      </div>
                    </div>

                    {/* ── Navigation ── */}
                    <div className="p-4 rounded-xl border border-gray-100 bg-gray-50/50 space-y-3">
                      <p className="text-xs font-bold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
                        <i className="fa-solid fa-compass text-green-500" />Navigation
                      </p>
                      <div className="grid grid-cols-3 gap-3">
                        {[
                          { k:'latitude',            label:'Latitude',           tip:'Current vessel latitude. Example: 25.27 for Dubai area.',        placeholder:'25.0'  },
                          { k:'longitude',           label:'Longitude',          tip:'Current vessel longitude. Example: 55.30 for Dubai area.',       placeholder:'55.0'  },
                          { k:'speed_knots',         label:'Speed (knots)',       tip:'Vessel speed over ground in knots. Typical: 10–18 knots.',       placeholder:'14.5'  },
                          { k:'heading',             label:'Heading (°)',         tip:'Compass heading in degrees (0–359). 180 = south.',               placeholder:'180'   },
                          { k:'distance_to_port_nm', label:'Distance to Port (nm)', tip:'Nautical miles remaining to port. Drives travel time estimate.', placeholder:'80' },
                        ].map(f => (
                          <div key={f.k}>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              {f.label}
                              <Tip text={f.tip} />
                            </label>
                            <input type="number" step="any" value={etaForm[f.k]}
                              onChange={e => setField(f.k, e.target.value)}
                              placeholder={f.placeholder}
                              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* ── Port Conditions ── */}
                    <div className="p-4 rounded-xl border border-orange-100 bg-orange-50/30 space-y-3">
                      <p className="text-xs font-bold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
                        <i className="fa-solid fa-anchor text-orange-500" />Port Conditions
                        <span className="normal-case font-normal text-orange-500 text-[11px] ml-1">★ highest impact on predicted delay</span>
                      </p>
                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Port ID
                            <Tip text="Which port the vessel is heading to. Ports have different baseline congestion profiles learned during training." />
                          </label>
                          <select value={etaForm.port_id} onChange={e => setField('port_id', e.target.value)}
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                            {EGYPT_PORTS.map(p => (
                              <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Traffic Density
                            <Tip text="Current port traffic level. High = many ships competing for berths." />
                          </label>
                          <select value={etaForm.traffic_density} onChange={e => setField('traffic_density', e.target.value)}
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                            {['Low','Medium','High'].map(v => <option key={v}>{v}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Congestion Index ★
                            <Tip text="0 = empty port, 1 = fully saturated. This is the #1 delay driver. Values above 0.6 cause significant delays." />
                          </label>
                          <input type="number" step="0.01" min="0" max="1" value={etaForm.port_congestion_index}
                            onChange={e => setField('port_congestion_index', e.target.value)}
                            className="w-full border border-orange-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-400" />
                          <div className="mt-1 flex gap-1">
                            {[['0.1','Low'],['0.4','Med'],['0.7','High'],['0.9','Crit']].map(([v,l]) => (
                              <button key={v} type="button" onClick={() => setField('port_congestion_index', v)}
                                className="flex-1 text-[10px] py-0.5 rounded border border-orange-100 text-orange-600 hover:bg-orange-50 transition-all">
                                {l}
                              </button>
                            ))}
                          </div>
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Berth Queue ★
                            <Tip text="Ships waiting for a berth. Each extra ship adds ~8 min of delay on average." />
                          </label>
                          <input type="number" min="0" max="30" value={etaForm.berth_queue_length}
                            onChange={e => setField('berth_queue_length', e.target.value)}
                            className="w-full border border-orange-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-400" />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Crane Availability (0–1)
                            <Tip text="Fraction of cranes available (1.0 = all available). Low ratio extends cargo op time." />
                          </label>
                          <input type="number" step="0.01" min="0" max="1" value={etaForm.crane_availability_ratio}
                            onChange={e => setField('crane_availability_ratio', e.target.value)}
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Berth Max Length (m)
                            <Tip text="Maximum vessel length the target berth can accommodate. Used for berth fit assessment." />
                          </label>
                          <input type="number" value={etaForm.berth_max_length}
                            onChange={e => setField('berth_max_length', e.target.value)}
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                        <div className="col-span-3">
                          <label className="block text-xs font-medium text-gray-600 mb-1">
                            Avg Delay Last 24 h (min)
                            <Tip text="Rolling average delay across all vessels at this port in the last 24 hours. High values indicate systemic congestion." />
                          </label>
                          <input type="number" step="any" value={etaForm.port_avg_delay_last_24h}
                            onChange={e => setField('port_avg_delay_last_24h', e.target.value)}
                            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
                        </div>
                      </div>
                    </div>

                    {/* ── Weather ── */}
                    <div className="p-4 rounded-xl border border-blue-100 bg-blue-50/20 space-y-3">
                      <p className="text-xs font-bold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
                        <i className="fa-solid fa-cloud-bolt text-blue-400" />Weather Conditions
                      </p>
                      <div className="grid grid-cols-3 gap-3">
                        {[
                          { k:'wave_height_m',    label:'Wave Height (m) ★',  step:'0.1', tip:'Sea wave height in metres. Above 3m causes significant speed reduction.'   },
                          { k:'wind_speed_knots', label:'Wind Speed (kn)',     step:'1',   tip:'Surface wind speed in knots. Above 30 kn may cause manoeuvring delays.'    },
                          { k:'visibility_km',    label:'Visibility (km)',     step:'0.5', tip:'Horizontal visibility. Below 2 km triggers pilotage restrictions.'         },
                          { k:'precipitation_mm', label:'Precipitation (mm)',  step:'0.1', tip:'Rainfall intensity. Heavy rain reduces visibility and slows cargo ops.'    },
                          { k:'temperature_c',    label:'Temperature (°C)',    step:'0.5', tip:'Ambient air temperature. Extreme heat/cold affects crew performance.'      },
                        ].map(f => (
                          <div key={f.k}>
                            <label className="block text-xs font-medium text-gray-600 mb-1">
                              {f.label}
                              <Tip text={f.tip} />
                            </label>
                            <input type="number" step={f.step} value={etaForm[f.k]}
                              onChange={e => setField(f.k, e.target.value)}
                              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-blue-500" />
                          </div>
                        ))}
                      </div>
                    </div>

                    {etaError && (
                      <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-sm text-red-600">
                        <i className="fa-solid fa-circle-exclamation mr-2" />{etaError}
                      </div>
                    )}

                    <button type="submit" disabled={etaRunning}
                      className="w-full flex items-center justify-center gap-2 py-3.5 px-6 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold rounded-xl transition-all text-sm shadow-sm shadow-blue-200">
                      {etaRunning
                        ? <><i className="fa-solid fa-spinner fa-spin" />Running CatBoost Model…</>
                        : <><i className="fa-solid fa-bolt" />Predict ETA Delay</>}
                    </button>
                  </form>
                </CardContainer>
              </div>

              {/* Result panel — right 2 cols */}
              <div className="col-span-2 space-y-4">

                {/* Model status badge */}
                <CardContainer className="p-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center flex-shrink-0">
                      <i className="fa-solid fa-brain text-white text-sm" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-semibold text-gray-900 text-sm">CatBoost ETA Model</p>
                      <p className="text-xs text-gray-400">
                      {modelInfo
                        ? `MAE ≈ ${modelInfo.metrics?.[modelInfo.model_name]?.MAE ?? '—'} min · R² ≈ ${modelInfo.metrics?.[modelInfo.model_name]?.R2 ?? '—'} · ${modelInfo.feature_count} features`
                        : 'loading…'}
                    </p>
                    </div>
                    <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-50 text-green-700 text-xs font-medium border border-green-100">
                      <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />Loaded
                    </span>
                  </div>
                </CardContainer>

                {/* What to expect */}
                {!etaResult && (
                  <>
                    <CardContainer className="p-5">
                      <p className="text-xs font-bold text-gray-500 uppercase tracking-wide mb-3">
                        <i className="fa-solid fa-circle-question mr-1.5" />What This Predicts
                      </p>
                      <div className="space-y-3 text-xs text-gray-600">
                        <div className="flex gap-2">
                          <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 text-blue-600 font-bold text-[10px]">1</div>
                          <div>
                            <p className="font-medium text-gray-800">Delay Minutes</p>
                            <p className="text-gray-500">How many minutes late the vessel will arrive compared to its scheduled ETA</p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0 text-green-600 font-bold text-[10px]">2</div>
                          <div>
                            <p className="font-medium text-gray-800">Predicted Arrival Time</p>
                            <p className="text-gray-500">Scheduled ETA + predicted delay = actual expected arrival</p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <div className="w-6 h-6 rounded-full bg-purple-100 flex items-center justify-center flex-shrink-0 text-purple-600 font-bold text-[10px]">3</div>
                          <div>
                            <p className="font-medium text-gray-800">Confidence Range</p>
                            <p className="text-gray-500">Lower–upper bound interval (±MAE 6.5 min)</p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          <div className="w-6 h-6 rounded-full bg-orange-100 flex items-center justify-center flex-shrink-0 text-orange-600 font-bold text-[10px]">4</div>
                          <div>
                            <p className="font-medium text-gray-800">Top Delay Factors</p>
                            <p className="text-gray-500">Which input features drove this specific prediction the most</p>
                          </div>
                        </div>
                      </div>
                    </CardContainer>
                    <CardContainer className="p-5 text-center text-gray-400">
                      <i className="fa-solid fa-bolt text-4xl mb-3 block opacity-20" />
                      <p className="text-sm font-medium text-gray-500">Fill in the form and click</p>
                      <p className="text-base font-bold text-blue-600 mt-1">⚡ Predict ETA Delay</p>
                      <p className="text-xs mt-2 text-gray-400">Result appears here with delay estimate,<br />confidence interval, and top delay drivers</p>
                    </CardContainer>
                  </>
                )}

                {/* Prediction result — combined ETA + Berth */}
                {etaResult && (() => {
                  // Support both flat (eta-only) and nested (eta-and-berth) responses
                  const eta   = etaResult.eta   || etaResult
                  const berth = etaResult.berth  || null
                  const berthErr = etaResult.berth_error || null
                  return (
                    <>
                      {/* ── Stage 1: ETA Result ── */}
                      <CardContainer className="p-5 border-2 border-blue-100">
                        <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-3">
                          <i className="fa-solid fa-clock mr-1" />Stage 1 — ETA Prediction
                          <span className="ml-2 text-gray-400 font-normal">#{eta.prediction_id}</span>
                        </p>
                        <div className="space-y-4">
                          <div className="text-center py-5 bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl">
                            <p className="text-5xl font-black text-blue-600 tabular-nums">{eta.predicted_delay_minutes}</p>
                            <p className="text-sm font-semibold text-blue-700 mt-1">minutes of delay</p>
                            <p className="text-xs text-blue-400 mt-1">
                              Range: {eta.lower_bound_minutes} – {eta.upper_bound_minutes} min
                            </p>
                          </div>
                          <div className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                            <p className="text-xs text-gray-500 mb-0.5">Expected Arrival</p>
                            <p className="font-bold text-gray-900 text-base">
                              {eta.predicted_eta ? fmtDt(eta.predicted_eta) : '—'}
                            </p>
                            <p className="text-[10px] text-gray-400 mt-0.5">Scheduled ETA + {eta.predicted_delay_minutes} min delay</p>
                          </div>
                          <div>
                            <p className="text-xs text-gray-500 mb-1.5">Prediction Confidence</p>
                            <ConfBar score={eta.confidence_score} />
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                              <p className="text-gray-400">MAE</p>
                              <p className="font-semibold text-gray-800">{eta.model_mae_minutes} min</p>
                            </div>
                            <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                              <p className="text-gray-400">R²</p>
                              <p className="font-semibold text-gray-800">{eta.model_r2}</p>
                            </div>
                          </div>
                        </div>
                      </CardContainer>

                      {/* ── Top Delay Factors ── */}
                      <CardContainer className="p-5">
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                          <i className="fa-solid fa-ranking-star mr-1.5" />Top Delay Factors
                        </p>
                        <div className="space-y-2.5">
                          {(eta.top_delay_factors || []).map((f, i) => (
                            <div key={f.feature} className="flex items-center gap-2">
                              <span className={`text-xs font-bold w-5 text-right flex-shrink-0 ${i === 0 ? 'text-orange-500' : 'text-gray-300'}`}>
                                {i + 1}
                              </span>
                              <div className="flex-1">
                                <div className="flex justify-between mb-0.5">
                                  <span className="text-xs font-medium text-gray-700 capitalize">{f.feature.replace(/_/g, ' ')}</span>
                                  <span className="text-xs text-gray-400 font-semibold">{f.importance_pct}%</span>
                                </div>
                                <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                                  <div className={`h-1.5 rounded-full ${i === 0 ? 'bg-orange-400' : i < 3 ? 'bg-blue-500' : 'bg-blue-300'}`}
                                    style={{ width:`${Math.min(100, f.importance_pct * 3)}%` }} />
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </CardContainer>

                      {/* ── Stage 2: Berth Assignment ── */}
                      {berth ? (
                        <CardContainer className="p-5 border-2 border-green-100">
                          <p className="text-xs font-semibold text-green-700 uppercase tracking-wide mb-3">
                            <i className="fa-solid fa-anchor mr-1" />Stage 2 — Berth Assignment
                            <span className="ml-2 text-gray-400 font-normal">req #{berth.request_id}</span>
                          </p>
                          {/* Berth name hero */}
                          <div className="text-center py-4 bg-gradient-to-br from-green-50 to-emerald-100 rounded-xl mb-4">
                            <p className="text-3xl font-black text-green-700">{berth.assigned_berth}</p>
                            <p className="text-xs text-green-600 mt-1 font-medium">Assigned Berth</p>
                          </div>
                          {/* Time details */}
                          <div className="grid grid-cols-2 gap-2 text-xs mb-4">
                            <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                              <p className="text-gray-400">Berthing Start</p>
                              <p className="font-semibold text-gray-800 text-sm">{fmtDt(berth.berthing_start_time)}</p>
                            </div>
                            <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                              <p className="text-gray-400">Departure</p>
                              <p className="font-semibold text-gray-800 text-sm">{fmtDt(berth.departure_time)}</p>
                            </div>
                            <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                              <p className="text-gray-400">Waiting Time</p>
                              <p className="font-semibold text-gray-800 text-sm">{berth.waiting_time_minutes} min</p>
                            </div>
                            <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                              <p className="text-gray-400">Berth Utilization</p>
                              <p className="font-semibold text-gray-800 text-sm">{Math.round(berth.berth_utilization * 100)}%</p>
                            </div>
                          </div>
                          {/* Utilization bar */}
                          <div className="mb-4">
                            <div className="flex justify-between text-xs text-gray-500 mb-1">
                              <span>Berth Utilization</span>
                              <span className="font-semibold">{Math.round(berth.berth_utilization * 100)}%</span>
                            </div>
                            <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                              <div className={`h-2.5 rounded-full transition-all ${
                                berth.berth_utilization > 0.85 ? 'bg-red-500' :
                                berth.berth_utilization > 0.65 ? 'bg-yellow-400' : 'bg-green-500'
                              }`} style={{ width: `${Math.round(berth.berth_utilization * 100)}%` }} />
                            </div>
                          </div>
                          {/* Status flags */}
                          <div className="flex gap-2 mb-3">
                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${
                              berth.conflict_flag
                                ? 'bg-red-50 text-red-700 border-red-200'
                                : 'bg-green-50 text-green-700 border-green-200'
                            }`}>
                              <i className={`fa-solid ${berth.conflict_flag ? 'fa-triangle-exclamation' : 'fa-circle-check'} text-[10px]`} />
                              {berth.conflict_flag ? 'Schedule Conflict' : 'No Conflict'}
                            </span>
                            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium border ${
                              berth.congestion_flag
                                ? 'bg-orange-50 text-orange-700 border-orange-200'
                                : 'bg-green-50 text-green-700 border-green-200'
                            }`}>
                              <i className={`fa-solid ${berth.congestion_flag ? 'fa-traffic-light' : 'fa-circle-check'} text-[10px]`} />
                              {berth.congestion_flag ? 'Port Congested' : 'Port Clear'}
                            </span>
                          </div>
                          {/* Alerts */}
                          {berth.alert_messages && berth.alert_messages.length > 0 && (
                            <div className="p-3 bg-amber-50 border border-amber-100 rounded-lg">
                              <p className="text-xs font-semibold text-amber-700 mb-1">
                                <i className="fa-solid fa-bell mr-1" />Alerts ({berth.alert_messages.length})
                              </p>
                              <ul className="space-y-1">
                                {berth.alert_messages.map((msg, i) => (
                                  <li key={i} className="text-xs text-amber-700 flex gap-1.5">
                                    <i className="fa-solid fa-circle-dot text-[8px] mt-1 flex-shrink-0" />{msg}
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </CardContainer>
                      ) : berthErr ? (
                        <CardContainer className="p-4 border border-orange-100 bg-orange-50/50">
                          <p className="text-xs font-semibold text-orange-600 mb-1">
                            <i className="fa-solid fa-triangle-exclamation mr-1" />Berth Allocation Failed
                          </p>
                          <p className="text-xs text-orange-700">{berthErr}</p>
                          <p className="text-[10px] text-orange-500 mt-1">ETA prediction above is still valid.</p>
                        </CardContainer>
                      ) : null}

                      <button type="button" onClick={() => { setEtaResult(null); setEtaError('') }}
                        className="w-full text-xs text-gray-400 hover:text-gray-600 py-1 transition-colors underline">
                        Clear result &amp; predict again
                      </button>
                    </>
                  )
                })()}
              </div>
            </div>
          </>
        )}

        {/* ════════════════════════════ MODEL INFO ════════════════════════ */}
        {tab === 'Model Info' && (
          <div className="space-y-5">
            {modelLoading ? (
              <div className="text-center py-12 text-gray-400">
                <i className="fa-solid fa-spinner fa-spin mr-2" />Loading model info…
              </div>
            ) : modelInfo ? (() => {
              const allModels   = modelInfo.available_models?.length ? modelInfo.available_models : [modelInfo.model_name]
              const metrics     = modelInfo.metrics || {}
              const active      = modelInfo.model_name
              const sortedNames = [...allModels].sort((a, b) => (metrics[a]?.MAE ?? 99) - (metrics[b]?.MAE ?? 99))

              async function handleSetActive(name) {
                setActivating(name)
                try {
                  await setActiveModel.mutateAsync(name)
                } catch { /* ignore */ }
                finally { setActivating(null) }
              }

              const COLORS = { CatBoost: '#6366f1', XGBoost: '#f97316', LightGBM: '#22c55e' }
              const ICONS  = { CatBoost: 'fa-cat', XGBoost: 'fa-bolt', LightGBM: 'fa-feather-pointed' }

              return (
                <>
                  {/* ── Model comparison grid ── */}
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                      <i className="fa-solid fa-trophy text-yellow-500" />
                      Model Comparison — pick the active prediction engine
                    </h3>
                    <div className="grid grid-cols-3 gap-4">
                      {sortedNames.map((name, rank) => {
                        const m      = metrics[name] || {}
                        const isActive = name === active
                        const color  = COLORS[name] || '#6b7280'
                        const icon   = ICONS[name]  || 'fa-brain'
                        const isBest = rank === 0
                        return (
                          <div key={name}
                            className="rounded-2xl p-5 border-2 transition-all"
                            style={{
                              borderColor: isActive ? color : 'transparent',
                              background:  isActive ? `${color}08` : '#f9fafb',
                              outline: isActive ? `1px solid ${color}33` : 'none',
                            }}>
                            {/* Header */}
                            <div className="flex items-start justify-between mb-4">
                              <div className="flex items-center gap-2.5">
                                <div className="w-9 h-9 rounded-xl flex items-center justify-center text-white text-sm flex-shrink-0"
                                  style={{ background: color }}>
                                  <i className={`fa-solid ${icon}`} />
                                </div>
                                <div>
                                  <p className="font-bold text-gray-900 text-sm leading-tight">{name}</p>
                                  <p className="text-[10px] text-gray-400 mt-0.5">Gradient Boosting</p>
                                </div>
                              </div>
                              <div className="flex flex-col items-end gap-1">
                                {isBest && (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full text-white"
                                    style={{ background: '#f59e0b' }}>
                                    <i className="fa-solid fa-crown mr-1" />BEST
                                  </span>
                                )}
                                {isActive && (
                                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full text-white"
                                    style={{ background: color }}>
                                    <i className="fa-solid fa-circle-dot mr-1" />ACTIVE
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Metrics */}
                            <div className="space-y-2 mb-4">
                              {[
                                { label: 'MAE', value: m.MAE != null ? `${m.MAE} min` : '—', desc: 'Avg prediction error' },
                                { label: 'RMSE', value: m.RMSE != null ? `${m.RMSE} min` : '—', desc: 'Error spread' },
                                { label: 'R²', value: m.R2 != null ? (m.R2 * 100).toFixed(1) + '%' : '—', desc: 'Variance explained' },
                                { label: '±15 min', value: m.within_15_pct != null ? `${m.within_15_pct}%` : '—', desc: 'Accuracy within ±15 min' },
                              ].map(({ label, value, desc }) => (
                                <div key={label} className="flex items-center justify-between py-1.5 border-b border-gray-100 last:border-0">
                                  <div>
                                    <p className="text-xs font-semibold text-gray-700">{label}</p>
                                    <p className="text-[10px] text-gray-400">{desc}</p>
                                  </div>
                                  <p className="text-sm font-bold" style={{ color }}>{value}</p>
                                </div>
                              ))}
                            </div>

                            {/* R² bar */}
                            {m.R2 != null && (
                              <div className="mb-4">
                                <div className="h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                  <div className="h-full rounded-full transition-all duration-700"
                                    style={{ width: `${(m.R2 * 100).toFixed(1)}%`, background: color }} />
                                </div>
                                <p className="text-[10px] text-gray-400 mt-1 text-right">{(m.R2 * 100).toFixed(1)}% accuracy</p>
                              </div>
                            )}

                            {/* Action button */}
                            {isActive ? (
                              <div className="w-full text-center text-xs font-semibold py-2 rounded-lg"
                                style={{ background: `${color}15`, color }}>
                                <i className="fa-solid fa-circle-check mr-1.5" />Currently active
                              </div>
                            ) : (
                              <button
                                onClick={() => handleSetActive(name)}
                                disabled={activating !== null}
                                className="w-full text-xs font-semibold py-2 rounded-lg border transition-all disabled:opacity-50"
                                style={{ borderColor: color, color, background: 'white' }}
                                onMouseEnter={e => { e.currentTarget.style.background = `${color}12` }}
                                onMouseLeave={e => { e.currentTarget.style.background = 'white' }}>
                                {activating === name
                                  ? <><i className="fa-solid fa-spinner fa-spin mr-1.5" />Switching…</>
                                  : <><i className="fa-solid fa-bolt mr-1.5" />Set as Active</>}
                              </button>
                            )}
                          </div>
                        )
                      })}
                    </div>
                    {allModels.length === 1 && (
                      <p className="text-xs text-gray-400 mt-3 text-center">
                        <i className="fa-solid fa-circle-info mr-1" />
                        Run the multi-model retrain script to compare CatBoost, XGBoost, and LightGBM side by side.
                      </p>
                    )}
                  </div>

                  {/* ── Meta + Feature importance ── */}
                  <div className="grid grid-cols-2 gap-5">
                    <CardContainer className="p-5">
                      <SectionHeader title="Artifact Metadata" />
                      <div className="grid grid-cols-2 gap-3">
                        {[
                          { label: 'Active Model', value: active },
                          { label: 'Features',     value: modelInfo.feature_count },
                          { label: 'Version',      value: modelInfo.model_version },
                          { label: 'Trained',      value: modelInfo.saved_at ? new Date(modelInfo.saved_at).toLocaleDateString() : '—' },
                          { label: 'Status',       value: modelInfo.status },
                          { label: 'Model Age',    value: `${modelInfo.model_age_days}d` },
                        ].map(i => (
                          <div key={i.label} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                            <p className="text-[10px] text-gray-400 uppercase tracking-wide">{i.label}</p>
                            <p className="text-sm font-semibold text-gray-900 mt-0.5 capitalize">{i.value}</p>
                          </div>
                        ))}
                      </div>
                      {modelInfo.staleness_warning && (
                        <div className="mt-3 p-3 bg-yellow-50 border border-yellow-100 rounded-lg text-xs text-yellow-700">
                          <i className="fa-solid fa-triangle-exclamation mr-1" />{modelInfo.staleness_warning}
                        </div>
                      )}
                    </CardContainer>

                    <CardContainer className="p-5">
                      <SectionHeader title="Feature Importance (Top 20)" />
                      <div className="space-y-1.5 overflow-y-auto max-h-72">
                        {(modelInfo.feature_importance || []).map((f, i) => (
                          <div key={f.feature} className="flex items-center gap-2">
                            <span className="text-[10px] text-gray-300 font-bold w-4 text-right flex-shrink-0">{i + 1}</span>
                            <div className="flex-1 min-w-0">
                              <div className="flex justify-between items-center mb-0.5">
                                <span className="text-xs font-medium text-gray-700 truncate capitalize">{f.feature.replace(/_/g, ' ')}</span>
                                <span className="text-[10px] text-gray-400 ml-1 flex-shrink-0">{f.importance_pct}%</span>
                              </div>
                              <div className="h-1 bg-gray-100 rounded-full">
                                <div className="h-full rounded-full"
                                  style={{
                                    width: `${Math.min(100, f.importance_pct / ((modelInfo.feature_importance[0]?.importance_pct) || 1) * 100)}%`,
                                    background: i < 3 ? '#6366f1' : i < 7 ? '#a5b4fc' : '#e0e7ff',
                                  }} />
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                      <div className="mt-3 p-2.5 bg-amber-50 border border-amber-100 rounded-lg text-[11px] text-amber-700">
                        <i className="fa-solid fa-lightbulb mr-1" />
                        <strong>Key insight:</strong> Queue × Congestion and Wave × Congestion dominate delay — reducing port congestion has the highest ROI.
                      </div>
                    </CardContainer>
                  </div>
                </>
              )
            })() : (
              <div className="text-center py-12 text-red-400 text-sm">
                <i className="fa-solid fa-triangle-exclamation mr-2" />Could not load model info. Ensure the backend is running.
              </div>
            )}
          </div>
        )}
      </div>
    </MainLayout>
  )
}
