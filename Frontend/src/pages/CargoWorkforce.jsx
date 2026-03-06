import { useState } from 'react'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { CardContainer, Badge, Button, Input, Select, SectionHeader } from '../components/ui'
import { workOrders, cargoStats } from '../data/mockData'

const priorityVariant = { High: 'red', Medium: 'yellow', Low: 'default' }
const statusVariant   = { 'In Progress': 'blue', Pending: 'yellow', Completed: 'green', Delayed: 'red' }

const avatarColors = ['bg-blue-500','bg-green-500','bg-purple-500','bg-yellow-500','bg-red-500','bg-pink-500']

export default function CargoWorkforce() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All Statuses')
  const [priorityFilter, setPriorityFilter] = useState('All Priorities')
  const [selected, setSelected] = useState([])
  const [page, setPage] = useState(0)

  const filtered = workOrders.filter(w =>
    (search === '' || w.id.toLowerCase().includes(search.toLowerCase()) || w.vessel.toLowerCase().includes(search.toLowerCase())) &&
    (statusFilter === 'All Statuses' || w.status === statusFilter) &&
    (priorityFilter === 'All Priorities' || w.priority === priorityFilter)
  )

  const toggleSelect = id => setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id])

  return (
    <MainLayout>
      <Navbar title="Cargo Management" subtitle="Track and manage cargo logistics and work orders">
        <Button variant="primary"><i className="fa-solid fa-plus" /> New Work Order</Button>
      </Navbar>

      {/* Filters */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Input icon="fa-search" placeholder="Search work orders…" className="w-80"
              value={search} onChange={e => setSearch(e.target.value)} />
            <Select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
              options={['All Statuses','Pending','In Progress','Completed','Delayed']} />
            <Select value={priorityFilter} onChange={e => setPriorityFilter(e.target.value)}
              options={['All Priorities','High','Medium','Low']} />
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="secondary"><i className="fa-solid fa-filter" /> More Filters</Button>
            <Button variant="secondary"><i className="fa-solid fa-download" /> Export</Button>
          </div>
        </div>
      </div>

      <div className="flex-1 p-6 overflow-auto">
        {/* Quick Stats */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          {[
            { label:'Total Orders', value: cargoStats.total,      icon:'fa-clipboard-list', bg:'bg-blue-100',   color:'text-blue-600' },
            { label:'Pending',      value: cargoStats.pending,    icon:'fa-clock',          bg:'bg-yellow-100', color:'text-status-yellow' },
            { label:'In Progress',  value: cargoStats.inProgress, icon:'fa-play',           bg:'bg-blue-100',   color:'text-blue-600' },
            { label:'Completed',    value: cargoStats.completed,  icon:'fa-check',          bg:'bg-green-100',  color:'text-status-green' },
            { label:'Delayed',      value: cargoStats.delayed,    icon:'fa-exclamation-triangle', bg:'bg-red-100', color:'text-status-red' },
          ].map(s => (
            <CardContainer key={s.label} className="p-4">
              <div className="flex items-center space-x-3">
                <div className={`w-10 h-10 ${s.bg} rounded-lg flex items-center justify-center`}>
                  <i className={`fa-solid ${s.icon} ${s.color}`} />
                </div>
                <div>
                  <p className="text-sm text-gray-600">{s.label}</p>
                  <p className="text-xl font-bold text-gray-900">{s.value}</p>
                </div>
              </div>
            </CardContainer>
          ))}
        </div>

        {/* Work Orders Table */}
        <CardContainer>
          <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">Work Orders</h3>
            <div className="flex items-center space-x-2">
              <span className="text-sm text-gray-500">Showing {filtered.length} of {workOrders.length}</span>
              <div className="flex space-x-1">
                <button className="p-2 border border-gray-300 rounded hover:bg-gray-50" onClick={() => setPage(p => Math.max(0,p-1))}>
                  <i className="fa-solid fa-chevron-left text-xs" />
                </button>
                <button className="p-2 border border-gray-300 rounded hover:bg-gray-50" onClick={() => setPage(p => p+1)}>
                  <i className="fa-solid fa-chevron-right text-xs" />
                </button>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left">
                    <input type="checkbox" className="rounded border-gray-300" />
                  </th>
                  {['Order ID','Type','Vessel','Cargo','Priority','Status','Assigned To','Due Date','Actions'].map(h => (
                    <th key={h} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filtered.map((w, idx) => (
                  <tr key={w.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <input type="checkbox" className="rounded border-gray-300"
                        checked={selected.includes(w.id)} onChange={() => toggleSelect(w.id)} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="font-medium text-blue-600 cursor-pointer hover:underline">{w.id}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{w.type}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{w.vessel}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{w.cargo}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant={priorityVariant[w.priority]}>{w.priority}</Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant={statusVariant[w.status]}>{w.status}</Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center space-x-2">
                        <div className={`w-6 h-6 ${avatarColors[idx % avatarColors.length]} rounded-full flex items-center justify-center text-white text-xs font-medium`}>
                          {w.assignee.split(' ').map(n=>n[0]).join('')}
                        </div>
                        <span className="text-sm text-gray-900">{w.assignee}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{w.due}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex space-x-2">
                        <button className="text-blue-600 hover:text-blue-800"><i className="fa-solid fa-eye" /></button>
                        <button className="text-green-600 hover:text-green-800"><i className="fa-solid fa-edit" /></button>
                        <button className="text-red-600 hover:text-red-800"><i className="fa-solid fa-trash" /></button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {filtered.length === 0 && (
              <div className="py-12 text-center text-gray-500">No work orders match your filters.</div>
            )}
          </div>
        </CardContainer>
      </div>
    </MainLayout>
  )
}
