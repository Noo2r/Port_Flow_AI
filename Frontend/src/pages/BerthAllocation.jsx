import { useState } from 'react'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { CardContainer, Button, SectionHeader } from '../components/ui'
import { berths } from '../data/mockData'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'

const SLOT_COLORS = {
  empty:       'bg-gray-100 border-2 border-dashed border-gray-300',
  available:   'bg-status-green text-white cursor-pointer',
  occupied:    'bg-blue-600 text-white cursor-pointer hover:bg-blue-700',
  maintenance: 'bg-status-yellow text-white',
  conflict:    'bg-status-red text-white cursor-pointer',
}
const SLOT_LABELS = {
  empty: '', available: 'Available', maintenance: 'Maintenance', conflict: 'Conflict!',
}

const pieData = [
  { name: 'Occupied',    value: 65, color: '#3b82f6' },
  { name: 'Available',   value: 20, color: '#22c55e' },
  { name: 'Maintenance', value: 10, color: '#eab308' },
  { name: 'Reserved',    value:  5, color: '#6b7280' },
]

const TIME_HEADERS = ['Berth','00:00','04:00','08:00','12:00','16:00','20:00','24:00']

export default function BerthAllocation() {
  const [view, setView] = useState('Week')

  return (
    <MainLayout>
      <Navbar title="Berth Management Board" subtitle="AI-powered berth allocation and scheduling optimization">
        <Button variant="primary"><i className="fa-solid fa-plus" /> New Assignment</Button>
      </Navbar>

      {/* Control Panel */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option>All Terminals</option>
              <option>Terminal A</option>
              <option>Terminal B</option>
              <option>Terminal C</option>
            </select>
            <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm">
              <option>Next 7 Days</option>
              <option>Next 14 Days</option>
              <option>Next 30 Days</option>
            </select>
            <Button variant="secondary"><i className="fa-solid fa-filter" /> Filters</Button>
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
            {/* Utilization Donut */}
            <CardContainer className="p-6">
              <SectionHeader title="Berth Utilization" />
              <ResponsiveContainer width="100%" height={180}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={55} outerRadius={80} dataKey="value">
                    {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                  </Pie>
                  <Tooltip formatter={(v, n) => [`${v}%`, n]} />
                </PieChart>
              </ResponsiveContainer>
              <div className="mt-2 space-y-1.5">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Current</span>
                  <span className="font-medium">87%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Optimal</span>
                  <span className="font-medium text-status-green">75–85%</span>
                </div>
              </div>
            </CardContainer>

            {/* AI Insights */}
            <CardContainer className="p-6">
              <div className="flex items-center space-x-2 mb-4">
                <i className="fa-solid fa-robot text-blue-600" />
                <h3 className="text-lg font-semibold text-gray-900">AI Insights</h3>
              </div>
              <div className="space-y-3">
                {[
                  { bg:'bg-blue-50',   border:'border-blue-600',       title:'Optimization Opportunity', msg:'Move MV Baltic Wind to Berth C1 to reduce congestion', tag:'+12% efficiency gain', tagColor:'text-blue-600' },
                  { bg:'bg-yellow-50', border:'border-status-yellow',   title:'Weather Alert',            msg:'High winds predicted tomorrow 2–6 PM',                 tag:'Reschedule 3 arrivals', tagColor:'text-status-yellow' },
                  { bg:'bg-green-50',  border:'border-status-green',    title:'Capacity Available',       msg:'Berth B3 free for 6 hours starting 14:00',             tag:'Perfect for small vessel', tagColor:'text-status-green' },
                ].map(i => (
                  <div key={i.title} className={`p-3 ${i.bg} rounded-lg border-l-4 ${i.border}`}>
                    <p className="text-sm font-medium text-gray-900">{i.title}</p>
                    <p className="text-xs text-gray-600">{i.msg}</p>
                    <p className={`text-xs ${i.tagColor} mt-1`}>{i.tag}</p>
                  </div>
                ))}
              </div>
            </CardContainer>

            {/* Conflicts */}
            <CardContainer className="p-6">
              <SectionHeader title="Scheduling Conflicts" />
              <div className="space-y-3">
                {[
                  { icon:'fa-exclamation-triangle', color:'text-status-red', bg:'bg-red-50',    name:'Berth A2', desc:'Double booking detected', time:'Tomorrow 08:00' },
                  { icon:'fa-clock',                color:'text-status-yellow', bg:'bg-yellow-50', name:'Berth C1', desc:'Delayed departure',      time:'Today 16:30' },
                ].map(c => (
                  <div key={c.name} className={`flex items-center space-x-3 p-3 ${c.bg} rounded-lg`}>
                    <i className={`fa-solid ${c.icon} ${c.color}`} />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{c.name}</p>
                      <p className="text-xs text-gray-600">{c.desc}</p>
                      <p className={`text-xs ${c.color}`}>{c.time}</p>
                    </div>
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
                  {['Today','Week','Month'].map(v => (
                    <button key={v} onClick={() => setView(v)}
                      className={`px-3 py-1 text-sm rounded ${view === v ? 'bg-blue-600 text-white' : 'border border-gray-300 hover:bg-gray-50'}`}>
                      {v}
                    </button>
                  ))}
                </div>
              </div>

              {/* Time header */}
              <div className="grid grid-cols-8 gap-1 mb-2">
                {TIME_HEADERS.map(h => (
                  <div key={h} className="text-sm font-medium text-gray-600 p-2 text-center first:text-left">{h}</div>
                ))}
              </div>

              {/* Berth rows */}
              <div className="space-y-2">
                {berths.map(b => (
                  <div key={b.id} className="grid grid-cols-8 gap-1">
                    <div className="bg-gray-50 p-3 rounded-lg flex items-center">
                      <div>
                        <p className="font-medium text-gray-900 text-sm">{b.id}</p>
                        <p className="text-xs text-gray-600">{b.type}</p>
                      </div>
                    </div>
                    {b.slots.map((slot, i) => (
                      <div key={i} className={`p-2 rounded text-xs font-medium flex items-center justify-center min-h-[40px] ${SLOT_COLORS[slot]}`}>
                        {slot === 'occupied' ? b.vessel : SLOT_LABELS[slot]}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </CardContainer>
          </div>
        </div>
      </div>
    </MainLayout>
  )
}
