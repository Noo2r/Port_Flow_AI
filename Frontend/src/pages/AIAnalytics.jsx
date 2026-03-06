import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { CardContainer, SectionHeader, Badge } from '../components/ui'
import { vesselTrafficData, cargoThroughputData, delayPredictionData, efficiencyData } from '../data/mockData'
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts'

const aiInsights = [
  { icon:'fa-robot',        color:'text-blue-600',   bg:'bg-blue-50',   border:'border-blue-600',   title:'Berth Optimization',  desc:'Reallocating MV Baltic Wind to Berth C1 will improve throughput by 12% and reduce congestion at Terminal A.' },
  { icon:'fa-cloud-rain',   color:'text-yellow-600', bg:'bg-yellow-50', border:'border-yellow-500', title:'Weather Risk',         desc:'Storm system arriving Friday 18:00. Recommend pre-positioning 4 vessels and restricting outer berths.' },
  { icon:'fa-chart-line',   color:'text-green-600',  bg:'bg-green-50',  border:'border-green-500',  title:'Peak Demand Forecast', desc:'Cargo volume expected to exceed capacity by ~8% next Tuesday. Consider activating surge staffing protocol.' },
  { icon:'fa-tools',        color:'text-red-600',    bg:'bg-red-50',    border:'border-red-500',    title:'Maintenance Alert',    desc:'Predictive analysis indicates Crane #2 may require maintenance within 72 hrs. Schedule before peak period.' },
]

export default function AIAnalytics() {
  return (
    <MainLayout>
      <Navbar title="AI-Powered Analytics" subtitle="Predictive insights and operational intelligence for smart decision-making" />
      <div className="flex-1 p-6 overflow-auto">

        {/* Top KPIs */}
        <div className="grid grid-cols-4 gap-6 mb-6">
          {[
            { label:'AI Predictions',   value:'94.2%', sub:'Accuracy rate',       icon:'fa-brain',       bg:'bg-purple-100', color:'text-purple-600' },
            { label:'Efficiency Score', value:'88%',   sub:'+5% vs last week',    icon:'fa-bolt',        bg:'bg-blue-100',   color:'text-blue-600' },
            { label:'Delays Prevented', value:'12',    sub:'This week by AI',     icon:'fa-shield-alt',  bg:'bg-green-100',  color:'text-status-green' },
            { label:'Cost Savings',     value:'$48K',  sub:'Estimated this month',icon:'fa-dollar-sign', bg:'bg-yellow-100', color:'text-yellow-600' },
          ].map(k => (
            <CardContainer key={k.label} className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">{k.label}</p>
                  <p className="text-2xl font-bold text-gray-900">{k.value}</p>
                  <p className="text-xs text-gray-500">{k.sub}</p>
                </div>
                <div className={`w-12 h-12 ${k.bg} rounded-lg flex items-center justify-center`}>
                  <i className={`fa-solid ${k.icon} ${k.color} text-lg`} />
                </div>
              </div>
            </CardContainer>
          ))}
        </div>

        {/* Charts row 1 */}
        <div className="grid grid-cols-2 gap-6 mb-6">
          {/* Vessel Traffic */}
          <CardContainer className="p-6">
            <SectionHeader title="Port Traffic Trend">
              <select className="text-sm border border-gray-300 rounded px-3 py-1">
                <option>Last 7 days</option><option>Last 30 days</option>
              </select>
            </SectionHeader>
            <ResponsiveContainer width="100%" height={240}>
              <LineChart data={vesselTrafficData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="arrivals"   stroke="#3b82f6" strokeWidth={2} name="Arrivals" />
                <Line type="monotone" dataKey="departures" stroke="#22c55e" strokeWidth={2} name="Departures" />
              </LineChart>
            </ResponsiveContainer>
          </CardContainer>

          {/* Cargo Throughput */}
          <CardContainer className="p-6">
            <SectionHeader title="Cargo Throughput (TEUs)" />
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={cargoThroughputData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="teus" fill="#3b82f6" radius={[4,4,0,0]} name="TEUs" />
              </BarChart>
            </ResponsiveContainer>
          </CardContainer>
        </div>

        {/* Charts row 2 */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          {/* Delay Causes Pie */}
          <CardContainer className="p-6">
            <SectionHeader title="Delay Prediction by Cause" />
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={delayPredictionData} cx="50%" cy="50%" outerRadius={75} dataKey="value" label={({ name, value }) => `${name} ${value}%`} labelLine={false}>
                  {delayPredictionData.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
                <Tooltip formatter={(v, n) => [`${v}%`, n]} />
              </PieChart>
            </ResponsiveContainer>
          </CardContainer>

          {/* Operational Efficiency */}
          <CardContainer className="col-span-2 p-6">
            <SectionHeader title="Operational Efficiency (24h)">
              <Badge variant="green">Live</Badge>
            </SectionHeader>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={efficiencyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="hour" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} domain={[60, 100]} />
                <Tooltip formatter={v => [`${v}%`, 'Efficiency']} />
                <Area type="monotone" dataKey="efficiency" stroke="#8b5cf6" fill="#ede9fe" strokeWidth={2} name="Efficiency %" />
              </AreaChart>
            </ResponsiveContainer>
          </CardContainer>
        </div>

        {/* AI Insights */}
        <CardContainer className="p-6">
          <div className="flex items-center space-x-2 mb-4">
            <i className="fa-solid fa-robot text-blue-600" />
            <h3 className="text-lg font-semibold text-gray-900">AI Recommendations</h3>
            <Badge variant="blue">4 New</Badge>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {aiInsights.map(i => (
              <div key={i.title} className={`p-4 ${i.bg} rounded-lg border-l-4 ${i.border}`}>
                <div className="flex items-start space-x-3">
                  <i className={`fa-solid ${i.icon} ${i.color} mt-0.5`} />
                  <div>
                    <p className="font-medium text-gray-900 text-sm">{i.title}</p>
                    <p className="text-xs text-gray-600 mt-1">{i.desc}</p>
                  </div>
                </div>
                <div className="mt-3 flex space-x-2">
                  <button className="text-xs text-blue-600 font-medium hover:underline">Apply</button>
                  <button className="text-xs text-gray-500 hover:underline">Dismiss</button>
                </div>
              </div>
            ))}
          </div>
        </CardContainer>
      </div>
    </MainLayout>
  )
}
