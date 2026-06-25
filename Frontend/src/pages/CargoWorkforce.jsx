import { useState, useRef } from 'react'
import * as XLSX from 'xlsx'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { CardContainer, Badge, Button, Input, Select, SectionHeader } from '../components/ui'
import {
  useWorkOrders, useVessels, useVisits,
  useCreateWorkOrder, useUpdateWorkOrder, useDeleteWorkOrder,
} from '../hooks/queries'

const ORDER_TYPES = [
  'mooring','unmooring','pilotage','tugboat','cargo_handling',
  'customs_inspection','health_inspection','bunkering',
  'fresh_water','waste_reception','maintenance','general',
]

const priorityVariant = { high: 'red', normal: 'yellow', low: 'default', urgent: 'red' }
const statusVariant   = { in_progress: 'blue', pending: 'yellow', completed: 'green', cancelled: 'red', assigned: 'blue' }

function priorityLabel(p) { return p ? p.charAt(0).toUpperCase() + p.slice(1) : '—' }
function statusLabel(s) {
  const map = { in_progress: 'In Progress', pending: 'Pending', completed: 'Completed', cancelled: 'Cancelled', assigned: 'Assigned' }
  return map[s] || s || '—'
}

const PAGE_SIZE = 10

export default function CargoWorkforce() {
  const [search, setSearch]               = useState('')
  const [statusFilter, setStatusFilter]   = useState('All Statuses')
  const [priorityFilter, setPriorityFilter] = useState('All Priorities')
  const [selected, setSelected]           = useState([])
  const [page, setPage]                   = useState(0)
  const [showModal, setShowModal]         = useState(false)
  const [editModal, setEditModal]         = useState(null)   // work order being edited
  const [editSaving, setEditSaving]       = useState(false)
  const [editError, setEditError]         = useState('')
  const [saving, setSaving]               = useState(false)
  const [saveError, setSaveError]         = useState('')

  const titleRef      = useRef()
  const descRef       = useRef()
  const orderTypeRef  = useRef()
  const priorityRef   = useRef()
  const scheduledRef  = useRef()
  const vesselIdRef   = useRef()
  const visitIdRef    = useRef()

  const { data: workOrders, isLoading: loading, error } = useWorkOrders()
  const { data: vessels } = useVessels(0, 200)
  const { data: visits  } = useVisits()
  const createWorkOrder = useCreateWorkOrder()
  const updateWorkOrder = useUpdateWorkOrder()
  const deleteWorkOrder = useDeleteWorkOrder()
  const list        = workOrders || []
  const vesselList  = vessels   || []
  const visitList   = visits    || []

  const filtered = list.filter(w =>
    (search === '' || String(w.id).includes(search) || (w.title || '').toLowerCase().includes(search.toLowerCase())) &&
    (statusFilter === 'All Statuses' || statusLabel(w.status) === statusFilter) &&
    (priorityFilter === 'All Priorities' || priorityLabel(w.priority) === priorityFilter)
  )

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const paginated  = filtered.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE)

  const toggleSelect = id => setSelected(s => s.includes(id) ? s.filter(x => x !== id) : [...s, id])

  // ── Export to Excel ────────────────────────────────────────────────────────
  function handleExport() {
    const rows = filtered.map(w => ({
      'Order ID':       w.id,
      'Title':          w.title || '',
      'Type':           (w.order_type || '').replace(/_/g,' '),
      'Priority':       priorityLabel(w.priority),
      'Status':         statusLabel(w.status),
      'Vessel ID':      w.vessel_id || '',
      'Visit ID':       w.visit_id || '',
      'Assigned To':    w.assigned_user_id ? `User #${w.assigned_user_id}` : 'Unassigned',
      'Scheduled Start':w.scheduled_start ? new Date(w.scheduled_start).toLocaleString() : '',
      'Description':    w.description || '',
    }))
    const ws = XLSX.utils.json_to_sheet(rows)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Work Orders')
    XLSX.writeFile(wb, `work-orders-${new Date().toISOString().slice(0,10)}.xlsx`)
  }

  // ── Edit work order ────────────────────────────────────────────────────────
  async function handleEdit(e) {
    e.preventDefault()
    setEditSaving(true); setEditError('')
    const form = new FormData(e.target)
    try {
      await updateWorkOrder.mutateAsync({
        id: editModal.id,
        data: {
          title:    form.get('title'),
          priority: form.get('priority'),
          status:   form.get('status'),
          description: form.get('description') || undefined,
        },
      })
      setEditModal(null)
    } catch (err) { setEditError(err.message || 'Update failed.') }
    finally { setEditSaving(false) }
  }

  // ── Delete work order ──────────────────────────────────────────────────────
  async function handleDelete(w) {
    if (!window.confirm(`Delete work order #${w.id} "${w.title}"?\nThis cannot be undone.`)) return
    try { await deleteWorkOrder.mutateAsync(w.id) }
    catch (err) { alert(`Delete failed: ${err.message}`) }
  }

  async function handleCreate(e) {
    e.preventDefault()
    setSaveError('')
    setSaving(true)
    try {
      await createWorkOrder.mutateAsync({
        title:           titleRef.current.value.trim(),
        description:     descRef.current.value.trim() || undefined,
        order_type:      orderTypeRef.current.value,
        priority:        priorityRef.current.value,
        vessel_id:       Number(vesselIdRef.current.value),
        visit_id:        Number(visitIdRef.current.value),
        scheduled_start: scheduledRef.current.value || undefined,
      })
      setShowModal(false)
    } catch (err) {
      setSaveError(err.message || 'Failed to create work order.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <MainLayout>
      <Navbar title="Cargo Management" subtitle="Track and manage cargo logistics and work orders">
        <Button variant="primary" onClick={() => { setSaveError(''); setShowModal(true) }}>
          <i className="fa-solid fa-plus" /> New Work Order
        </Button>
      </Navbar>

      {/* Filters */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Input icon="fa-search" placeholder="Search work orders…" className="w-80"
              value={search} onChange={e => { setSearch(e.target.value); setPage(0) }} />
            <Select value={statusFilter} onChange={e => { setStatusFilter(e.target.value); setPage(0) }}
              options={['All Statuses','Pending','In Progress','Completed','Cancelled']} />
            <Select value={priorityFilter} onChange={e => { setPriorityFilter(e.target.value); setPage(0) }}
              options={['All Priorities','High','Normal','Low','Urgent']} />
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="secondary" onClick={handleExport}><i className="fa-solid fa-download" /> Export</Button>
          </div>
        </div>
      </div>

      <div className="flex-1 p-6 overflow-auto">
        {/* Quick Stats */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          {[
            { label:'Total Orders', value: loading ? '…' : list.length,                                     icon:'fa-clipboard-list', bg:'bg-blue-100',   color:'text-blue-600' },
            { label:'Pending',      value: loading ? '…' : list.filter(w=>w.status==='pending').length,     icon:'fa-clock',          bg:'bg-yellow-100', color:'text-status-yellow' },
            { label:'In Progress',  value: loading ? '…' : list.filter(w=>w.status==='in_progress').length, icon:'fa-play',           bg:'bg-blue-100',   color:'text-blue-600' },
            { label:'Completed',    value: loading ? '…' : list.filter(w=>w.status==='completed').length,   icon:'fa-check',          bg:'bg-green-100',  color:'text-status-green' },
            { label:'Cancelled',    value: loading ? '…' : list.filter(w=>w.status==='cancelled').length,   icon:'fa-xmark',          bg:'bg-red-100',    color:'text-status-red' },
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
              <span className="text-sm text-gray-500">
                {filtered.length === 0 ? '0 orders' : `${page * PAGE_SIZE + 1}–${Math.min((page + 1) * PAGE_SIZE, filtered.length)} of ${filtered.length}`}
              </span>
              <button className="p-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
                disabled={page === 0} onClick={() => setPage(p => Math.max(0, p - 1))}>
                <i className="fa-solid fa-chevron-left text-xs" />
              </button>
              <button className="p-2 border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
                disabled={page >= totalPages - 1} onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}>
                <i className="fa-solid fa-chevron-right text-xs" />
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left">
                    <input type="checkbox" className="rounded border-gray-300" />
                  </th>
                  {['Order ID','Type','Title','Priority','Status','Assigned To','Scheduled','Actions'].map(h => (
                    <th key={h} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {loading && (
                  <tr><td colSpan={9} className="px-6 py-8 text-center text-gray-500">
                    <i className="fa-solid fa-spinner fa-spin mr-2" />Loading work orders…
                  </td></tr>
                )}
                {error && (
                  <tr><td colSpan={9} className="px-6 py-8 text-center text-red-600">
                    <i className="fa-solid fa-circle-exclamation mr-2" />{error.message}
                  </td></tr>
                )}
                {!loading && !error && paginated.map((w) => (
                  <tr key={w.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <input type="checkbox" className="rounded border-gray-300"
                        checked={selected.includes(w.id)} onChange={() => toggleSelect(w.id)} />
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className="font-medium text-blue-600">#{w.id}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{(w.order_type || '').replace(/_/g,' ')}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{w.title || '—'}</td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant={priorityVariant[w.priority] || 'default'}>{priorityLabel(w.priority)}</Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <Badge variant={statusVariant[w.status] || 'default'}>{statusLabel(w.status)}</Badge>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {w.assigned_user_id ? `User #${w.assigned_user_id}` : 'Unassigned'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {w.scheduled_start ? new Date(w.scheduled_start).toLocaleDateString() : '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex space-x-1">
                        <button title="Edit"
                          onClick={() => { setEditError(''); setEditModal(w) }}
                          className="w-7 h-7 rounded flex items-center justify-center text-blue-500 hover:bg-blue-50">
                          <i className="fa-solid fa-pen text-xs" />
                        </button>
                        <button title="Delete"
                          onClick={() => handleDelete(w)}
                          className="w-7 h-7 rounded flex items-center justify-center text-red-400 hover:bg-red-50">
                          <i className="fa-solid fa-trash text-xs" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!loading && !error && filtered.length === 0 && (
              <div className="py-12 text-center text-gray-500">
                <i className="fa-solid fa-clipboard-list text-3xl mb-3 opacity-30 block" />
                No work orders yet. Click <strong>New Work Order</strong> to create one.
              </div>
            )}
          </div>
        </CardContainer>
      </div>

      {/* New Work Order Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-lg mx-4">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-lg font-semibold text-gray-900">New Work Order</h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <i className="fa-solid fa-times" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Title <span className="text-red-500">*</span></label>
                <input ref={titleRef} name="title" required type="text" placeholder="e.g. Unload Container Batch A"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea ref={descRef} rows={3} placeholder="Optional details…"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Vessel <span className="text-red-500">*</span></label>
                  <select ref={vesselIdRef} required
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="">— Select vessel —</option>
                    {vesselList.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Visit <span className="text-red-500">*</span></label>
                  <select ref={visitIdRef} required
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="">— Select visit —</option>
                    {visitList.map(v => <option key={v.id} value={v.id}>Visit #{v.id} – {v.status || ''}</option>)}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Order Type <span className="text-red-500">*</span></label>
                  <select ref={orderTypeRef} required
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    {ORDER_TYPES.map(t => <option key={t} value={t}>{t.replace(/_/g,' ')}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Priority</label>
                  <select ref={priorityRef}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="normal">Normal</option>
                    <option value="low">Low</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Scheduled Start</label>
                <input ref={scheduledRef} type="datetime-local"
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>

              {saveError && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  <i className="fa-solid fa-circle-exclamation mr-2" />{saveError}
                </div>
              )}

              <div className="flex space-x-3 pt-2">
                <button type="button" onClick={() => setShowModal(false)}
                  className="flex-1 py-2 px-4 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 text-sm font-medium">
                  Cancel
                </button>
                <button type="submit" disabled={saving}
                  className="flex-1 py-2 px-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-60">
                  {saving ? <><i className="fa-solid fa-spinner fa-spin mr-2" />Creating…</> : 'Create Work Order'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Edit Work Order Modal */}
      {editModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-semibold text-gray-900">Edit Work Order #{editModal.id}</h3>
              <button onClick={() => setEditModal(null)} className="text-gray-400 hover:text-gray-600">
                <i className="fa-solid fa-xmark" />
              </button>
            </div>
            <form onSubmit={handleEdit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Title</label>
                <input name="title" defaultValue={editModal.title || ''}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
                <textarea name="description" rows={3} defaultValue={editModal.description || ''}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
                  <select name="status" defaultValue={editModal.status}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="pending">Pending</option>
                    <option value="assigned">Assigned</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Priority</label>
                  <select name="priority" defaultValue={editModal.priority}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                    <option value="low">Low</option>
                    <option value="normal">Normal</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>
              {editError && (
                <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-xs text-red-600">
                  <i className="fa-solid fa-circle-exclamation mr-1" />{editError}
                </div>
              )}
              <div className="flex gap-3 pt-1">
                <button type="button" onClick={() => setEditModal(null)}
                  className="flex-1 py-2 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
                <button type="submit" disabled={editSaving}
                  className="flex-1 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60">
                  {editSaving ? <><i className="fa-solid fa-spinner fa-spin mr-1" />Saving…</> : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </MainLayout>
  )
}
