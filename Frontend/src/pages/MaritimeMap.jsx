import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'

// ── Vessel type config ────────────────────────────────────────────────────────
const VT = {
  container: { color: '#3b82f6', w: 15, h: 27, label: 'Container Ship',  flags: ['🇬🇷','🇩🇰','🇨🇭','🇨🇳','🇩🇪','🇰🇷','🇹🇼','🇯🇵'] },
  tanker:    { color: '#ef4444', w: 13, h: 25, label: 'Tanker',           flags: ['🇸🇦','🇦🇪','🇧🇭','🇰🇼','🇮🇷'] },
  bulk:      { color: '#22c55e', w: 13, h: 24, label: 'Bulk Carrier',     flags: ['🇧🇷','🇵🇦','🇬🇷','🇺🇦','🇧🇿'] },
  passenger: { color: '#f97316', w: 13, h: 23, label: 'Passenger Ship',   flags: ['🇮🇹','🇬🇷','🇹🇷','🇳🇴'] },
  tug:       { color: '#eab308', w: 9,  h: 16, label: 'Tugboat',          flags: ['🇪🇬','🇬🇷','🇹🇷'] },
  cargo:     { color: '#a78bfa', w: 11, h: 21, label: 'General Cargo',    flags: ['🇩🇪','🇸🇬','🇯🇵','🇦🇪','🇵🇦'] },
}

// ── Routes ────────────────────────────────────────────────────────────────────
const ROUTE_DEFS = [
  { id:0,  from:'Gibraltar',  to:'Piraeus',    pts:[[36.0,-5.5],[36.2,-1.0],[36.8,4.5],[37.5,9.0],[37.8,14.0],[38.0,18.5],[37.8,21.5],[37.94,23.64]] },
  { id:1,  from:'Piraeus',    to:'Alexandria', pts:[[37.94,23.64],[36.5,25.2],[34.8,26.8],[33.0,28.5],[31.19,29.87]] },
  { id:2,  from:'Istanbul',   to:'Port Said',  pts:[[41.01,28.96],[39.5,27.5],[37.8,28.5],[36.0,30.0],[33.5,32.0],[31.26,32.31]] },
  { id:3,  from:'Port Said',  to:'Sokhna',     pts:[[31.26,32.31],[31.0,32.32],[30.5,32.35],[30.0,32.44],[29.96,32.57],[29.7,32.35]] },
  { id:4,  from:'Sokhna',     to:'Jeddah',     pts:[[29.7,32.35],[27.5,33.8],[25.0,35.5],[23.0,37.2],[21.5,39.1]] },
  { id:5,  from:'Jeddah',     to:'Aden',       pts:[[21.5,39.1],[18.5,41.0],[15.5,42.5],[13.0,43.8],[12.79,44.99]] },
  { id:6,  from:'Barcelona',  to:'Damietta',   pts:[[41.5,2.2],[39.5,5.0],[38.5,9.5],[37.2,13.5],[36.0,17.5],[34.5,22.5],[32.5,27.0],[31.41,31.82]] },
  { id:7,  from:'Piraeus',    to:'Istanbul',   pts:[[37.94,23.64],[39.2,25.5],[40.2,27.0],[40.8,28.2],[41.01,28.96]] },
  { id:8,  from:'Alexandria', to:'Port Said',  pts:[[31.19,29.87],[31.3,30.4],[31.4,31.0],[31.41,31.82],[31.3,32.0],[31.26,32.31]] },
  { id:9,  from:'Aden',       to:'Muscat',     pts:[[12.79,44.99],[12.5,48.0],[13.5,52.0],[16.0,55.0],[20.0,57.5],[23.5,58.5]] },
  { id:10, from:'Istanbul',   to:'Izmir',      pts:[[41.01,28.96],[40.5,27.5],[39.8,26.8],[39.0,26.6],[38.42,27.16]] },
  { id:11, from:'Damietta',   to:'Piraeus',    pts:[[31.41,31.82],[33.0,29.8],[35.0,27.5],[36.5,25.5],[37.94,23.64]] },
]

