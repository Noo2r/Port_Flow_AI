import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { StatCard, CardContainer, SectionHeader, Badge } from '../components/ui'
import { kpis, berthStatusCards, vesselTrafficData, recentActivity } from '../data/mockData'
import { LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer, CartesianGrid } from 'recharts'

const berthBadge = { green: 'solid_green', yellow: 'solid_yellow', gray: 'solid_gray' }

export default function Dashboard() {
  return (
    <MainLayout>
      <Navbar title="Port Operations Dashboard" subtitle="Real-time overview of port activities and performance" />
      <div className="flex-1 p-6 overflow-auto">

        {/* KPIs */}
        <div className="grid grid-cols-4 gap-6 mb-6">
          {kpis.map(k => <StatCard key={k.label} {...k} />)}
        </div>

        {/* Charts row */}
        <div className="grid grid-cols-3 gap-6 mb-6">
          {/* Vessel Traffic Chart */}
          <CardContainer className="col-span-2 p-6">
            <SectionHeader title="Vessel Traffic Trend">
              <select className="text-sm border border-gray-300 rounded px-3 py-1">
                <option>Last 7 days</option>
                <option>Last 30 days</option>
                <option>Last 90 days</option>
              </select>
            </SectionHeader>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={vesselTrafficData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
                <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="arrivals"   stroke="#3b82f6" strokeWidth={3} dot={false} name="Arrivals" />
                <Line type="monotone" dataKey="departures" stroke="#22c55e" strokeWidth={3} dot={false} name="Departures" />
              </LineChart>
            </ResponsiveContainer>
          </CardContainer>

          {/* Berth Status */}
          <CardContainer className="p-6">
            <SectionHeader title="Berth Status" />
            <div className="space-y-3">
              {berthStatusCards.map(b => (
                <div key={b.name} className={`flex items-center justify-between p-3 rounded-lg ${b.color === 'green' ? 'bg-green-50' : b.color === 'yellow' ? 'bg-yellow-50' : 'bg-gray-50'}`}>
                  <div>
                    <p className="font-medium text-gray-900">{b.name}</p>
                    <p className="text-sm text-gray-600">{b.vessel}</p>
                  </div>
                  <Badge variant={berthBadge[b.color]}>{b.status}</Badge>
                </div>
              ))}
            </div>
          </CardContainer>
        </div>

        {/* Alerts & Recent Activity */}
        <div className="grid grid-cols-2 gap-6">
          {/* Critical Alerts */}
          <CardContainer className="p-6">
            <SectionHeader title="Critical Alerts">
              <Badge variant="red">3 Active</Badge>
            </SectionHeader>
            <div className="space-y-3">
              {[
                { color: 'red',    icon: 'fa-exclamation-triangle', title: 'Weather Alert',      msg: 'High winds expected (35+ knots) – Consider vessel movement restrictions', time: '2 minutes ago' },
                { color: 'yellow', icon: 'fa-clock',                title: 'Delayed Arrival',    msg: 'MV Container Express – 3 hours behind schedule',                        time: '15 minutes ago' },
                { color: 'red',    icon: 'fa-tools',                title: 'Equipment Failure',  msg: 'Crane #3 offline – Maintenance required',                               time: '1 hour ago' },
              ].map(a => (
                <div key={a.title} className={`flex items-start space-x-3 p-3 rounded-lg border-l-4 ${a.color === 'red' ? 'bg-red-50 border-status-red' : 'bg-yellow-50 border-status-yellow'}`}>
                  <i className={`fa-solid ${a.icon} ${a.color === 'red' ? 'text-status-red' : 'text-status-yellow'} mt-1`} />
                  <div>
                    <p className="font-medium text-gray-900">{a.title}</p>
                    <p className="text-sm text-gray-600">{a.msg}</p>
                    <p className="text-xs text-gray-500 mt-1">{a.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContainer>

          {/* Recent Activity */}
          <CardContainer className="p-6">
            <SectionHeader title="Recent Activity" />
            <div className="space-y-3">
              {recentActivity.map(a => (
                <div key={a.title} className="flex items-center space-x-3 p-3 hover:bg-gray-50 rounded-lg">
                  <div className={`w-8 h-8 ${a.iconBg} rounded-full flex items-center justify-center flex-shrink-0`}>
                    <i className={`fa-solid ${a.icon} ${a.iconColor} text-sm`} />
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-gray-900">{a.title}</p>
                    <p className="text-sm text-gray-600">{a.desc}</p>
                    <p className="text-xs text-gray-500">{a.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContainer>
        </div>
      </div>
    </MainLayout>
  )
}
