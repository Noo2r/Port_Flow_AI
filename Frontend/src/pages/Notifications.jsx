import { useState } from 'react'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { StatCard, CardContainer, Button, SectionHeader } from '../components/ui'
import { notifications, notifStats } from '../data/mockData'

const severityIcon  = { critical:'fa-exclamation-triangle', warning:'fa-exclamation-circle', info:'fa-info-circle' }
const severityColor = { critical:'text-status-red',  warning:'text-status-yellow', info:'text-blue-600' }
const severityBg    = { critical:'bg-red-50 border-status-red', warning:'bg-yellow-50 border-status-yellow', info:'bg-blue-50 border-blue-600' }

export default function Notifications() {
  const [items, setItems] = useState(notifications)
  const [severityFilter, setSeverityFilter] = useState('All Alerts')
  const [categoryFilter, setCategoryFilter] = useState('All Categories')

  const markAllRead = () => setItems(prev => prev.map(n => ({ ...n, read: true })))
  const markRead = id => setItems(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))

  const filtered = items.filter(n =>
    (severityFilter === 'All Alerts'    || n.severity === severityFilter.toLowerCase().split(' ')[0]) &&
    (categoryFilter === 'All Categories' || n.category === categoryFilter)
  )

  const critical = filtered.filter(n => n.severity === 'critical')
  const warnings  = filtered.filter(n => n.severity === 'warning')
  const infos     = filtered.filter(n => n.severity === 'info')

  return (
    <MainLayout>
      <Navbar title="Alerts & Notifications" subtitle="Real-time monitoring of port operations, system updates, and critical events">
        <Button variant="primary" onClick={markAllRead}>
          <i className="fa-solid fa-check-double" /> Mark All Read
        </Button>
      </Navbar>

      <div className="flex-1 p-6 overflow-auto">
        {/* Stats */}
        <div className="grid grid-cols-4 gap-6 mb-6">
          <StatCard label="Total Alerts"   value={notifStats.total}    sub="Last 24 hours"       subColor="text-gray-500"        icon="fa-bell"                 iconBg="bg-blue-100"   iconColor="text-blue-600" />
          <StatCard label="Critical"       value={notifStats.critical} sub="Requires action"     subColor="text-status-red"      icon="fa-exclamation-triangle" iconBg="bg-red-100"    iconColor="text-status-red" />
          <StatCard label="Warning"        value={notifStats.warning}  sub="Monitor closely"     subColor="text-status-yellow"   icon="fa-exclamation-circle"   iconBg="bg-yellow-100" iconColor="text-status-yellow" />
          <StatCard label="Info"           value={notifStats.info}     sub="General updates"     subColor="text-status-green"    icon="fa-info-circle"          iconBg="bg-green-100"  iconColor="text-status-green" />
        </div>

        {/* Filters */}
        <CardContainer className="p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700">Filter by:</label>
                <select className="border border-gray-300 rounded px-3 py-2 text-sm"
                  value={severityFilter} onChange={e => setSeverityFilter(e.target.value)}>
                  {['All Alerts','Critical Only','Warning Only','Info Only'].map(o => <option key={o}>{o}</option>)}
                </select>
              </div>
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700">Category:</label>
                <select className="border border-gray-300 rounded px-3 py-2 text-sm"
                  value={categoryFilter} onChange={e => setCategoryFilter(e.target.value)}>
                  {['All Categories','Vessel Ops','Berth Mgmt','Weather','Equipment','System','Cargo','Security'].map(o => <option key={o}>{o}</option>)}
                </select>
              </div>
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700">Time:</label>
                <select className="border border-gray-300 rounded px-3 py-2 text-sm">
                  {['Last 24 hours','Last 7 days','Last 30 days'].map(o => <option key={o}>{o}</option>)}
                </select>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Button variant="secondary"><i className="fa-solid fa-filter" /> More Filters</Button>
              <Button variant="secondary"><i className="fa-solid fa-download" /> Export</Button>
            </div>
          </div>
        </CardContainer>

        {/* Three columns */}
        <div className="grid grid-cols-3 gap-6">
          {[
            { label: 'Critical Alerts', items: critical, color: 'red' },
            { label: 'Warnings',        items: warnings, color: 'yellow' },
            { label: 'Information',     items: infos,    color: 'blue' },
          ].map(col => (
            <CardContainer key={col.label} className="p-6">
              <SectionHeader title={col.label}>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  col.color === 'red' ? 'bg-red-100 text-status-red' :
                  col.color === 'yellow' ? 'bg-yellow-100 text-status-yellow' :
                  'bg-blue-100 text-blue-700'
                }`}>{col.items.length} Active</span>
              </SectionHeader>

              <div className="space-y-3">
                {col.items.length === 0 && (
                  <p className="text-sm text-gray-400 text-center py-4">No alerts in this category.</p>
                )}
                {col.items.map(n => (
                  <div key={n.id}
                    className={`p-4 rounded-lg border-l-4 ${severityBg[n.severity]} ${n.read ? 'opacity-60' : ''} cursor-pointer`}
                    onClick={() => markRead(n.id)}>
                    <div className="flex items-start space-x-3">
                      <i className={`fa-solid ${severityIcon[n.severity]} ${severityColor[n.severity]} mt-0.5 flex-shrink-0`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="font-medium text-gray-900 text-sm">{n.title}</p>
                          {!n.read && <span className="w-2 h-2 bg-blue-600 rounded-full flex-shrink-0" />}
                        </div>
                        <p className="text-xs text-gray-600 mt-1">{n.message}</p>
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-xs text-gray-400">{n.time}</span>
                          <span className="text-xs text-gray-500 bg-white/70 px-2 py-0.5 rounded-full">{n.category}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContainer>
          ))}
        </div>
      </div>
    </MainLayout>
  )
}