// ── Ports ─────────────────────────────────────────────────────────────────────
const PORTS = [
  { name:'Port Said East CT',             lat:31.265, lng:32.320, type:'Container Terminal',   berths:6,  occ:75, cap:'4.5M TEU',  note:'Main Suez entry point' },
  { name:'Alexandria Container Terminal', lat:31.192, lng:29.872, type:'Container Terminal',   berths:4,  occ:62, cap:'1.8M TEU',  note:"Egypt's largest city port" },
  { name:'Damietta Port',                 lat:31.415, lng:31.820, type:'Bulk / General Cargo', berths:8,  occ:45, cap:'12M T/yr',  note:'Eastern Delta port' },
  { name:'Ain Sokhna Port',               lat:29.702, lng:32.352, type:'Multi-Purpose',        berths:5,  occ:80, cap:'8M T/yr',   note:'Red Sea gateway' },
  { name:'Jeddah Islamic Port',           lat:21.490, lng:39.087, type:'Container Terminal',   berths:10, occ:70, cap:'7.2M TEU',  note:'Saudi Arabia main hub' },
  { name:'Port of Piraeus',               lat:37.940, lng:23.644, type:'Container Terminal',   berths:12, occ:85, cap:'5.5M TEU',  note:"Med's busiest port" },
  { name:'Port of Aden',                  lat:12.785, lng:44.993, type:'Multi-Purpose',        berths:6,  occ:55, cap:'3M T/yr',   note:'Gulf of Aden hub' },
  { name:'Istanbul Haydarpasha',          lat:41.005, lng:28.975, type:'General Cargo',        berths:8,  occ:40, cap:'2M T/yr',   note:"Turkey's Bosphorus port" },
]

