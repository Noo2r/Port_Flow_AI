import { useState, useRef } from 'react'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { CardContainer, Badge, Button, SectionHeader, Tabs } from '../components/ui'
import { useUsers, useCreateUser, useUpdateUser } from '../hooks/queries'

// ── Constants ─────────────────────────────────────────────────────────────────
const ROLES = [
  { value: 'admin',        label: 'Admin' },
  { value: 'port_manager', label: 'Port Manager' },
  { value: 'vessel_agent', label: 'Vessel Agent' },
  { value: 'operations',   label: 'Operations' },
  { value: 'analyst',      label: 'Analyst' },
  { value: 'readonly',     label: 'Read Only' },
]

const roleColor = {
  admin:        'red',
  port_manager: 'blue',
  vessel_agent: 'yellow',
  operations:   'purple',
  analyst:      'green',
  readonly:     'default',
}

function roleLabel(r) {
  return ROLES.find(x => x.value === r)?.label || r || '—'
}

const TABS = ['User Management', 'System Configuration', 'Database', 'Audit Logs', 'Role Permissions']

export default function Administration() {
  const [activeTab, setActiveTab]   = useState('User Management')
  const [search,    setSearch]      = useState('')
  const [config,    setConfig]      = useState({
    aiOptimization: false,
    autoAlerts:     true,
    maintenanceMode:false,
  })

  // ── Edit state ──
  const [editUser,    setEditUser]    = useState(null)
  const [editSaving,  setEditSaving]  = useState(false)
  const [editError,   setEditError]   = useState('')

  // ── Add user state ──
  const [showAdd,     setShowAdd]     = useState(false)
  const [addSaving,   setAddSaving]   = useState(false)
  const [addError,    setAddError]    = useState('')
  const [addOk,       setAddOk]       = useState(false)
  const addNameRef    = useRef()
  const addEmailRef   = useRef()
  const addPassRef    = useRef()
  const addRoleRef    = useRef()

  const { data: usersData, isLoading: usersLoading } = useUsers()
  const createUser = useCreateUser()
  const updateUser = useUpdateUser()
  const userList = usersData || []

  const filtered = userList.filter(u => {
    const q = search.toLowerCase()
    return !q || (u.full_name || '').toLowerCase().includes(q) || (u.email || '').toLowerCase().includes(q)
  })

  // ── Add user ────────────────────────────────────────────────────────────────
  async function handleAdd(e) {
    e.preventDefault()
    setAddError('')
    setAddSaving(true)
    try {
      await createUser.mutateAsync({
        full_name: addNameRef.current.value.trim(),
        email:     addEmailRef.current.value.trim(),
        password:  addPassRef.current.value,
        role:      addRoleRef.current.value,
      })
      setAddOk(true)
      setTimeout(() => { setShowAdd(false); setAddOk(false) }, 1400)
    } catch (err) {
      setAddError(err.message || 'Failed to create user.')
    } finally {
      setAddSaving(false)
    }
  }

  // ── Edit user ───────────────────────────────────────────────────────────────
  async function handleEdit(e) {
    e.preventDefault()
    setEditError('')
    setEditSaving(true)
    const form = new FormData(e.target)
    try {
      await updateUser.mutateAsync({
        id: editUser.id,
        data: {
          full_name: form.get('full_name') || undefined,
          role:      form.get('role'),
          is_active: form.get('is_active') === 'true',
        },
      })
      setEditUser(null)
    } catch (err) {
      setEditError(err.message || 'Update failed.')
    } finally {
      setEditSaving(false)
    }
  }

  // ── Deactivate user (no DELETE endpoint — use is_active:false) ──────────────
  async function handleDeactivate(u) {
    if (u.is_active) {
      if (!window.confirm(`Deactivate "${u.full_name || u.email}"?\nThey will no longer be able to log in.`)) return
      try {
        await updateUser.mutateAsync({ id: u.id, data: { is_active: false } })
      } catch (err) { alert(`Failed: ${err.message}`) }
    } else {
      if (!window.confirm(`Reactivate "${u.full_name || u.email}"?`)) return
      try {
        await updateUser.mutateAsync({ id: u.id, data: { is_active: true } })
      } catch (err) { alert(`Failed: ${err.message}`) }
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────
  return (
    <MainLayout>
      <Navbar title="Administration" subtitle="Manage users, roles, permissions, and system settings">
        <Button variant="primary" onClick={() => { setAddError(''); setAddOk(false); setShowAdd(true) }}>
          <i className="fa-solid fa-plus" /> Add User
        </Button>
      </Navbar>

      <div className="flex-1 p-6 overflow-auto">
        <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />

        {/* ══════════════════════════════════════════════
            User Management
        ══════════════════════════════════════════════ */}
        {activeTab === 'User Management' && (
          <div className="space-y-5">
            {/* Stats */}
            <div className="grid grid-cols-4 gap-4">
              {[
                { label:'Total Users',  value: usersLoading ? '…' : userList.length,                              icon:'fa-users',      bg:'bg-blue-50',   color:'text-blue-600' },
                { label:'Active Users', value: usersLoading ? '…' : userList.filter(u => u.is_active).length,     icon:'fa-user-check', bg:'bg-green-50',  color:'text-green-600' },
                { label:'Inactive',     value: usersLoading ? '…' : userList.filter(u => !u.is_active).length,    icon:'fa-user-xmark', bg:'bg-red-50',    color:'text-red-500' },
                { label:'Roles',        value: 6,                                                                  icon:'fa-id-badge',   bg:'bg-purple-50', color:'text-purple-600' },
              ].map(s => (
                <CardContainer key={s.label} className="p-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 ${s.bg} rounded-xl flex items-center justify-center flex-shrink-0`}>
                      <i className={`fa-solid ${s.icon} ${s.color} text-sm`} />
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">{s.label}</p>
                      <p className="text-xl font-bold text-gray-900">{s.value}</p>
                    </div>
                  </div>
                </CardContainer>
              ))}
            </div>

            {/* Users table */}
            <CardContainer>
              <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
                <h3 className="font-semibold text-gray-900">All Users</h3>
                <div className="flex items-center gap-3">
                  <div className="relative">
                    <i className="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-xs" />
                    <input
                      type="text"
                      placeholder="Search users…"
                      value={search}
                      onChange={e => setSearch(e.target.value)}
                      className="border border-gray-200 rounded-lg pl-8 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-56"
                    />
                  </div>
                </div>
              </div>

              {usersLoading ? (
                <div className="p-6 text-center text-gray-400 text-sm">
                  <i className="fa-solid fa-spinner fa-spin mr-2" />Loading users…
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 border-b border-gray-100 text-xs text-gray-500 uppercase tracking-wide">
                        {['User', 'Role', 'Status', 'Last Login', 'Actions'].map(h => (
                          <th key={h} className="px-5 py-3 text-left font-semibold">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {filtered.map(u => (
                        <tr key={u.id} className="hover:bg-blue-50/20 transition-colors">
                          <td className="px-5 py-3.5">
                            <div className="flex items-center gap-3">
                              <div className="w-9 h-9 bg-gradient-to-br from-slate-600 to-slate-800 rounded-xl flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                                {(u.full_name || u.email || '?').charAt(0).toUpperCase()}
                              </div>
                              <div>
                                <p className="font-medium text-gray-900">{u.full_name || '—'}</p>
                                <p className="text-xs text-gray-400">{u.email}</p>
                              </div>
                            </div>
                          </td>
                          <td className="px-5 py-3.5">
                            <Badge variant={roleColor[u.role] || 'default'}>{roleLabel(u.role)}</Badge>
                          </td>
                          <td className="px-5 py-3.5">
                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${u.is_active ? 'bg-green-50 text-green-700 border-green-100' : 'bg-gray-100 text-gray-500 border-gray-200'}`}>
                              <span className={`w-1.5 h-1.5 rounded-full ${u.is_active ? 'bg-green-500' : 'bg-gray-400'}`} />
                              {u.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="px-5 py-3.5 text-gray-500 text-xs">
                            {u.last_login ? new Date(u.last_login).toLocaleDateString() : 'Never'}
                          </td>
                          <td className="px-5 py-3.5">
                            <div className="flex gap-1">
                              <button
                                title="Edit user"
                                onClick={() => { setEditError(''); setEditUser(u) }}
                                className="w-7 h-7 rounded flex items-center justify-center text-blue-500 hover:bg-blue-50"
                              >
                                <i className="fa-solid fa-pen text-xs" />
                              </button>
                              <button
                                title={u.is_active ? 'Deactivate user' : 'Reactivate user'}
                                onClick={() => handleDeactivate(u)}
                                className={`w-7 h-7 rounded flex items-center justify-center ${u.is_active ? 'text-red-400 hover:bg-red-50' : 'text-green-500 hover:bg-green-50'}`}
                              >
                                <i className={`fa-solid ${u.is_active ? 'fa-ban' : 'fa-circle-check'} text-xs`} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {filtered.length === 0 && (
                    <div className="py-10 text-center text-gray-400 text-sm">
                      {search ? `No users matching "${search}"` : 'No users found.'}
                    </div>
                  )}
                </div>
              )}
            </CardContainer>
          </div>
        )}

        {/* ══════════════════════════════════════════════
            System Configuration
        ══════════════════════════════════════════════ */}
        {activeTab === 'System Configuration' && (
          <CardContainer className="p-6">
            <h3 className="font-semibold text-gray-900 mb-5">System Settings</h3>
            <div className="space-y-4">
              {[
                { key:'aiOptimization', label:'AI Optimization Engine',  desc:'Automatically optimize berth assignments and resource allocation using AI' },
                { key:'autoAlerts',     label:'Automated Alert System',   desc:'Send automatic alerts for critical port events and threshold breaches' },
                { key:'maintenanceMode',label:'Maintenance Mode',          desc:'Put system in read-only maintenance mode for all non-admin users' },
              ].map(s => (
                <div key={s.key} className="flex items-center justify-between p-4 border border-gray-100 rounded-xl hover:bg-gray-50 transition-colors">
                  <div>
                    <p className="font-medium text-gray-900 text-sm">{s.label}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{s.desc}</p>
                  </div>
                  <button
                    onClick={() => setConfig(c => ({ ...c, [s.key]: !c[s.key] }))}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0 ml-6 ${config[s.key] ? 'bg-blue-600' : 'bg-gray-200'}`}
                  >
                    <span className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${config[s.key] ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>
              ))}
              <div className="grid grid-cols-3 gap-4 mt-2 pt-2 border-t border-gray-100">
                {[
                  { label:'Version',      value: '2.0.0' },
                  { label:'System Status',value: 'Live' },
                  { label:'Last Backup',  value: 'Not configured' },
                ].map(i => (
                  <div key={i.label} className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                    <p className="text-xs text-gray-500">{i.label}</p>
                    <p className="text-base font-bold text-gray-900 mt-0.5">{i.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </CardContainer>
        )}

        {/* ══════════════════════════════════════════════
            Database
        ══════════════════════════════════════════════ */}
        {activeTab === 'Database' && (
          <div className="space-y-5">
            <CardContainer className="p-6">
              <div className="flex items-center gap-2 mb-4">
                <i className="fa-solid fa-database text-blue-600" />
                <h3 className="font-semibold text-gray-900">Database Connection</h3>
                <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-700 border border-green-100">
                  <span className="w-1.5 h-1.5 rounded-full bg-green-500" />Connected
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3 mb-5">
                {[
                  { label:'Host',     value:'localhost' },
                  { label:'Port',     value:'5432' },
                  { label:'Database', value:'portflow' },
                  { label:'Username', value:'portflow' },
                  { label:'Engine',   value:'PostgreSQL 18' },
                  { label:'Network',  value:'localhost / LAN' },
                ].map(item => (
                  <div key={item.label} className="p-3 bg-gray-50 rounded-lg border border-gray-100">
                    <p className="text-xs text-gray-400 mb-0.5">{item.label}</p>
                    <p className="font-mono text-sm font-medium text-gray-900">{item.value}</p>
                  </div>
                ))}
              </div>
              <div className="p-4 bg-blue-50 border border-blue-100 rounded-xl flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0">
                    <i className="fa-solid fa-database text-white text-sm" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900 text-sm">pgAdmin 4</p>
                    <p className="text-xs text-gray-500">Browse tables, run queries, and manage data visually</p>
                  </div>
                </div>
                <a href="http://localhost:63198" target="_blank" rel="noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
                  Open pgAdmin4 <i className="fa-solid fa-arrow-up-right-from-square text-xs" />
                </a>
              </div>
              <p className="text-xs text-gray-400 mt-2">* If pgAdmin4 doesn't open, launch it from your Start menu — it uses a random port each session.</p>
            </CardContainer>

            <CardContainer className="p-6">
              <SectionHeader title="Database Tables" />
              <div className="grid grid-cols-3 gap-3">
                {[
                  { table:'vessels',         icon:'fa-ship',                desc:'Vessel registry' },
                  { table:'ports',           icon:'fa-anchor',              desc:'Port registry (WPI)' },
                  { table:'berths',          icon:'fa-warehouse',           desc:'Berth definitions' },
                  { table:'visits',          icon:'fa-calendar',            desc:'Vessel port visits' },
                  { table:'voyages',         icon:'fa-route',               desc:'Voyage records' },
                  { table:'work_orders',     icon:'fa-clipboard-list',      desc:'Work orders' },
                  { table:'users',           icon:'fa-users',               desc:'System users' },
                  { table:'notifications',   icon:'fa-bell',                desc:'Notifications' },
                  { table:'predictions',     icon:'fa-brain',               desc:'AI predictions' },
                  { table:'audit_trails',    icon:'fa-shield',              desc:'Audit log' },
                  { table:'weather_data',    icon:'fa-cloud',               desc:'Weather records' },
                  { table:'kpi_values',      icon:'fa-chart-line',          desc:'KPI data' },
                ].map(t => (
                  <div key={t.table} className="flex items-center gap-3 p-3 border border-gray-100 rounded-lg hover:bg-gray-50">
                    <div className="w-8 h-8 bg-blue-50 rounded-lg flex items-center justify-center flex-shrink-0">
                      <i className={`fa-solid ${t.icon} text-blue-500 text-xs`} />
                    </div>
                    <div>
                      <p className="font-mono text-xs font-semibold text-gray-900">{t.table}</p>
                      <p className="text-xs text-gray-400">{t.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContainer>
          </div>
        )}

        {/* ══════════════════════════════════════════════
            Audit Logs
        ══════════════════════════════════════════════ */}
        {activeTab === 'Audit Logs' && (
          <CardContainer className="p-6">
            <SectionHeader title="Audit Trail" />
            <div className="flex flex-col items-center justify-center py-16 text-gray-400">
              <i className="fa-solid fa-clipboard-list text-4xl mb-3 opacity-20" />
              <p className="text-sm font-medium text-gray-500">No audit logs yet</p>
              <p className="text-xs mt-1">All user actions (logins, edits, deletions) will be recorded here automatically.</p>
            </div>
          </CardContainer>
        )}

        {/* ══════════════════════════════════════════════
            Role Permissions
        ══════════════════════════════════════════════ */}
        {activeTab === 'Role Permissions' && (
          <CardContainer className="p-6 overflow-x-auto">
            <SectionHeader title="Role Permission Matrix" />
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100">
                  <th className="py-3 text-left font-semibold text-gray-700 pr-6">Permission</th>
                  {['Admin', 'Port Manager', 'Operations', 'Analyst', 'Read Only'].map(r => (
                    <th key={r} className="py-3 text-center font-semibold text-gray-700 px-3">{r}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {[
                  { perm:'View Dashboard',       vals:[true,  true,  true,  true,  true]  },
                  { perm:'Manage Vessels',        vals:[true,  true,  true,  false, false] },
                  { perm:'Manage Berths',         vals:[true,  true,  true,  false, false] },
                  { perm:'Create Work Orders',    vals:[true,  true,  true,  false, false] },
                  { perm:'View Analytics',        vals:[true,  true,  true,  true,  true]  },
                  { perm:'AI Predictions',        vals:[true,  true,  false, true,  true]  },
                  { perm:'Export Reports',        vals:[true,  true,  true,  true,  false] },
                  { perm:'System Configuration',  vals:[true,  false, false, false, false] },
                  { perm:'User Management',       vals:[true,  false, false, false, false] },
                ].map(row => (
                  <tr key={row.perm} className="hover:bg-gray-50">
                    <td className="py-2.5 text-gray-700 font-medium pr-6">{row.perm}</td>
                    {row.vals.map((v, i) => (
                      <td key={i} className="py-2.5 text-center px-3">
                        {v
                          ? <i className="fa-solid fa-check text-green-500" />
                          : <i className="fa-solid fa-minus text-gray-200" />}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContainer>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════
          Add User Modal
      ═══════════════════════════════════════════════════ */}
      {showAdd && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-900">Add New User</h3>
              <button onClick={() => setShowAdd(false)} className="text-gray-400 hover:text-gray-600 w-7 h-7 flex items-center justify-center rounded hover:bg-gray-100">
                <i className="fa-solid fa-xmark" />
              </button>
            </div>
            <div className="p-6">
              {addOk ? (
                <div className="py-8 text-center text-green-600">
                  <i className="fa-solid fa-circle-check text-4xl mb-3 block" />
                  <p className="font-medium">User created successfully!</p>
                </div>
              ) : (
                <form onSubmit={handleAdd} className="space-y-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Full Name <span className="text-red-500">*</span></label>
                    <input ref={addNameRef} required minLength={2} placeholder="e.g. John Smith"
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Email Address <span className="text-red-500">*</span></label>
                    <input ref={addEmailRef} required type="email" placeholder="user@example.com"
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Password <span className="text-red-500">*</span></label>
                    <input ref={addPassRef} required type="password" minLength={8} placeholder="Min 8 chars, 1 uppercase, 1 digit"
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                    <p className="text-xs text-gray-400 mt-1">At least 8 characters, one uppercase letter, one digit</p>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Role</label>
                    <select ref={addRoleRef} defaultValue="readonly"
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                      {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                    </select>
                  </div>
                  {addError && (
                    <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-xs text-red-600">
                      <i className="fa-solid fa-circle-exclamation mr-1" />{addError}
                    </div>
                  )}
                  <div className="flex gap-3 pt-1">
                    <button type="button" onClick={() => setShowAdd(false)}
                      className="flex-1 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
                    <button type="submit" disabled={addSaving}
                      className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60">
                      {addSaving ? <><i className="fa-solid fa-spinner fa-spin mr-1" />Creating…</> : 'Create User'}
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════
          Edit User Modal
      ═══════════════════════════════════════════════════ */}
      {editUser && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="font-semibold text-gray-900">Edit User</h3>
              <button onClick={() => setEditUser(null)} className="text-gray-400 hover:text-gray-600 w-7 h-7 flex items-center justify-center rounded hover:bg-gray-100">
                <i className="fa-solid fa-xmark" />
              </button>
            </div>
            <div className="p-6">
              <form onSubmit={handleEdit} className="space-y-4">
                {/* Read-only info */}
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
                  <div className="w-10 h-10 bg-slate-700 rounded-xl flex items-center justify-center text-white font-bold flex-shrink-0">
                    {(editUser.full_name || editUser.email || '?').charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-900">{editUser.email}</p>
                    <p className="text-xs text-gray-400">User ID #{editUser.id}</p>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Full Name</label>
                  <input name="full_name" defaultValue={editUser.full_name || ''}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Role</label>
                    <select name="role" defaultValue={editUser.role}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                      {ROLES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Status</label>
                    <select name="is_active" defaultValue={editUser.is_active ? 'true' : 'false'}
                      className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
                      <option value="true">Active</option>
                      <option value="false">Inactive</option>
                    </select>
                  </div>
                </div>
                {editError && (
                  <div className="p-3 bg-red-50 border border-red-100 rounded-lg text-xs text-red-600">
                    <i className="fa-solid fa-circle-exclamation mr-1" />{editError}
                  </div>
                )}
                <div className="flex gap-3 pt-1">
                  <button type="button" onClick={() => setEditUser(null)}
                    className="flex-1 py-2.5 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50">Cancel</button>
                  <button type="submit" disabled={editSaving}
                    className="flex-1 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-60">
                    {editSaving ? <><i className="fa-solid fa-spinner fa-spin mr-1" />Saving…</> : 'Save Changes'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  )
}
