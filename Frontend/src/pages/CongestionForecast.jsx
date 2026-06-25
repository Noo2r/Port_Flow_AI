import { useState, useEffect, useCallback } from 'react'
import Sidebar from '../components/Sidebar'
import {
  useCongestionPortOverview, useCongestionEvaluation, useCongestionModelInfo,
  useCongestionPredict,
} from '../hooks/queries'

// ── Colour system (matches ModelEvaluation and the rest of the dark-theme pages)
const CARD_BG  = '#080f1e'
const BORDER   = 'rgba(148,163,184,0.1)'
const TRACK    = 'rgba(148,163,184,0.08)'   // progress-bar track
const INPUT_BG = '#0d1929'                  // input / select fill
const TEXT     = '#f0f6ff'
const MUTED    = '#94a3b8'
const DIM      = '#3d5a8a'
const ORANGE   = '#f97316'

// ── Status colours for congestion labels
const LABEL_STYLE = {
  Low:      { bg: 'bg-green-500/15',  text: 'text-green-400',  borderColor: 'rgba(34,197,94,0.3)',  ring: '#22c55e' },
  Medium:   { bg: 'bg-amber-500/15',  text: 'text-amber-400',  borderColor: 'rgba(245,158,11,0.3)', ring: '#f59e0b' },
  High:     { bg: 'bg-orange-500/15', text: 'text-orange-400', borderColor: 'rgba(249,115,22,0.3)', ring: '#f97316' },
  Critical: { bg: 'bg-red-500/15',    text: 'text-red-400',    borderColor: 'rgba(239,68,68,0.3)',  ring: '#ef4444' },
}

function labelStyle(label) {
  return LABEL_STYLE[label] || LABEL_STYLE.Medium
}

// ── Gauge SVG ────────────────────────────────────────────────────────────────
function CongestionGauge({ pct = 0, label = 'Low', color = '#22c55e' }) {
  const r = 56, cx = 70, cy = 70
  const circumference = Math.PI * r
  const stroke = circumference * (pct / 100)
  return (
    <svg viewBox="0 0 140 85" className="w-full max-w-[200px]">
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none" stroke={TRACK} strokeWidth="12" strokeLinecap="round" />
      <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
        fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
        strokeDasharray={`${stroke} ${circumference}`}
        style={{ transition: 'stroke-dasharray 0.8s ease' }} />
      <text x={cx} y={cy - 10} textAnchor="middle" fill={TEXT} fontSize="22" fontWeight="700">{pct}%</text>
      <text x={cx} y={cy + 8}  textAnchor="middle" fill={color} fontSize="11" fontWeight="600">{label}</text>
    </svg>
  )
}

// ── Queue bar ────────────────────────────────────────────────────────────────
function QueueBar({ count = 0, max = 13 }) {
  const pct   = Math.min((count / max) * 100, 100)
  const color = pct < 30 ? '#22c55e' : pct < 60 ? '#f59e0b' : pct < 80 ? '#f97316' : '#ef4444'
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs" style={{ color: MUTED }}>
        <span>Queue length</span>
        <span className="font-semibold" style={{ color }}>{count} vessels</span>
      </div>
      <div className="h-3 rounded-full overflow-hidden" style={{ background: TRACK }}>
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
      </div>
      <div className="flex justify-between text-[10px]" style={{ color: DIM }}>
        <span>0</span><span>{max}</span>
      </div>
    </div>
  )
}