// ── Vessels ───────────────────────────────────────────────────────────────────
const VESSEL_DEFS = [
  { id:'VC001', nm:'EVER BRIGHT',        tp:'container', ri:0,  pr:0.05, sp:0.0000035, dst:'Piraeus',    imo:'9123456', kn:19.2, cargo:'Electronics/General' },
  { id:'VC002', nm:'MSC ZEUS',           tp:'container', ri:0,  pr:0.38, sp:0.0000030, dst:'Piraeus',    imo:'9234561', kn:17.8, cargo:'28000 TEU General' },
  { id:'VC003', nm:'MAERSK ALPHA',       tp:'container', ri:0,  pr:0.65, sp:0.0000038, dst:'Piraeus',    imo:'9345672', kn:20.4, cargo:'General Merchandise' },
  { id:'VC004', nm:'HAPAG FELIX',        tp:'container', ri:0,  pr:0.82, sp:0.0000032, dst:'Piraeus',    imo:'9456783', kn:18.1, cargo:'Electronics/Auto' },
  { id:'VC005', nm:'COSCO ATLAS',        tp:'container', ri:1,  pr:0.18, sp:0.0000042, dst:'Alexandria', imo:'9567894', kn:21.0, cargo:'15000 TEU General' },
  { id:'VC006', nm:'YANG MING OCEAN',    tp:'container', ri:1,  pr:0.60, sp:0.0000035, dst:'Alexandria', imo:'9678905', kn:18.5, cargo:'General/Reefer' },
  { id:'VT007', nm:'PERSIAN BAY',        tp:'tanker',    ri:1,  pr:0.40, sp:0.0000028, dst:'Alexandria', imo:'9789016', kn:14.2, cargo:'Crude Oil 280000 DWT' },
  { id:'VC008', nm:'ISTANBUL STAR',      tp:'container', ri:2,  pr:0.10, sp:0.0000033, dst:'Port Said',  imo:'9890127', kn:17.9, cargo:'Textiles/Automotive' },
  { id:'VB009', nm:'BLACK SEA PRIDE',    tp:'bulk',      ri:2,  pr:0.45, sp:0.0000025, dst:'Port Said',  imo:'9901238', kn:13.5, cargo:'Wheat 65000 T' },
  { id:'VG010', nm:'EASTERN GATE',       tp:'cargo',     ri:2,  pr:0.68, sp:0.0000029, dst:'Port Said',  imo:'9012349', kn:15.8, cargo:'Project Cargo' },
  { id:'VT011', nm:'MARMARA QUEEN',      tp:'tanker',    ri:2,  pr:0.86, sp:0.0000024, dst:'Port Said',  imo:'9123460', kn:12.4, cargo:'LPG 55000 T' },
  { id:'VU012', nm:'TUG ALFA',           tp:'tug',       ri:3,  pr:0.15, sp:0.0000065, dst:'Sokhna',     imo:'9234571', kn:11.2, cargo:'Canal Escort' },
  { id:'VG013', nm:'CANAL MASTER',       tp:'cargo',     ri:3,  pr:0.46, sp:0.0000042, dst:'Sokhna',     imo:'9345682', kn:10.5, cargo:'Steel Coils 22000 T' },
  { id:'VU014', nm:'TUG BETA',           tp:'tug',       ri:3,  pr:0.70, sp:0.0000060, dst:'Sokhna',     imo:'9456793', kn:10.8, cargo:'Canal Escort' },
  { id:'VC015', nm:'SUEZ GUARDIAN',      tp:'container', ri:3,  pr:0.88, sp:0.0000035, dst:'Sokhna',     imo:'9567804', kn:9.5,  cargo:'In-Canal Transit' },
  { id:'VT016', nm:'GULF PRIDE',         tp:'tanker',    ri:4,  pr:0.18, sp:0.0000030, dst:'Jeddah',     imo:'9678915', kn:15.4, cargo:'Crude Oil 320000 DWT' },
  { id:'VT017', nm:'ARABIAN SEA',        tp:'tanker',    ri:4,  pr:0.52, sp:0.0000028, dst:'Jeddah',     imo:'9789026', kn:14.8, cargo:'Refined Products' },
  { id:'VB018', nm:'ORE MASTER',         tp:'bulk',      ri:4,  pr:0.77, sp:0.0000026, dst:'Jeddah',     imo:'9890137', kn:13.2, cargo:'Iron Ore 85000 T' },
  { id:'VT041', nm:'NILE SPIRIT',        tp:'tanker',    ri:4,  pr:0.36, sp:0.0000028, dst:'Jeddah',     imo:'9123490', kn:14.0, cargo:'Petroleum Products' },
  { id:'VT019', nm:'ATLAS OIL',          tp:'tanker',    ri:5,  pr:0.22, sp:0.0000028, dst:'Aden',       imo:'9901248', kn:14.6, cargo:'Crude Oil 180000 DWT' },
  { id:'VP020', nm:'RED SEA DREAM',      tp:'passenger', ri:5,  pr:0.50, sp:0.0000048, dst:'Aden',       imo:'9012359', kn:22.5, cargo:'2800 Passengers' },
  { id:'VB021', nm:'COAL DUKE',          tp:'bulk',      ri:5,  pr:0.76, sp:0.0000025, dst:'Aden',       imo:'9123470', kn:12.8, cargo:'Coal 72000 T' },
  { id:'VC022', nm:'HMM GLORY',          tp:'container', ri:6,  pr:0.08, sp:0.0000032, dst:'Damietta',   imo:'9234581', kn:17.4, cargo:'23000 TEU General' },
  { id:'VP023', nm:'MED PEARL',          tp:'passenger', ri:6,  pr:0.28, sp:0.0000046, dst:'Damietta',   imo:'9345692', kn:21.5, cargo:'3200 Passengers' },
  { id:'VB024', nm:'GRAIN STAR',         tp:'bulk',      ri:6,  pr:0.52, sp:0.0000026, dst:'Damietta',   imo:'9456803', kn:13.5, cargo:'Grain 68000 T' },
  { id:'VG025', nm:'PIL AFRICA',         tp:'cargo',     ri:6,  pr:0.74, sp:0.0000028, dst:'Damietta',   imo:'9567814', kn:15.2, cargo:'Break Bulk 18000 T' },
  { id:'VC026', nm:'EVERGREEN UNITY',    tp:'container', ri:6,  pr:0.90, sp:0.0000030, dst:'Damietta',   imo:'9678925', kn:16.9, cargo:'18000 TEU General' },
  { id:'VP027', nm:'AEGEAN QUEEN',       tp:'passenger', ri:7,  pr:0.30, sp:0.0000052, dst:'Istanbul',   imo:'9789036', kn:24.0, cargo:'1800 Passengers' },
  { id:'VB028', nm:'IRON QUEEN',         tp:'bulk',      ri:7,  pr:0.68, sp:0.0000026, dst:'Istanbul',   imo:'9890147', kn:13.0, cargo:'Iron Ore 52000 T' },
  { id:'VU029', nm:'DELTA PILOT',        tp:'tug',       ri:8,  pr:0.14, sp:0.0000068, dst:'Port Said',  imo:'9901258', kn:12.0, cargo:'Coastal Tug' },
  { id:'VG030', nm:'NILE CARGO',         tp:'cargo',     ri:8,  pr:0.42, sp:0.0000038, dst:'Port Said',  imo:'9012369', kn:16.0, cargo:'Local Cargo 5000 T' },
  { id:'VU031', nm:'HARBOR MASTER',      tp:'tug',       ri:8,  pr:0.62, sp:0.0000065, dst:'Port Said',  imo:'9123480', kn:11.5, cargo:'Port Assistance' },
  { id:'VC032', nm:'EGYPT EXPRESS',      tp:'container', ri:8,  pr:0.83, sp:0.0000035, dst:'Port Said',  imo:'9234591', kn:18.2, cargo:'8000 TEU General' },
  { id:'VT033', nm:'SAHARA CRUDE',       tp:'tanker',    ri:9,  pr:0.20, sp:0.0000030, dst:'Muscat',     imo:'9345702', kn:15.8, cargo:'Crude Oil 260000 DWT' },
  { id:'VB034', nm:'STEPPE WIND',        tp:'bulk',      ri:9,  pr:0.52, sp:0.0000026, dst:'Muscat',     imo:'9456813', kn:13.4, cargo:'Grain 58000 T' },
  { id:'VG035', nm:'ARABIAN WIND',       tp:'cargo',     ri:9,  pr:0.80, sp:0.0000032, dst:'Muscat',     imo:'9567824', kn:15.5, cargo:'General Cargo 22000 T' },
  { id:'VP036', nm:'BOSPHORUS STAR',     tp:'passenger', ri:10, pr:0.35, sp:0.0000055, dst:'Izmir',      imo:'9678935', kn:25.0, cargo:'2400 Passengers' },
  { id:'VG037', nm:'ANKARA TRADER',      tp:'cargo',     ri:10, pr:0.72, sp:0.0000040, dst:'Izmir',      imo:'9789046', kn:16.2, cargo:'Steel Products 28000 T' },
  { id:'VC038', nm:'ONE HARMONY',        tp:'container', ri:11, pr:0.18, sp:0.0000033, dst:'Piraeus',    imo:'9890157', kn:17.7, cargo:'14000 TEU General' },
  { id:'VC039', nm:'MSC AQUILA',         tp:'container', ri:11, pr:0.48, sp:0.0000030, dst:'Piraeus',    imo:'9901268', kn:16.8, cargo:'16000 TEU General' },
  { id:'VB040', nm:'ORE EMPRESS',        tp:'bulk',      ri:11, pr:0.75, sp:0.0000025, dst:'Piraeus',    imo:'9012379', kn:12.6, cargo:'Iron Ore 78000 T' },
  { id:'VC042', nm:'HMM UNITY',          tp:'container', ri:1,  pr:0.85, sp:0.0000038, dst:'Alexandria', imo:'9234601', kn:19.5, cargo:'19000 TEU General' },
]

