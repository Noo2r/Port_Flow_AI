import { useState } from 'react'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { SmallStatCard, CardContainer, Badge, Button, Input, Select, SectionHeader, StatusDot } from '../components/ui'
import { vessels, vesselStats } from '../data/mockData'

const statusVariant = { Docked: 'green', 'En Route': 'blue', Anchored: 'yellow', Delayed: 'red', Departed: 'default' }
const typeVariant   = { Container: 'blue', 'Bulk Carrier': 'purple', Tanker: 'yellow', 'Ro-Ro': 'green' }

export default function VesselMonitoring() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All Statuses')
  const [typeFilter, setTypeFilter] = useState('All Vessel Types')

  const filtered = vessels.filter(v =>
    (search === '' || v.name.toLowerCase().includes(search.toLowerCase()) || v.imo.includes(search)) &&
    (statusFilter === 'All Statuses' || v.status === statusFilter) &&
    (typeFilter === 'All Vessel Types' || v.type === typeFilter)
  )

  return (
    <MainLayout>
      <Navbar title="Real-time Vessel Tracking" subtitle="Monitor vessel positions, statuses, and estimated arrival times" />

      <div className="flex-1 p-6 overflow-auto">
        {/* Controls */}
        <CardContainer className="p-4 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Input icon="fa-search" placeholder="Search vessel name, IMO, or MMSI…"
                className="w-80" value={search} onChange={e => setSearch(e.target.value)} />
              <Select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                options={['All Statuses', 'En Route', 'Anchored', 'Docked', 'Departed', 'Delayed']} />
              <Select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
                options={['All Vessel Types', 'Container', 'Bulk Carrier', 'Tanker', 'Ro-Ro']} />
            </div>
            <div className="flex items-center space-x-3">
              <Button variant="primary"><i className="fa-solid fa-download" /> Export</Button>
              <Button variant="secondary"><i className="fa-solid fa-filter" /> Filters</Button>
            </div>
          </div>
        </CardContainer>

        {/* Stats */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          <SmallStatCard label="En Route"     value={vesselStats.enRoute}  icon="fa-route"  iconBg="bg-blue-100"   iconColor="text-blue-600" />
          <SmallStatCard label="Anchored"     value={vesselStats.anchored} icon="fa-anchor" iconBg="bg-yellow-100" iconColor="text-yellow-600" />
          <SmallStatCard label="Docked"       value={vesselStats.docked}   icon="fa-ship"   iconBg="bg-green-100"  iconColor="text-status-green" />
          <SmallStatCard label="Delayed"      value={vesselStats.delayed}  icon="fa-clock"  iconBg="bg-red-100"    iconColor="text-status-red" />
          <SmallStatCard label="Total Tracked"value={vesselStats.total}    icon="fa-list"   iconBg="bg-gray-100"   iconColor="text-gray-600" />
        </div>

        {/* Table */}
        <CardContainer>
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Active Vessels</h3>
            <div className="flex items-center space-x-2">
              <button className="px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200">List View</button>
              <button className="px-3 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded">Map View</button>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Vessel Name','IMO / MMSI','Type','Status','Location','ETA','Speed','Actions'].map(h => (
                    <th key={h} className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filtered.map(v => (
                  <tr key={v.id} className="hover:bg-gray-50 cursor-pointer">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center mr-3">
                          <i className="fa-solid fa-ship text-blue-600 text-sm" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{v.name}</p>
                          <p className="text-xs text-gray-500">{v.flag} {v.type}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-gray-900">{v.imo}</p>
                      <p className="text-xs text-gray-500">{v.mmsi}</p>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant={typeVariant[v.type] || 'default'}>{v.type}</Badge>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        v.status === 'Docked'    ? 'bg-green-100 text-status-green'  :
                        v.status === 'En Route'  ? 'bg-blue-100 text-blue-700'       :
                        v.status === 'Anchored'  ? 'bg-yellow-100 text-yellow-700'   :
                        v.status === 'Delayed'   ? 'bg-red-100 text-status-red'      :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        <StatusDot status={v.status} />{v.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-gray-900">{v.location}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-gray-900">{v.eta}</p>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm text-gray-900">{v.speed}</p>
                    </td>
                    <td className="px-6 py-4">
                      <button className="text-blue-600 hover:text-blue-800">
                        <i className="fa-solid fa-eye" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="py-12 text-center text-gray-500">No vessels match your filters.</div>
            )}
          </div>
        </CardContainer>
      </div>
    </MainLayout>
  )
}
