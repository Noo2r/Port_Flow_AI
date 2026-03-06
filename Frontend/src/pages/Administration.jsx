import { useState } from 'react'
import MainLayout from '../layout/MainLayout'
import Navbar from '../components/Navbar'
import { CardContainer, Badge, Button, SectionHeader, Tabs } from '../components/ui'
import { users, systemConfig } from '../data/mockData'

const roleColor = { 'Port Manager':'blue', 'Terminal Operator':'purple', 'Berth Planner':'green', 'Shipping Agent':'yellow', 'Cargo Inspector':'default', 'Security Officer':'red' }

export default function Administration() {
  const [activeTab, setActiveTab] = useState('User Management')
  const [config, setConfig] = useState(systemConfig)
  const [showAddUser, setShowAddUser] = useState(false)
  const [userList, setUserList] = useState(users)

  const toggleStatus = id => setUserList(prev => prev.map(u => u.id === id ? { ...u, status: u.status === 'Active' ? 'Inactive' : 'Active' } : u))

  const TABS = ['User Management','System Configuration','Audit Logs','Role Permissions']

  return (
    <MainLayout>
      <Navbar title="User Management & System Configuration" subtitle="Manage users, roles, permissions, and system settings">
        <Button variant="primary" onClick={() => setShowAddUser(true)}>
          <i className="fa-solid fa-plus" /> Add User
        </Button>
      </Navbar>

      <div className="flex-1 p-6 overflow-auto">
        <Tabs tabs={TABS} active={activeTab} onChange={setActiveTab} />

        {activeTab === 'User Management' && (
          <div className="space-y-6">
            {/* System stats */}
            <div className="grid grid-cols-4 gap-6">
              {[
                { label:'Total Users',  value: userList.length, icon:'fa-users',      bg:'bg-blue-100',   color:'text-blue-600' },
                { label:'Active Users', value: userList.filter(u=>u.status==='Active').length, icon:'fa-user-check', bg:'bg-green-100', color:'text-status-green' },
                { label:'Roles',        value: 6,               icon:'fa-id-badge',   bg:'bg-purple-100', color:'text-purple-600' },
                { label:'Last Backup',  value: config.lastBackup, icon:'fa-database', bg:'bg-yellow-100', color:'text-yellow-600' },
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

            {/* Users table */}
            <CardContainer>
              <div className="px-6 py-4 border-b border-gray-200">
                <SectionHeader title="All Users">
                  <input type="text" placeholder="Search users…" className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-64" />
                </SectionHeader>
              </div>
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    {['User','Role','Status','Last Login','Actions'].map(h => (
                      <th key={h} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {userList.map(u => (
                    <tr key={u.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-3">
                          <div className="w-9 h-9 bg-navy rounded-full flex items-center justify-center text-white text-sm font-medium">
                            {u.avatar}
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{u.name}</p>
                            <p className="text-xs text-gray-500">{u.email}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <Badge variant={roleColor[u.role] || 'default'}>{u.role}</Badge>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium ${u.status === 'Active' ? 'bg-green-100 text-status-green' : 'bg-gray-100 text-gray-600'}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${u.status === 'Active' ? 'bg-status-green' : 'bg-gray-400'}`} />
                          {u.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">{u.lastLogin}</td>
                      <td className="px-6 py-4">
                        <div className="flex space-x-2">
                          <button className="text-blue-600 hover:text-blue-800 text-sm"><i className="fa-solid fa-edit" /></button>
                          <button onClick={() => toggleStatus(u.id)} className="text-yellow-600 hover:text-yellow-800 text-sm">
                            <i className={`fa-solid ${u.status === 'Active' ? 'fa-ban' : 'fa-check'}`} />
                          </button>
                          <button className="text-red-600 hover:text-red-800 text-sm"><i className="fa-solid fa-trash" /></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContainer>
          </div>
        )}

        {activeTab === 'System Configuration' && (
          <CardContainer className="p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-6">System Settings</h3>
            <div className="space-y-6">
              {/* Toggles */}
              {[
                { key:'aiOptimization', label:'AI Optimization Engine', desc:'Automatically optimize berth assignments and resource allocation using AI' },
                { key:'autoAlerts',     label:'Automated Alert System',  desc:'Send automatic alerts for critical port events and threshold breaches' },
                { key:'maintenanceMode',label:'Maintenance Mode',        desc:'Put system in read-only maintenance mode for all non-admin users' },
              ].map(s => (
                <div key={s.key} className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
                  <div>
                    <p className="font-medium text-gray-900">{s.label}</p>
                    <p className="text-sm text-gray-600">{s.desc}</p>
                  </div>
                  <button
                    onClick={() => setConfig(c => ({ ...c, [s.key]: !c[s.key] }))}
                    className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${config[s.key] ? 'bg-blue-600' : 'bg-gray-200'}`}>
                    <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${config[s.key] ? 'translate-x-6' : 'translate-x-1'}`} />
                  </button>
                </div>
              ))}

              {/* System info */}
              <div className="grid grid-cols-3 gap-4 mt-4">
                {[
                  { label:'Version',     value: config.version },
                  { label:'System Uptime',value: config.uptime },
                  { label:'Last Backup', value: config.lastBackup },
                ].map(i => (
                  <div key={i.label} className="p-4 bg-gray-50 rounded-lg">
                    <p className="text-sm text-gray-600">{i.label}</p>
                    <p className="text-lg font-bold text-gray-900">{i.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </CardContainer>
        )}

        {activeTab === 'Audit Logs' && (
          <CardContainer className="p-6">
            <SectionHeader title="Audit Trail" />
            <div className="space-y-3">
              {[
                { user:'John Harbor',  action:'Updated berth assignment for MV Ocean Star',          time:'2 min ago',  icon:'fa-warehouse' },
                { user:'Sarah Lee',    action:'Marked Work Order WO-2024-008 as Completed',          time:'15 min ago', icon:'fa-check' },
                { user:'Mike Johnson', action:'Added new vessel MV Pacific Bridge to monitoring',     time:'1 hr ago',   icon:'fa-ship' },
                { user:'System',       action:'AI optimization applied – 3 berths reallocated',       time:'2 hr ago',   icon:'fa-robot' },
                { user:'Anna Clark',   action:'Exported cargo report (Q1 2024)',                      time:'3 hr ago',   icon:'fa-download' },
                { user:'System',       action:'Automated backup completed successfully',              time:'4 hr ago',   icon:'fa-database' },
              ].map((l, i) => (
                <div key={i} className="flex items-center space-x-4 p-3 hover:bg-gray-50 rounded-lg">
                  <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
                    <i className={`fa-solid ${l.icon} text-blue-600 text-sm`} />
                  </div>
                  <div className="flex-1">
                    <span className="font-medium text-gray-900">{l.user}</span>
                    <span className="text-gray-600"> – {l.action}</span>
                  </div>
                  <span className="text-xs text-gray-500 flex-shrink-0">{l.time}</span>
                </div>
              ))}
            </div>
          </CardContainer>
        )}

        {activeTab === 'Role Permissions' && (
          <CardContainer className="p-6 overflow-x-auto">
            <SectionHeader title="Role Permission Matrix" />
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="py-3 text-left font-medium text-gray-700">Permission</th>
                  {['Port Manager','Terminal Operator','Berth Planner','Shipping Agent'].map(r => (
                    <th key={r} className="py-3 text-center font-medium text-gray-700">{r}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {[
                  { perm:'View Dashboard',        pm:true,  to:true,  bp:true,  sa:true  },
                  { perm:'Manage Vessels',         pm:true,  to:true,  bp:false, sa:true  },
                  { perm:'Manage Berths',          pm:true,  to:true,  bp:true,  sa:false },
                  { perm:'Create Work Orders',     pm:true,  to:true,  bp:false, sa:false },
                  { perm:'View Analytics',         pm:true,  to:false, bp:true,  sa:false },
                  { perm:'System Configuration',   pm:true,  to:false, bp:false, sa:false },
                  { perm:'User Management',        pm:true,  to:false, bp:false, sa:false },
                  { perm:'Export Reports',         pm:true,  to:true,  bp:true,  sa:false },
                ].map(row => (
                  <tr key={row.perm} className="hover:bg-gray-50">
                    <td className="py-3 text-gray-900 font-medium">{row.perm}</td>
                    {[row.pm, row.to, row.bp, row.sa].map((v, i) => (
                      <td key={i} className="py-3 text-center">
                        <i className={`fa-solid ${v ? 'fa-check text-status-green' : 'fa-times text-gray-300'}`} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContainer>
        )}
      </div>

      {/* Add User Modal */}
      {showAddUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Add New User</h3>
              <button onClick={() => setShowAddUser(false)} className="text-gray-400 hover:text-gray-600">
                <i className="fa-solid fa-times" />
              </button>
            </div>
            <div className="space-y-4">
              {['Full Name','Email Address'].map(l => (
                <div key={l}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">{l}</label>
                  <input type={l.includes('Email') ? 'email' : 'text'} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
                </div>
              ))}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
                <select className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm">
                  {['Port Manager','Terminal Operator','Berth Planner','Shipping Agent','Cargo Inspector','Security Officer'].map(r => <option key={r}>{r}</option>)}
                </select>
              </div>
              <div className="flex space-x-3 pt-2">
                <Button variant="secondary" className="flex-1" onClick={() => setShowAddUser(false)}>Cancel</Button>
                <Button variant="primary" className="flex-1" onClick={() => setShowAddUser(false)}>Add User</Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </MainLayout>
  )
}