// ── Spline & bearing helpers ──────────────────────────────────────────────────
function crPoint(p0, p1, p2, p3, t) {
  const t2 = t * t, t3 = t2 * t
  return [
    .5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2 + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3),
    .5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2 + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3),
  ]
}
function buildSpline(pts, seg = 18) {
  const n = pts.length, out = []
  for (let i = 0; i < n - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(n - 1, i + 2)]
    for (let j = 0; j < seg; j++) out.push(crPoint(p0, p1, p2, p3, j / seg))
  }
  out.push(pts[n - 1])
  return out
}
function bearing(lat1, lng1, lat2, lng2) {
  const dL = (lng2 - lng1) * Math.PI / 180
  const φ1 = lat1 * Math.PI / 180, φ2 = lat2 * Math.PI / 180
  const y = Math.sin(dL) * Math.cos(φ2)
  const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(dL)
  return (Math.atan2(y, x) * 180 / Math.PI + 360) % 360
}
function shipSVG(color, w, h) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 28" width="${w}" height="${h}"><path d="M8 1 C11 4 12 8 12 13 L12 23 C12 25 10 26 8 26 C6 26 4 25 4 23 L4 13 C4 8 5 4 8 1 Z" fill="${color}" stroke="rgba(255,255,255,.35)" stroke-width=".6"/><rect x="5.5" y="14.5" width="5" height="5" rx=".5" fill="rgba(255,255,255,.18)"/><circle cx="8" cy="19" r=".7" fill="rgba(255,255,255,.35)"/></svg>`
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function MaritimeMap() {
  const mapDivRef   = useRef(null)
  const leafletRef  = useRef(null)
  const animRef     = useRef(null)
  const lastTsRef   = useRef(null)
  const vesselsRef  = useRef([])

  // Hover detail panel state (use refs for DOM updates to avoid 60fps re-renders)
  const detailRef   = useRef(null)
  const [hoveredVessel, setHoveredVessel] = useState(null)

  // UTC clock state
  const [utcTime, setUtcTime] = useState('')

  // Fleet stats
  const typeCounts = VESSEL_DEFS.reduce((acc, v) => { acc[v.tp] = (acc[v.tp] || 0) + 1; return acc }, {})

  useEffect(() => {
    const t = setInterval(() => {
      const n = new Date()
      setUtcTime(`${String(n.getUTCHours()).padStart(2,'0')}:${String(n.getUTCMinutes()).padStart(2,'0')}:${String(n.getUTCSeconds()).padStart(2,'0')} UTC`)
    }, 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    if (!mapDivRef.current || leafletRef.current) return

    // Inject Leaflet CSS overrides
    const styleEl = document.createElement('style')
    styleEl.textContent = `
      .lf-dark .leaflet-container { background: #06111f !important; }
      .lf-dark .leaflet-control-zoom a { background: rgba(6,17,31,.9) !important; color: #38bdf8 !important; border-color: rgba(56,189,248,.18) !important; }
      .lf-dark .leaflet-control-zoom a:hover { background: rgba(56,189,248,.12) !important; }
      .lf-dark .leaflet-control-attribution { background: rgba(6,17,31,.75) !important; color: #334155 !important; font-size:10px !important; }
      .lf-dark .leaflet-control-attribution a { color:#475569 !important; }
      .lf-dark .leaflet-div-icon { background:none !important; border:none !important; }
      .lf-dark .leaflet-popup-content-wrapper { background:rgba(6,17,31,.96) !important; border:1px solid rgba(251,191,36,.3) !important; border-radius:10px !important; box-shadow:0 8px 32px rgba(0,0,0,.65) !important; padding:0 !important; }
      .lf-dark .leaflet-popup-content { margin:0 !important; }
      .lf-dark .leaflet-popup-tip-container { display:none; }
      .lf-dark .leaflet-popup-close-button { color:#64748b !important; font-size:17px !important; top:8px !important; right:10px !important; }
      .lf-dark .leaflet-popup-close-button:hover { color:#fbbf24 !important; }
      .lf-dark .v-tt { background:rgba(6,17,31,.95) !important; border:1px solid rgba(56,189,248,.28) !important; border-radius:8px !important; color:#e2e8f0 !important; font-family:Inter,sans-serif !important; font-size:11px !important; padding:0 !important; box-shadow:0 6px 24px rgba(0,0,0,.5) !important; }
      .lf-dark .v-tt::before { border-right-color:rgba(56,189,248,.28) !important; }
      .lf-dark .port-lbl { background:none !important; border:none !important; box-shadow:none !important; padding:0 !important; }
      @keyframes mm-pring { 0%{transform:scale(.4);opacity:.75} 100%{transform:scale(3.2);opacity:0} }
    `
    document.head.appendChild(styleEl)

    // Init map
    const map = L.map(mapDivRef.current, { center: [30, 33], zoom: 5, minZoom: 3, maxZoom: 14 })
    map.getContainer().classList.add('lf-dark')
    leafletRef.current = map

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/">OSM</a> © <a href="https://carto.com/">CARTO</a>',
      subdomains: 'abcd', maxZoom: 20,
    }).addTo(map)

    map.zoomControl.setPosition('bottomright')

    // Build splines & route lines
    const routeSplines = {}
    ROUTE_DEFS.forEach(r => {
      const spl = buildSpline(r.pts, 20)
      routeSplines[r.id] = spl
      L.polyline(spl, { color: 'rgba(56,189,248,.18)', weight: 1.2, dashArray: '4 8', lineCap: 'round' }).addTo(map)
    })

    // Port markers
    PORTS.forEach(port => {
      const occ = port.occ
      const c = occ >= 80 ? '#ef4444' : occ >= 60 ? '#f59e0b' : '#22c55e'
      const d1 = (Math.random() * 1.5).toFixed(2)
      const d2 = (parseFloat(d1) + 0.5).toFixed(2)
      const icon = L.divIcon({
        html: `<div style="position:relative;width:14px;height:14px">
          <div style="position:absolute;inset:0;border-radius:50%;background:${c};border:1.5px solid rgba(255,255,255,.6);box-shadow:0 0 10px ${c}"></div>
          <div style="position:absolute;inset:-5px;border-radius:50%;border:1.5px solid ${c};animation:mm-pring 2.2s ${d1}s ease-out infinite"></div>
          <div style="position:absolute;inset:-12px;border-radius:50%;border:1px solid ${c};animation:mm-pring 2.2s ${d2}s ease-out infinite"></div>
        </div>`,
        className: '', iconSize: [14, 14], iconAnchor: [7, 7],
      })
      const marker = L.marker([port.lat, port.lng], { icon }).addTo(map)
      marker.bindPopup(`
        <div style="padding:13px 15px;min-width:195px;font-family:Inter,sans-serif">
          <div style="font-size:13px;font-weight:700;color:#fbbf24;margin-bottom:2px">${port.name}</div>
          <div style="font-size:9.5px;color:#64748b;letter-spacing:1px;text-transform:uppercase;margin-bottom:11px">${port.type}</div>
          <div style="display:flex;justify-content:space-between;font-size:11px;padding:2.5px 0;color:#94a3b8"><span>Berths</span><span style="color:#e2e8f0;font-weight:600">${port.berths}</span></div>
          <div style="display:flex;justify-content:space-between;font-size:11px;padding:2.5px 0;color:#94a3b8"><span>Annual Capacity</span><span style="color:#e2e8f0;font-weight:600">${port.cap}</span></div>
          <div style="display:flex;justify-content:space-between;font-size:11px;padding:2.5px 0;color:#94a3b8"><span>Occupancy</span><span style="color:${c};font-weight:700">${port.occ}%</span></div>
          <div style="margin-top:9px;background:rgba(255,255,255,.06);border-radius:3px;height:3px;overflow:hidden">
            <div style="width:${port.occ}%;height:100%;background:${c};border-radius:3px"></div>
          </div>
          <div style="margin-top:9px;font-size:10px;color:#475569;font-style:italic">${port.note}</div>
        </div>`, { maxWidth: 240 })

      L.tooltip({ permanent: true, direction: 'right', offset: [10, 0], className: 'port-lbl', opacity: 1 })
        .setContent(`<span style="font-family:Inter,sans-serif;font-size:10px;color:#fbbf24;font-weight:600;background:rgba(6,17,31,.8);padding:2px 5px;border-radius:3px;white-space:nowrap">${port.name}</span>`)
        .setLatLng([port.lat, port.lng])
        .addTo(map)
    })

    // Vessel markers
    const vessels = []
    VESSEL_DEFS.forEach(def => {
      const spec = VT[def.tp]
      const spl  = routeSplines[def.ri]
      if (!spl) return

      const idx   = Math.floor(def.pr * (spl.length - 1))
      const pos   = spl[idx] || spl[0]
      const nextP = spl[Math.min(idx + 1, spl.length - 1)]
      const hdg   = bearing(pos[0], pos[1], nextP[0], nextP[1])
      const flag  = spec.flags[Math.floor(Math.random() * spec.flags.length)]
      const etaH  = 2 + Math.floor(Math.random() * 22)
      const etaM  = Math.floor(Math.random() * 60)
      const eta   = `${String(etaH).padStart(2,'0')}:${String(etaM).padStart(2,'0')} UTC`

      const iconHTML = `<div style="width:${spec.w}px;height:${spec.h}px;filter:drop-shadow(0 0 5px ${spec.color}40)">
        <div class="vi-inner" style="width:100%;height:100%;transform:rotate(${hdg}deg);transform-origin:50% 50%">
          ${shipSVG(spec.color, spec.w, spec.h)}
        </div>
      </div>`

      const icon = L.divIcon({ html: iconHTML, className: '', iconSize: [spec.w, spec.h], iconAnchor: [spec.w / 2, spec.h / 2] })
      const lMarker = L.marker([pos[0], pos[1]], { icon, zIndexOffset: 100 }).addTo(map)

      lMarker.bindTooltip(
        `<div style="padding:9px 13px">
          <div style="font-weight:700;font-size:12.5px;color:#7dd3fc;margin-bottom:5px">${def.nm}</div>
          <div style="display:flex;justify-content:space-between;gap:14px;font-size:11px;color:#64748b;padding:1.5px 0"><span>Type</span><span style="color:#cbd5e1;font-weight:500">${spec.label}</span></div>
          <div style="display:flex;justify-content:space-between;gap:14px;font-size:11px;color:#64748b;padding:1.5px 0"><span>Speed</span><span style="color:#cbd5e1;font-weight:500">${def.kn} kn</span></div>
          <div style="display:flex;justify-content:space-between;gap:14px;font-size:11px;color:#64748b;padding:1.5px 0"><span>Destination</span><span style="color:#cbd5e1;font-weight:500">${def.dst}</span></div>
        </div>`,
        { sticky: false, direction: 'right', opacity: 1, className: 'v-tt', offset: [8, 0] }
      )

      const vObj = { def: { ...def, flag, eta }, lMarker, spec, spl, progress: def.pr, speed: def.sp, heading: hdg, innerEl: null }

      lMarker.on('mouseover', () => setHoveredVessel({ ...vObj.def, heading: vObj.heading }))
      lMarker.on('mouseout',  () => setHoveredVessel(null))

      vessels.push(vObj)
    })

    // Cache inner elements for direct DOM rotation
    requestAnimationFrame(() => requestAnimationFrame(() => {
      vessels.forEach(v => {
        const el = v.lMarker.getElement()
        if (el) v.innerEl = el.querySelector('.vi-inner')
      })
    }))

    vesselsRef.current = vessels

    // Animation loop
    function animate(ts) {
      if (lastTsRef.current === null) lastTsRef.current = ts
      const dt = Math.min(ts - lastTsRef.current, 100)
      lastTsRef.current = ts

      vessels.forEach(v => {
        v.progress += v.speed * dt
        if (v.progress >= 1) v.progress %= 1

        const rawIdx = v.progress * (v.spl.length - 1)
        const i0 = Math.floor(rawIdx)
        const i1 = Math.min(i0 + 1, v.spl.length - 1)
        const f  = rawIdx - i0
        const p0 = v.spl[i0], p1 = v.spl[i1]
        const lat = p0[0] + (p1[0] - p0[0]) * f
        const lng = p0[1] + (p1[1] - p0[1]) * f

        v.lMarker.setLatLng([lat, lng])

        if (i1 !== i0) {
          const target = bearing(p0[0], p0[1], p1[0], p1[1])
          let diff = target - v.heading
          if (diff > 180) diff -= 360
          if (diff < -180) diff += 360
          v.heading += diff * 0.1
        }
        if (v.innerEl) v.innerEl.style.transform = `rotate(${v.heading}deg)`
      })

      animRef.current = requestAnimationFrame(animate)
    }
    animRef.current = requestAnimationFrame(animate)

    return () => {
      cancelAnimationFrame(animRef.current)
      lastTsRef.current = null
      map.remove()
      leafletRef.current = null
      if (styleEl.parentNode) styleEl.parentNode.removeChild(styleEl)
    }
  }, [])

  // Update hovered vessel heading every frame would cause too many re-renders;
  // instead we only update heading when a new vessel is hovered.

  const panelBg  = 'rgba(6,17,31,.9)'
  const panelBdr = '1px solid rgba(56,189,248,.13)'
  const panelStyle = { background: panelBg, backdropFilter: 'blur(16px)', border: panelBdr, borderRadius: 12, padding: '15px 17px', fontFamily: 'Inter, sans-serif' }
  const ptStyle  = { fontFamily: 'monospace', fontSize: 9.5, letterSpacing: '2.5px', color: '#38bdf8', textTransform: 'uppercase', marginBottom: 12, paddingBottom: 8, borderBottom: '1px solid rgba(56,189,248,.1)', display: 'flex', alignItems: 'center', gap: 6 }

  return (
    <MainLayout>
      <Navbar title="Maritime Live Map" subtitle="Real-time vessel tracking · 42 vessels across 12 shipping lanes" />

      {/* Map fills remaining space */}
      <div className="flex-1 relative overflow-hidden" style={{ background: '#06111f' }}>

        {/* Leaflet map target */}
        <div ref={mapDivRef} style={{ position: 'absolute', inset: 0 }} />

        {/* Vignette */}
        <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', background: 'radial-gradient(ellipse at center,transparent 55%,rgba(6,17,31,.5) 100%)', zIndex: 5 }} />

        {/* UTC Clock */}
        <div style={{ position: 'absolute', top: 14, left: 14, zIndex: 10, fontFamily: 'monospace', fontSize: 13, color: '#38bdf8', letterSpacing: '2px', background: 'rgba(6,17,31,.85)', backdropFilter: 'blur(8px)', border: '1px solid rgba(56,189,248,.12)', borderRadius: 7, padding: '5px 12px', pointerEvents: 'none' }}>
          {utcTime || '—'}
        </div>

        {/* ── Fleet Overview (bottom-left) ── */}
        <div style={{ ...panelStyle, position: 'absolute', bottom: 22, left: 18, zIndex: 10, minWidth: 205 }}>
          <div style={ptStyle}>
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
            Fleet Overview
          </div>
          {[
            ['Total Vessels',    VESSEL_DEFS.length, '#38bdf8'],
            ['Container Ships',  typeCounts.container || 0, null],
            ['Tankers',          typeCounts.tanker || 0, null],
            ['Bulk Carriers',    typeCounts.bulk || 0, null],
            ['Passenger Ships',  typeCounts.passenger || 0, null],
            ['Tugs / Cargo',     (typeCounts.tug || 0) + (typeCounts.cargo || 0), null],
          ].map(([lbl, val, col]) => (
            <div key={lbl} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4.5px 0', borderBottom: '1px solid rgba(255,255,255,.04)', fontSize: 11.5 }}>
              <span style={{ color: '#64748b' }}>{lbl}</span>
              <span style={{ fontWeight: 700, color: col || '#e2e8f0', fontSize: 12.5 }}>{val}</span>
            </div>
          ))}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4.5px 0', fontSize: 11.5 }}>
            <span style={{ color: '#64748b' }}>Avg Speed</span>
            <span style={{ fontWeight: 700, color: '#e2e8f0', fontSize: 12.5 }}>16.4 <span style={{ fontSize: 10, color: '#64748b' }}>kn</span></span>
          </div>
        </div>

        {/* ── Legend (bottom-right) ── */}
        <div style={{ ...panelStyle, position: 'absolute', bottom: 22, right: 18, zIndex: 10, minWidth: 158 }}>
          <div style={ptStyle}>
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            Vessel Types
          </div>
          {Object.entries(VT).map(([key, spec]) => (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 9, padding: '3.5px 0', fontSize: 11.5, color: '#cbd5e1' }}>
              <div style={{ width: 18, height: 18, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}
                dangerouslySetInnerHTML={{ __html: shipSVG(spec.color, spec.w, spec.h) }} />
              {spec.label}
            </div>
          ))}
          <div style={{ marginTop: 10, paddingTop: 9, borderTop: '1px solid rgba(56,189,248,.1)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '3.5px 0', fontSize: 11.5, color: '#cbd5e1' }}>
              <span style={{ color: 'rgba(251,191,36,.8)', fontSize: 14 }}>◉</span> Port / Terminal
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, padding: '3.5px 0', fontSize: 11.5, color: '#cbd5e1' }}>
              <span style={{ display: 'inline-block', width: 20, height: 1, borderTop: '2px dashed rgba(56,189,248,.3)', verticalAlign: 'middle' }} /> Shipping Lane
            </div>
          </div>
        </div>

        {/* ── Vessel Detail Panel (top-right, on hover) ── */}
        {hoveredVessel && (
          <div style={{ ...panelStyle, position: 'absolute', top: 14, right: 18, zIndex: 10, minWidth: 248 }}>
            <div style={ptStyle}>
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M22 17H2a3 3 0 003-3V9a7 7 0 0114 0v5a3 3 0 003 3z"/><path d="M9 17v1a3 3 0 006 0v-1"/></svg>
              Vessel Detail
            </div>
            <div style={{ width: '100%', height: 2, borderRadius: 1, background: `linear-gradient(90deg,${VT[hoveredVessel.tp]?.color},transparent)`, marginBottom: 12 }} />
            <div style={{ fontSize: 15, fontWeight: 700, color: '#e2e8f0', marginBottom: 2 }}>{hoveredVessel.nm}</div>
            <div style={{ fontSize: 10, color: '#64748b', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 11 }}>{VT[hoveredVessel.tp]?.label}</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 7 }}>
              {[
                ['Speed',       `${hoveredVessel.kn} kn`],
                ['Heading',     `${Math.round(hoveredVessel.heading || 0)}°`],
                ['Destination', hoveredVessel.dst],
                ['ETA',         hoveredVessel.eta],
                ['IMO',         hoveredVessel.imo],
                ['Flag',        hoveredVessel.flag],
              ].map(([lb, vl]) => (
                <div key={lb} style={{ padding: '8px 10px', background: 'rgba(56,189,248,.04)', border: '1px solid rgba(56,189,248,.08)', borderRadius: 6 }}>
                  <div style={{ color: '#64748b', fontSize: 9.5, textTransform: 'uppercase', letterSpacing: .5, marginBottom: 3 }}>{lb}</div>
                  <div style={{ color: '#e2e8f0', fontSize: 12.5, fontWeight: 600 }}>{vl}</div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>
    </MainLayout>
  )
}