// ── Port card ────────────────────────────────────────────────────────────────
function PortCard({ port }) {
  const s = labelStyle(port.congestion_label)
  return (
    <div className={`rounded-xl p-3 flex flex-col gap-2 ${s.bg}`}
      style={{ border: `1px solid ${s.borderColor}` }}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold truncate" style={{ color: MUTED }}>
          {port.port_name || port.port_code}
        </span>
        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${s.bg} ${s.text}`}
          style={{ border: `1px solid ${s.borderColor}` }}>
          {port.congestion_label}
        </span>
      </div>
      <div className="flex gap-3 text-xs">
        <div>
          <div style={{ color: DIM }}>Congestion</div>
          <div className="font-bold" style={{ color: port.congestion_color }}>{port.congestion_pct}%</div>
        </div>
        <div>
          <div style={{ color: DIM }}>Queue</div>
          <div className="font-bold" style={{ color: TEXT }}>{port.queue_length}</div>
        </div>
        <div>
          <div style={{ color: DIM }}>Risk</div>
          <div className="font-bold" style={{ color: TEXT }}>{port.risk_pct}%</div>
        </div>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: TRACK }}>
        <div className="h-full rounded-full"
          style={{ width: `${port.congestion_pct}%`, background: port.congestion_color }} />
      </div>
    </div>
  )
}

// ── Form constants (match training dataset exactly) ──────────────────────────
const VESSEL_TYPES = ['Bulk Carrier','Car Carrier','Container','Cruise','Feeder','General Cargo','LNG Carrier','RoRo','Tanker','VLCC']
const TRAFFIC_OPTS = ['Low','Medium','High']
const PORT_IDS     = ['PORT_A','PORT_B','PORT_C','PORT_D','PORT_E','PORT_F','PORT_G','PORT_H']
const PORT_NAMES   = {
  PORT_A: 'Port Alpha',   PORT_B: 'Port Bravo',   PORT_C: 'Port Capri',   PORT_D: 'Port Delta',
  PORT_E: 'Port Echo',    PORT_F: 'Port Foxtrot', PORT_G: 'Port Gulf',    PORT_H: 'Port Harbor',
}

const DEFAULTS = {
  port_id: 'PORT_A', vessel_type: 'Container', traffic_density: 'Medium',
  loa_m: 230, draft_m: 11, gross_tonnage: 58000, vessel_age_years: 8,
  distance_to_port_nm: 80,
  wave_height_m: 0.9, wind_speed_knots: 10, visibility_km: 15,
  precipitation_mm: 0.5, temperature_c: 20,
  port_congestion_index: 0.42, berth_queue_length: 4,
  crane_availability_ratio: 0.77, port_avg_delay_last_24h: 25,
  estimated_service_time_hours: 20,
  eta_prediction_minutes: '',
}

const INPUT_STYLE = {
  background: INPUT_BG,
  border: `1px solid ${BORDER}`,
  color: TEXT,
  borderRadius: '0.5rem',
  padding: '6px 12px',
  fontSize: '0.875rem',
  outline: 'none',
  width: '100%',
}

function InputRow({ label, name, form, setForm, type = 'number', options, min, max, step = '1' }) {
  const handleFocus = e => { e.target.style.borderColor = ORANGE }
  const handleBlur  = e => { e.target.style.borderColor = BORDER }
  return (
    <div className="flex flex-col gap-1">
      <label style={{ fontSize: '11px', color: MUTED, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </label>
      {options ? (
        <select
          value={form[name]}
          onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))}
          onFocus={handleFocus} onBlur={handleBlur}
          style={{ ...INPUT_STYLE }}
        >
          {options.map(o => <option key={o} value={o} style={{ background: CARD_BG }}>{o}</option>)}
        </select>
      ) : (
        <input
          type={type} value={form[name]} min={min} max={max} step={step}
          onChange={e => setForm(f => ({ ...f, [name]: e.target.value }))}
          onFocus={handleFocus} onBlur={handleBlur}
          style={{ ...INPUT_STYLE }}
        />
      )}
    </div>
  )
}

function SectionDivider({ label }) {
  return (
    <>
      <div style={{ height: '1px', background: BORDER }} />
      <p style={{ fontSize: '10px', color: MUTED, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.1em' }}>
        {label}
      </p>
    </>
  )
}

// ── Main page ────────────────────────────────────────────────────────────────
// Coerce the form's string input values to the numeric types the backend
// expects — shared by the initial-default forecast and the on-demand one.
function buildPredictPayload(f) {
  return {
    ...f,
    loa_m:                       parseFloat(f.loa_m),
    draft_m:                     parseFloat(f.draft_m),
    gross_tonnage:               parseFloat(f.gross_tonnage),
    vessel_age_years:            parseFloat(f.vessel_age_years),
    distance_to_port_nm:         parseFloat(f.distance_to_port_nm),
    wave_height_m:               parseFloat(f.wave_height_m),
    wind_speed_knots:            parseFloat(f.wind_speed_knots),
    visibility_km:               parseFloat(f.visibility_km),
    precipitation_mm:            parseFloat(f.precipitation_mm),
    temperature_c:               parseFloat(f.temperature_c),
    port_congestion_index:       parseFloat(f.port_congestion_index),
    berth_queue_length:          parseInt(f.berth_queue_length),
    crane_availability_ratio:    parseFloat(f.crane_availability_ratio),
    port_avg_delay_last_24h:     parseFloat(f.port_avg_delay_last_24h),
    estimated_service_time_hours:parseFloat(f.estimated_service_time_hours),
    eta_prediction_minutes: f.eta_prediction_minutes !== '' ? parseFloat(f.eta_prediction_minutes) : null,
  }
}

export default function CongestionForecast() {
  const [form, setForm]   = useState(DEFAULTS)
  const [error, setError] = useState(null)
  const [tab, setTab]     = useState('ports')

  const { data: overview, isLoading: ovLoading } = useCongestionPortOverview()
  const { data: evalData }                       = useCongestionEvaluation()
  const { data: modelInfo }                      = useCongestionModelInfo()
  const congestionPredict                        = useCongestionPredict()

  const result  = congestionPredict.data
  const loading = congestionPredict.isPending

  // Seed the result panel with a forecast for the default form values on
  // first mount — matches the original behaviour of showing a populated
  // panel immediately rather than an empty state.
  useEffect(() => {
    congestionPredict.mutate(buildPredictPayload(DEFAULTS))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handlePredict = useCallback(() => {
    setError(null)
    congestionPredict.mutate(buildPredictPayload(form), {
      onError: (e) => setError(e?.message || 'Prediction failed. Check that the API is running.'),
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form])

  const s = result ? labelStyle(result.congestion_label) : labelStyle('Low')

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: '#030710', color: TEXT }}>
      <Sidebar />
      <div className="flex-1 overflow-y-auto">

        {/* ── Header ── */}
        <div className="sticky top-0 z-10 px-6 py-4 flex items-center justify-between"
          style={{ background: 'rgba(3,7,16,0.92)', backdropFilter: 'blur(12px)', borderBottom: `1px solid ${BORDER}` }}>
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2" style={{ color: TEXT }}>
              <i className="fa-solid fa-water" style={{ color: ORANGE }} />
              Congestion Forecast
            </h1>
            <p className="text-xs mt-0.5" style={{ color: DIM }}>Stage 3 — AI-powered port congestion &amp; queue prediction</p>
          </div>
          {modelInfo && (
            <div className="hidden md:flex items-center gap-3 text-xs" style={{ color: MUTED }}>
              {[
                `${modelInfo.congestion_model_name} + ${modelInfo.queue_model_name}`,
                `R² ${modelInfo.metrics?.congestion?.R2?.toFixed(4)}`,
                `${modelInfo.training_rows?.toLocaleString()} rows trained`,
              ].map(txt => (
                <span key={txt} className="px-2 py-1 rounded-lg"
                  style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                  {txt}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* ── Tabs ── */}
        <div className="px-6 pt-4 flex gap-2" style={{ borderBottom: `1px solid ${BORDER}` }}>
          {[
            { id: 'forecast',   icon: 'fa-magnifying-glass-chart', label: 'Live Forecast' },
            { id: 'ports',      icon: 'fa-map-location-dot',       label: 'Port Overview' },
            { id: 'evaluation', icon: 'fa-flask',                   label: 'Model Evaluation' },
          ].map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{
                padding: '10px 16px',
                fontSize: '0.875rem',
                fontWeight: 500,
                borderBottom: `2px solid ${tab === t.id ? ORANGE : 'transparent'}`,
                color: tab === t.id ? ORANGE : DIM,
                background: tab === t.id ? `${ORANGE}08` : 'transparent',
                borderRadius: '8px 8px 0 0',
                marginBottom: '-1px',
                transition: 'all 0.15s',
                cursor: 'pointer',
              }}
              onMouseEnter={e => { if (tab !== t.id) e.currentTarget.style.color = MUTED }}
              onMouseLeave={e => { if (tab !== t.id) e.currentTarget.style.color = DIM }}
            >
              <i className={`fa-solid ${t.icon} mr-1.5`} />{t.label}
            </button>
          ))}
        </div>

        <div className="p-6 space-y-6">

          {/* ══════ TAB: FORECAST ══════ */}
          {tab === 'forecast' && (
            <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">

              {/* Input panel */}
              <div className="xl:col-span-2 rounded-2xl p-5 space-y-4"
                style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                <h2 className="text-sm font-semibold flex items-center gap-2" style={{ color: TEXT }}>
                  <i className="fa-solid fa-sliders" style={{ color: ORANGE }} />
                  Input Parameters
                </h2>

                <div className="grid grid-cols-2 gap-3">
                  {/* Port selector — shows code + name */}
                  <div className="flex flex-col gap-1">
                    <label style={{ fontSize: '11px', color: MUTED, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Port</label>
                    <select
                      value={form.port_id}
                      onChange={e => setForm(f => ({ ...f, port_id: e.target.value }))}
                      onFocus={e => { e.target.style.borderColor = ORANGE }}
                      onBlur={e  => { e.target.style.borderColor = BORDER }}
                      style={{ ...INPUT_STYLE }}
                    >
                      {PORT_IDS.map(id => (
                        <option key={id} value={id} style={{ background: CARD_BG }}>
                          {id} — {PORT_NAMES[id]}
                        </option>
                      ))}
                    </select>
                  </div>
                  <InputRow label="Vessel Type"     name="vessel_type"    form={form} setForm={setForm} options={VESSEL_TYPES} />
                  <InputRow label="Traffic Density" name="traffic_density"form={form} setForm={setForm} options={TRAFFIC_OPTS} />
                  <InputRow label="ETA Delay (min)" name="eta_prediction_minutes" form={form} setForm={setForm} min="-15" max="200" step="0.1" />
                </div>

                <SectionDivider label="Vessel" />
                <div className="grid grid-cols-2 gap-3">
                  <InputRow label="LOA (m)"       name="loa_m"               form={form} setForm={setForm} min="65"   max="399"    step="0.1" />
                  <InputRow label="Draft (m)"     name="draft_m"             form={form} setForm={setForm} min="4"    max="22"     step="0.1" />
                  <InputRow label="Gross Tonnage" name="gross_tonnage"       form={form} setForm={setForm} min="2000" max="161000" step="100" />
                  <InputRow label="Age (years)"   name="vessel_age_years"    form={form} setForm={setForm} min="0"    max="35"     step="0.5" />
                  <InputRow label="Distance (nm)" name="distance_to_port_nm" form={form} setForm={setForm} min="0.5"  max="788"    step="0.5" />
                </div>

                <SectionDivider label="Weather" />
                <div className="grid grid-cols-2 gap-3">
                  <InputRow label="Wave Ht (m)"    name="wave_height_m"    form={form} setForm={setForm} min="0"   max="7.4"  step="0.1" />
                  <InputRow label="Wind (kn)"      name="wind_speed_knots" form={form} setForm={setForm} min="0.1" max="60"   step="0.1" />
                  <InputRow label="Visibility (km)"name="visibility_km"    form={form} setForm={setForm} min="3.5" max="27.7" step="0.1" />
                  <InputRow label="Precip (mm)"    name="precipitation_mm" form={form} setForm={setForm} min="0"   max="12.8" step="0.1" />
                  <InputRow label="Temp (°C)"      name="temperature_c"    form={form} setForm={setForm} min="-5"  max="42"   step="0.1" />
                </div>

                <SectionDivider label="Port State" />
                <div className="grid grid-cols-2 gap-3">
                  <InputRow label="Congestion Idx"  name="port_congestion_index"       form={form} setForm={setForm} min="0"    max="1"    step="0.01" />
                  <InputRow label="Queue Length"    name="berth_queue_length"          form={form} setForm={setForm} min="0"    max="13"   step="1" />
                  <InputRow label="Crane Avail."    name="crane_availability_ratio"    form={form} setForm={setForm} min="0.52" max="1"    step="0.01" />
                  <InputRow label="Avg Delay 24h"   name="port_avg_delay_last_24h"     form={form} setForm={setForm} min="-15"  max="67.2" step="0.1" />
                  <InputRow label="Service Time (h)"name="estimated_service_time_hours"form={form} setForm={setForm} min="4"    max="36"   step="0.5" />
                </div>

                {error && (
                  <div className="text-xs rounded-lg px-3 py-2"
                    style={{ color: '#fca5a5', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.2)' }}>
                    <i className="fa-solid fa-circle-exclamation mr-1" />{error}
                  </div>
                )}

                <button onClick={handlePredict} disabled={loading}
                  className="w-full py-3 rounded-xl font-semibold text-sm transition-all disabled:opacity-50"
                  style={{
                    background: loading ? `${ORANGE}50` : `linear-gradient(135deg,${ORANGE},#ea580c)`,
                    color: 'white',
                    boxShadow: loading ? 'none' : `0 0 20px ${ORANGE}40`,
                  }}>
                  {loading
                    ? <><i className="fa-solid fa-spinner fa-spin mr-2" />Forecasting…</>
                    : <><i className="fa-solid fa-wave-square mr-2" />Generate Forecast</>}
                </button>
              </div>

              {/* Result panel */}
              <div className="xl:col-span-3 space-y-4">
                {!result && !loading && (
                  <div className="h-full flex flex-col items-center justify-center rounded-2xl py-20 text-center"
                    style={{ border: `1px dashed ${BORDER}` }}>
                    <i className="fa-solid fa-spinner fa-spin text-3xl mb-3" style={{ color: DIM }} />
                    <p className="text-sm" style={{ color: MUTED }}>Loading forecast…</p>
                  </div>
                )}

                {result && (
                  <>
                    {/* Risk banner */}
                    <div className={`rounded-2xl p-5 flex items-center gap-5 ${s.bg}`}
                      style={{ border: `1px solid ${s.borderColor}` }}>
                      <div className="flex-shrink-0">
                        <CongestionGauge pct={result.congestion_pct} label={result.congestion_label} color={result.congestion_color} />
                      </div>
                      <div className="flex-1 space-y-3">
                        <div className={`text-2xl font-black ${s.text}`}>{result.congestion_label} Congestion</div>
                        <QueueBar count={result.queue_length} />
                        <div className="grid grid-cols-3 gap-3 text-xs">
                          {[
                            { label: 'Risk Score', value: `${result.risk_pct}%`,                        color: '#ef4444' },
                            { label: 'Certainty',  value: `${(result.confidence * 100).toFixed(1)}%`,   color: '#22c55e' },
                            { label: 'Queue',      value: `${result.queue_length}`,                     color: '#22d3ee' },
                          ].map(({ label, value, color }) => (
                            <div key={label} className="rounded-lg p-2 text-center"
                              style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                              <div style={{ color: DIM }}>{label}</div>
                              <div className="text-lg font-bold" style={{ color }}>{value}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>

                    {/* Feature importance */}
                    {result.top_factors?.length > 0 && (
                      <div className="rounded-2xl p-5 space-y-3"
                        style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                        <h3 className="text-sm font-semibold flex items-center gap-2" style={{ color: TEXT }}>
                          <i className="fa-solid fa-list-check" style={{ color: '#22d3ee' }} />
                          Top Influencing Factors
                        </h3>
                        <div className="space-y-2">
                          {result.top_factors.slice(0, 5).map((f, i) => (
                            <div key={i} className="flex items-center gap-3">
                              <div className="text-[10px] w-4 text-right" style={{ color: DIM }}>{i + 1}</div>
                              <div className="text-xs w-40 truncate" style={{ color: MUTED }}>{f.feature.replace(/_/g, ' ')}</div>
                              <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: TRACK }}>
                                <div className="h-full rounded-full"
                                  style={{ width: `${f.importance_pct}%`, background: i === 0 ? ORANGE : i === 1 ? '#f59e0b' : '#22d3ee' }} />
                              </div>
                              <div className="text-[11px] w-12 text-right" style={{ color: MUTED }}>{f.importance_pct}%</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Pipeline summary */}
                    <div className="rounded-2xl p-4" style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                      <p className="text-[10px] mb-3 uppercase tracking-widest" style={{ color: DIM }}>Pipeline</p>
                      <div className="flex items-center gap-2 text-xs flex-wrap">
                        {[
                          { label: 'Stage 1', sub: 'ETA Predictor',       icon: 'fa-clock',     color: '#818cf8' },
                          { label: 'Stage 2', sub: 'Berth Optimizer',     icon: 'fa-warehouse', color: '#22d3ee' },
                          { label: 'Stage 3', sub: 'Congestion Forecast', icon: 'fa-water',     color: ORANGE },
                        ].map((st, idx) => (
                          <div key={idx} className="flex items-center gap-2">
                            {idx > 0 && <i className="fa-solid fa-arrow-right" style={{ color: DIM }} />}
                            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg"
                              style={{ background: `${st.color}12`, border: `1px solid ${st.color}30` }}>
                              <i className={`fa-solid ${st.icon}`} style={{ color: st.color }} />
                              <div>
                                <div className="font-semibold" style={{ color: TEXT }}>{st.label}</div>
                                <div className="text-[10px]" style={{ color: DIM }}>{st.sub}</div>
                              </div>
                              {idx === 2 && <i className="fa-solid fa-check-circle ml-1" style={{ color: '#22c55e' }} />}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Models used */}
                    <div className="flex gap-3 text-xs">
                      {[
                        { icon: 'fa-chart-line',  iconColor: ORANGE,     label: 'Congestion model', value: result.congestion_model },
                        { icon: 'fa-people-group', iconColor: '#22d3ee', label: 'Queue model',      value: result.queue_model },
                      ].map(({ icon, iconColor, label, value }) => (
                        <div key={label} className="flex-1 rounded-xl p-3 flex items-center gap-2"
                          style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                          <i className={`fa-solid ${icon}`} style={{ color: iconColor }} />
                          <div>
                            <div style={{ color: DIM }}>{label}</div>
                            <div className="font-semibold" style={{ color: TEXT }}>{value}</div>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Model Efficiency */}
                    {modelInfo && (
                      <div className="rounded-2xl p-4 space-y-3"
                        style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                        <p className="text-[10px] uppercase tracking-widest font-semibold" style={{ color: MUTED }}>
                          <i className="fa-solid fa-gauge-high mr-1.5" style={{ color: ORANGE }} />
                          Model Efficiency
                        </p>
                        <div className="grid grid-cols-3 gap-3 text-xs">
                          {/* R² */}
                          <div className="flex flex-col gap-1.5">
                            <div style={{ color: DIM }}>R² Score</div>
                            <div className="text-base font-bold" style={{ color: '#818cf8' }}>
                              {(modelInfo.metrics.congestion.R2 * 100).toFixed(2)}%
                            </div>
                            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: TRACK }}>
                              <div className="h-full rounded-full" style={{ width: `${modelInfo.metrics.congestion.R2 * 100}%`, background: '#818cf8' }} />
                            </div>
                            <div style={{ color: DIM, fontSize: '10px' }}>Variance explained</div>
                          </div>
                          {/* MAE error band */}
                          <div className="flex flex-col gap-1.5">
                            <div style={{ color: DIM }}>Error Band</div>
                            <div className="text-base font-bold" style={{ color: '#22c55e' }}>
                              ±{(modelInfo.metrics.congestion.MAE * 100).toFixed(2)}%
                            </div>
                            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: TRACK }}>
                              <div className="h-full rounded-full" style={{ width: `${Math.max(2, (1 - modelInfo.metrics.congestion.MAE * 4) * 100)}%`, background: '#22c55e' }} />
                            </div>
                            <div style={{ color: DIM, fontSize: '10px' }}>Avg prediction MAE</div>
                          </div>
                          {/* Training rows */}
                          <div className="flex flex-col gap-1.5">
                            <div style={{ color: DIM }}>Trained On</div>
                            <div className="text-base font-bold" style={{ color: ORANGE }}>
                              {(modelInfo.training_rows / 1000).toFixed(0)}K
                            </div>
                            <div className="h-1.5 rounded-full overflow-hidden" style={{ background: TRACK }}>
                              <div className="h-full rounded-full" style={{ width: '100%', background: ORANGE }} />
                            </div>
                            <div style={{ color: DIM, fontSize: '10px' }}>Training samples</div>
                          </div>
                        </div>
                        {/* 95% accuracy band annotation */}
                        <div className="flex items-center gap-2 pt-1 text-[11px]"
                          style={{ borderTop: `1px solid ${BORDER}` }}>
                          <i className="fa-solid fa-circle-check" style={{ color: '#22c55e' }} />
                          <span style={{ color: MUTED }}>
                            95% of predictions within{' '}
                            <span className="font-semibold" style={{ color: '#22c55e' }}>
                              ±{(modelInfo.metrics.congestion.MAE * 2 * 100).toFixed(1)}%
                            </span>
                            {' '}of actual congestion
                          </span>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          {/* ══════ TAB: PORT OVERVIEW ══════ */}
          {tab === 'ports' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold flex items-center gap-2" style={{ color: TEXT }}>
                  <i className="fa-solid fa-map-location-dot" style={{ color: '#22d3ee' }} />
                  Port Congestion Overview
                </h2>
                {overview && (
                  <span className="text-xs" style={{ color: DIM }}>
                    {overview.count} ports · updated {new Date(overview.generated).toLocaleTimeString()}
                  </span>
                )}
              </div>

              {ovLoading && (
                <div className="flex items-center justify-center py-20">
                  <i className="fa-solid fa-spinner fa-spin text-2xl mr-3" style={{ color: MUTED }} />
                  <span className="text-sm" style={{ color: MUTED }}>Loading port forecasts…</span>
                </div>
              )}

              {!ovLoading && overview?.ports?.length > 0 && (
                <>
                  {/* Summary row */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    {['Low','Medium','High','Critical'].map(lbl => {
                      const count = overview.ports.filter(p => p.congestion_label === lbl).length
                      const st = labelStyle(lbl)
                      return (
                        <div key={lbl} className={`rounded-xl p-3 text-center ${st.bg}`}
                          style={{ border: `1px solid ${st.borderColor}` }}>
                          <div className={`text-2xl font-black ${st.text}`}>{count}</div>
                          <div className="text-xs mt-0.5" style={{ color: MUTED }}>{lbl} congestion</div>
                        </div>
                      )
                    })}
                  </div>

                  {/* Port cards */}
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                    {overview.ports.map(port => <PortCard key={port.port_id} port={port} />)}
                  </div>

                  {/* Comparison bar */}
                  <div className="rounded-2xl p-5" style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                    <h3 className="text-xs font-semibold mb-4 uppercase tracking-widest" style={{ color: MUTED }}>
                      Congestion Comparison
                    </h3>
                    <div className="space-y-3">
                      {[...overview.ports]
                        .sort((a, b) => b.congestion_level - a.congestion_level)
                        .map(p => (
                          <div key={p.port_id} className="flex items-center gap-3 text-xs">
                            <div className="w-20 truncate" style={{ color: MUTED }}>{p.port_name || p.port_code}</div>
                            <div className="flex-1 h-5 rounded-full overflow-hidden relative" style={{ background: TRACK }}>
                              <div className="h-full rounded-full transition-all duration-700 flex items-center pl-2"
                                style={{ width: `${p.congestion_pct}%`, background: p.congestion_color }}>
                                <span className="text-[10px] font-bold hidden sm:block" style={{ color: 'rgba(255,255,255,0.85)' }}>
                                  {p.congestion_pct}%
                                </span>
                              </div>
                            </div>
                            <div className="w-12 text-right font-semibold" style={{ color: p.congestion_color }}>{p.congestion_pct}%</div>
                            <span className={`text-[10px] px-1.5 py-0.5 rounded ${labelStyle(p.congestion_label).bg} ${labelStyle(p.congestion_label).text}`}>
                              {p.congestion_label}
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>
                </>
              )}

              {!ovLoading && (!overview || overview.ports.length === 0) && (
                <div className="flex flex-col items-center justify-center py-20 text-center">
                  <i className="fa-solid fa-map-location-dot text-4xl mb-3" style={{ color: DIM }} />
                  <p className="text-sm" style={{ color: MUTED }}>No port data available</p>
                  <p className="text-xs mt-1" style={{ color: DIM }}>Ports must be registered in the system first</p>
                </div>
              )}
            </div>
          )}

          {/* ══════ TAB: EVALUATION ══════ */}
          {tab === 'evaluation' && (
            <div className="space-y-5">
              <h2 className="text-sm font-semibold flex items-center gap-2" style={{ color: TEXT }}>
                <i className="fa-solid fa-flask" style={{ color: '#f59e0b' }} />
                Stage 3 Model Evaluation
              </h2>

              {evalData ? (
                <>
                  {/* Model cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {Object.entries(evalData.models).map(([key, m]) => (
                      <div key={key} className="rounded-2xl p-5 space-y-4"
                        style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                        <div className="flex items-center justify-between">
                          <h3 className="font-semibold flex items-center gap-2" style={{ color: TEXT }}>
                            <i className={`fa-solid ${key === 'congestion' ? 'fa-water' : 'fa-people-group'}`}
                              style={{ color: key === 'congestion' ? ORANGE : '#22d3ee' }} />
                            {key === 'congestion' ? 'Congestion Level' : 'Queue Length'}
                          </h3>
                          <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${m.grade === 'Excellent' ? 'bg-green-500/15 text-green-400' : 'bg-amber-500/15 text-amber-400'}`}>
                            {m.grade}
                          </span>
                        </div>
                        <div className="text-xs" style={{ color: MUTED }}>{m.target}</div>
                        <div className="grid grid-cols-3 gap-3">
                          {[
                            { label: 'MAE',  value: m.MAE,  color: '#22c55e' },
                            { label: 'RMSE', value: m.RMSE, color: '#f59e0b' },
                            { label: 'R²',   value: m.R2,   color: '#818cf8' },
                          ].map(({ label, value, color }) => (
                            <div key={label} className="rounded-xl p-3 text-center"
                              style={{ background: `${color}10`, border: `1px solid ${color}25` }}>
                              <div className="text-[10px] mb-1" style={{ color: MUTED }}>{label}</div>
                              <div className="text-xl font-bold" style={{ color }}>{value.toFixed(4)}</div>
                            </div>
                          ))}
                        </div>
                        <div className="text-xs italic" style={{ color: MUTED }}>{m.note}</div>
                        <div className="text-[10px]" style={{ color: DIM }}>
                          Model: <span className="font-semibold" style={{ color: MUTED }}>{m.name}</span>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Training info */}
                  <div className="rounded-2xl p-5 grid grid-cols-2 md:grid-cols-4 gap-4 text-center"
                    style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                    {[
                      { label: 'Training Rows', value: evalData.training_rows?.toLocaleString(), icon: 'fa-database', color: '#818cf8' },
                      { label: 'Features',      value: evalData.features,                        icon: 'fa-list',     color: '#22d3ee' },
                      { label: 'Congestion R²', value: `${(evalData.models.congestion.R2 * 100).toFixed(1)}%`, icon: 'fa-water', color: ORANGE },
                      { label: 'Queue MAE',     value: `±${evalData.models.queue.MAE.toFixed(2)} ships`, icon: 'fa-ship',  color: '#22c55e' },
                    ].map(({ label, value, icon, color }) => (
                      <div key={label}>
                        <i className={`fa-solid ${icon} text-xl mb-2`} style={{ color }} />
                        <div className="text-lg font-bold" style={{ color: TEXT }}>{value}</div>
                        <div className="text-xs" style={{ color: MUTED }}>{label}</div>
                      </div>
                    ))}
                  </div>

                  {/* Pipeline diagram */}
                  <div className="rounded-2xl p-5" style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                    <p className="text-xs mb-4 uppercase tracking-widest" style={{ color: MUTED }}>AI Pipeline</p>
                    <div className="text-sm italic text-center" style={{ color: MUTED }}>{evalData.pipeline}</div>
                    <div className="mt-4 flex items-center justify-center gap-3 text-xs flex-wrap">
                      {[
                        { n: '1', label: 'ETA',        sub: 'CatBoost MAE 5.76 min', color: '#818cf8' },
                        { n: '2', label: 'Berth',      sub: 'Optimizer Score 0.82',  color: '#22d3ee' },
                        { n: '3', label: 'Congestion', sub: `LightGBM R² ${evalData.models.congestion.R2.toFixed(4)}`, color: ORANGE },
                      ].map((st, i) => (
                        <div key={i} className="flex items-center gap-3">
                          {i > 0 && <i className="fa-solid fa-arrow-right" style={{ color: DIM }} />}
                          <div className="rounded-xl p-3 text-center min-w-[90px]"
                            style={{ background: `${st.color}12`, border: `1px solid ${st.color}30` }}>
                            <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold mx-auto mb-1"
                              style={{ background: st.color, color: 'white' }}>{st.n}</div>
                            <div className="font-semibold" style={{ color: TEXT }}>{st.label}</div>
                            <div className="text-[10px] mt-0.5" style={{ color: DIM }}>{st.sub}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Feature importance */}
                  {modelInfo?.feature_importance?.congestion?.length > 0 && (
                    <div className="rounded-2xl p-5" style={{ background: CARD_BG, border: `1px solid ${BORDER}` }}>
                      <h3 className="text-sm font-semibold mb-4 flex items-center gap-2" style={{ color: TEXT }}>
                        <i className="fa-solid fa-ranking-star" style={{ color: '#f59e0b' }} />
                        Global Feature Importance — Congestion Model
                      </h3>
                      <div className="space-y-2">
                        {modelInfo.feature_importance.congestion.slice(0, 10).map((f, i) => (
                          <div key={i} className="flex items-center gap-3 text-xs">
                            <div className="w-4 text-right" style={{ color: DIM }}>{i + 1}</div>
                            <div className="w-44 truncate" style={{ color: MUTED }}>{f.feature.replace(/_/g, ' ')}</div>
                            <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: TRACK }}>
                              <div className="h-full rounded-full"
                                style={{ width: `${f.importance_pct}%`, background: i < 3 ? ORANGE : i < 6 ? '#f59e0b' : '#22d3ee' }} />
                            </div>
                            <div className="w-12 text-right" style={{ color: MUTED }}>{f.importance_pct}%</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex items-center justify-center py-20">
                  <i className="fa-solid fa-spinner fa-spin text-2xl mr-3" style={{ color: MUTED }} />
                  <span className="text-sm" style={{ color: MUTED }}>Loading evaluation data…</span>
                </div>
              )}
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
