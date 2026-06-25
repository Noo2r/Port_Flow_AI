import { useState } from 'react'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { StatCard, CardContainer, Button, SectionHeader } from '../components/ui'
import { useNotifications } from '../hooks/queries'

const channelIcon  = { email: 'fa-envelope', in_app: 'fa-bell', webhook: 'fa-globe' }
const statusIcon   = { sent: 'fa-check-circle', failed: 'fa-times-circle', pending: 'fa-clock' }
const statusColor  = { sent: 'text-status-green', failed: 'text-status-red', pending: 'text-status-yellow' }
const statusBg     = { sent: 'bg-green-50 border-status-green', failed: 'bg-red-50 border-status-red', pending: 'bg-yellow-50 border-status-yellow' }

export default function Notifications() {
  const [channelFilter, setChannelFilter] = useState('All')
  const [statusFilter,  setStatusFilter]  = useState('All')
  const [read, setRead] = useState(new Set())

  const { data, isLoading: loading, error } = useNotifications()
  const items = data || []

  const filtered = items.filter(n =>
    (channelFilter === 'All' || n.channel === channelFilter) &&
    (statusFilter  === 'All' || n.status  === statusFilter)
  )

  const sent    = filtered.filter(n => n.status === 'sent')
  const failed  = filtered.filter(n => n.status === 'failed')
  const pending = filtered.filter(n => n.status === 'pending')

  const markRead = id => setRead(s => new Set([...s, id]))
  const markAllRead = () => setRead(new Set(items.map(n => n.id)))

  function formatTime(ts) {
    if (!ts) return '—'
    try { return new Date(ts).toLocaleString() } catch { return ts }
  }

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
          <StatCard label="Total"   value={loading ? '…' : items.length}   sub="All notifications"    subColor="text-gray-500"      icon="fa-bell"                 iconBg="bg-blue-100"   iconColor="text-blue-600" />
          <StatCard label="Sent"    value={loading ? '…' : items.filter(n=>n.status==='sent').length}    sub="Successfully delivered" subColor="text-status-green"  icon="fa-check-circle"         iconBg="bg-green-100"  iconColor="text-status-green" />
          <StatCard label="Failed"  value={loading ? '…' : items.filter(n=>n.status==='failed').length}  sub="Delivery errors"        subColor="text-status-red"    icon="fa-times-circle"         iconBg="bg-red-100"    iconColor="text-status-red" />
          <StatCard label="Pending" value={loading ? '…' : items.filter(n=>n.status==='pending').length} sub="Awaiting delivery"      subColor="text-status-yellow" icon="fa-clock"                iconBg="bg-yellow-100" iconColor="text-status-yellow" />
        </div>

        {/* Filters */}
        <CardContainer className="p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700">Channel:</label>
                <select className="border border-gray-300 rounded px-3 py-2 text-sm"
                  value={channelFilter} onChange={e => setChannelFilter(e.target.value)}>
                  {['All','email','in_app','webhook'].map(o => <option key={o}>{o}</option>)}
                </select>
              </div>
              <div className="flex items-center space-x-2">
                <label className="text-sm font-medium text-gray-700">Status:</label>
                <select className="border border-gray-300 rounded px-3 py-2 text-sm"
                  value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
                  {['All','sent','failed','pending'].map(o => <option key={o}>{o}</option>)}
                </select>
              </div>
            </div>
            <Button variant="secondary"><i className="fa-solid fa-download" /> Export</Button>
          </div>
        </CardContainer>

        {loading && (
          <div className="py-12 text-center text-gray-500">
            <i className="fa-solid fa-spinner fa-spin mr-2" />Loading notifications…
          </div>
        )}
        {error && (
          <div className="py-12 text-center text-red-600">
            <i className="fa-solid fa-circle-exclamation mr-2" />Failed to load notifications: {error.message}
          </div>
        )}

        {!loading && !error && (
          <div className="grid grid-cols-3 gap-6">
            {[
              { label: 'Sent',    items: sent,    color: 'green' },
              { label: 'Pending', items: pending, color: 'yellow' },
              { label: 'Failed',  items: failed,  color: 'red' },
            ].map(col => (
              <CardContainer key={col.label} className="p-6">
                <SectionHeader title={col.label}>
                  <span className={`px-2 py-1 text-xs rounded-full ${
                    col.color === 'red'    ? 'bg-red-100 text-status-red' :
                    col.color === 'yellow' ? 'bg-yellow-100 text-status-yellow' :
                    'bg-green-100 text-status-green'
                  }`}>{col.items.length}</span>
                </SectionHeader>

                <div className="space-y-3">
                  {col.items.length === 0 && (
                    <p className="text-sm text-gray-400 text-center py-4">No notifications.</p>
                  )}
                  {col.items.map(n => (
                    <div key={n.id}
                      className={`p-4 rounded-lg border-l-4 ${statusBg[n.status] || 'bg-gray-50 border-gray-300'} ${read.has(n.id) ? 'opacity-60' : ''} cursor-pointer`}
                      onClick={() => markRead(n.id)}>
                      <div className="flex items-start space-x-3">
                        <i className={`fa-solid ${statusIcon[n.status] || 'fa-bell'} ${statusColor[n.status] || 'text-gray-500'} mt-0.5 flex-shrink-0`} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <p className="font-medium text-gray-900 text-sm truncate">{n.subject || '(No subject)'}</p>
                            {!read.has(n.id) && <span className="w-2 h-2 bg-blue-600 rounded-full flex-shrink-0 ml-2" />}
                          </div>
                          <p className="text-xs text-gray-600 mt-1 line-clamp-2">{n.body || '—'}</p>
                          <div className="flex items-center justify-between mt-2">
                            <span className="text-xs text-gray-400">{formatTime(n.sent_at || n.created_at)}</span>
                            <span className="text-xs text-gray-500 bg-white/70 px-2 py-0.5 rounded-full">
                              <i className={`fa-solid ${channelIcon[n.channel] || 'fa-bell'} mr-1`} />{n.channel}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContainer>
            ))}
          </div>
        )}
      </div>
    </MainLayout>
  )
}
