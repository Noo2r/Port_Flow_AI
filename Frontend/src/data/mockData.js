// ─── Vessel Data ───────────────────────────────────────────────
export const vessels = [
  { id: 1, name: 'MV Ocean Star',        imo: '9876543', mmsi: '367123456', type: 'Container',   status: 'Docked',   location: 'Berth A1',          eta: '–',         speed: '0 kn',  flag: '🇺🇸' },
  { id: 2, name: 'MV Container Express', imo: '9765432', mmsi: '366234567', type: 'Container',   status: 'Delayed',  location: '48°N 012°W',        eta: '16:30',     speed: '14 kn', flag: '🇩🇪' },
  { id: 3, name: 'MV Baltic Wind',       imo: '9654321', mmsi: '230345678', type: 'Bulk Carrier',status: 'Docked',   location: 'Berth B2',          eta: '–',         speed: '0 kn',  flag: '🇫🇮' },
  { id: 4, name: 'MV Trade Wind',        imo: '9543210', mmsi: '319456789', type: 'Ro-Ro',       status: 'En Route', location: '52°N 008°W',        eta: '09:00',     speed: '18 kn', flag: '🇬🇧' },
  { id: 5, name: 'MV Bulk Carrier',      imo: '9432109', mmsi: '244567890', type: 'Bulk Carrier',status: 'Anchored', location: 'Outer Anchorage 3', eta: '14:00',     speed: '0 kn',  flag: '🇳🇱' },
  { id: 6, name: 'MV Cargo King',        imo: '9321098', mmsi: '477678901', type: 'Container',   status: 'En Route', location: '45°N 015°W',        eta: 'Tomorrow',  speed: '16 kn', flag: '🇨🇳' },
  { id: 7, name: 'MV Northern Star',     imo: '9210987', mmsi: '257789012', type: 'Tanker',      status: 'En Route', location: '55°N 005°E',        eta: 'Tomorrow',  speed: '13 kn', flag: '🇳🇴' },
  { id: 8, name: 'MV Pacific Bridge',    imo: '9109876', mmsi: '431890123', type: 'Container',   status: 'Departed', location: '48°N 002°W',        eta: '–',         speed: '21 kn', flag: '🇯🇵' },
]

export const vesselStats = {
  enRoute: 12, anchored: 5, docked: 7, delayed: 3, total: 27,
}

// ─── Berth Data ────────────────────────────────────────────────
export const berths = [
  { id: 'A1', type: 'Deep Water',    slots: ['empty','occupied','occupied','occupied','available','available','available'], vessel: 'MV Ocean Star' },
  { id: 'A2', type: 'Container',     slots: ['maintenance','maintenance','conflict','occupied','occupied','available','available'], vessel: 'MV Cargo King' },
  { id: 'B1', type: 'General Cargo', slots: ['available','available','available','available','available','occupied','occupied'], vessel: 'MV Trade Wind' },
  { id: 'B2', type: 'Container',     slots: ['occupied','occupied','occupied','occupied','available','available','available'], vessel: 'MV Baltic Wind' },
  { id: 'C1', type: 'Bulk Cargo',    slots: ['available','available','occupied','occupied','occupied','occupied','available'], vessel: 'MV Bulk Carrier' },
  { id: 'C2', type: 'RoRo',         slots: ['available','available','available','available','available','available','available'], vessel: null },
]

export const berthStatusCards = [
  { name: 'Berth A1', vessel: 'MV Ocean Star',  status: 'Occupied',    color: 'green' },
  { name: 'Berth A2', vessel: 'Maintenance',     status: 'Unavailable', color: 'yellow' },
  { name: 'Berth B1', vessel: 'Available',       status: 'Free',        color: 'gray' },
  { name: 'Berth B2', vessel: 'MV Baltic Wind',  status: 'Occupied',    color: 'green' },
]

// ─── Work Orders ────────────────────────────────────────────────
export const workOrders = [
  { id: 'WO-2024-001', type: 'Container Loading',   vessel: 'MV Ocean Star',        cargo: 'Electronics – 45 TEUs',   priority: 'High',   status: 'In Progress', assignee: 'Mike Johnson',  due: 'Jan 20, 14:00' },
  { id: 'WO-2024-002', type: 'Container Discharge',  vessel: 'MV Baltic Wind',       cargo: 'Auto Parts – 67 TEUs',    priority: 'Medium', status: 'In Progress', assignee: 'Sarah Lee',    due: 'Jan 20, 16:00' },
  { id: 'WO-2024-003', type: 'Bulk Loading',         vessel: 'MV Bulk Carrier',      cargo: 'Grain – 2,500 MT',        priority: 'High',   status: 'Pending',     assignee: 'Tom Baker',    due: 'Jan 21, 08:00' },
  { id: 'WO-2024-004', type: 'Vehicle Loading',      vessel: 'MV Trade Wind',        cargo: 'Vehicles – 120 Units',    priority: 'Medium', status: 'Pending',     assignee: 'Anna Clark',   due: 'Jan 21, 12:00' },
  { id: 'WO-2024-005', type: 'Container Discharge',  vessel: 'MV Container Express', cargo: 'General – 89 TEUs',       priority: 'Low',    status: 'Delayed',     assignee: 'Chris Evans',  due: 'Jan 20, 10:00' },
  { id: 'WO-2024-006', type: 'Container Loading',    vessel: 'MV Cargo King',        cargo: 'Machinery – 34 TEUs',     priority: 'High',   status: 'Pending',     assignee: 'Mike Johnson', due: 'Jan 22, 06:00' },
  { id: 'WO-2024-007', type: 'Tanker Discharge',     vessel: 'MV Northern Star',     cargo: 'Crude Oil – 45,000 MT',   priority: 'High',   status: 'Pending',     assignee: 'Sarah Lee',    due: 'Jan 22, 14:00' },
  { id: 'WO-2024-008', type: 'Container Loading',    vessel: 'MV Ocean Star',        cargo: 'Consumer Goods – 55 TEUs',priority: 'Medium', status: 'Completed',   assignee: 'Tom Baker',    due: 'Jan 19, 18:00' },
  { id: 'WO-2024-009', type: 'Container Discharge',  vessel: 'MV Baltic Wind',       cargo: 'Food Products – 42 TEUs', priority: 'Medium', status: 'Completed',   assignee: 'Anna Clark',   due: 'Jan 19, 20:00' },
  { id: 'WO-2024-010', type: 'Bulk Discharge',       vessel: 'MV Bulk Carrier',      cargo: 'Coal – 1,800 MT',         priority: 'Low',    status: 'Completed',   assignee: 'Chris Evans',  due: 'Jan 19, 16:00' },
]

export const cargoStats = { total: 156, pending: 23, inProgress: 47, completed: 82, delayed: 4 }

// ─── Notifications ──────────────────────────────────────────────
export const notifications = [
  { id: 1, severity: 'critical', category: 'Weather',        title: 'Severe Weather Alert',         message: 'High winds expected (35+ knots) – Consider vessel movement restrictions in Terminal A and B.',  time: '2 min ago',  read: false },
  { id: 2, severity: 'critical', category: 'Equipment',      title: 'Crane #3 Equipment Failure',   message: 'Crane #3 at Berth A2 is offline due to hydraulic failure. Maintenance team dispatched.',        time: '45 min ago', read: false },
  { id: 3, severity: 'critical', category: 'Security',       title: 'Unauthorized Access Attempt',  message: 'Multiple failed login attempts detected on admin portal. Account temporarily locked.',           time: '1 hr ago',   read: false },
  { id: 4, severity: 'critical', category: 'Vessel Ops',     title: 'Vessel Grounding Risk',        message: 'MV Northern Star approaching shallow waters. Immediate course correction required.',             time: '3 hr ago',   read: false },
  { id: 5, severity: 'critical', category: 'Cargo',          title: 'Hazmat Cargo Alert',           message: 'Undeclared hazardous materials detected in Container MSCU1234567. Customs notified.',           time: '4 hr ago',   read: true  },
  { id: 6, severity: 'warning',  category: 'Vessel Ops',     title: 'Delayed Arrival',              message: 'MV Container Express is 3 hours behind schedule due to engine maintenance.',                    time: '15 min ago', read: false },
  { id: 7, severity: 'warning',  category: 'Berth Mgmt',     title: 'Berth Scheduling Conflict',    message: 'Double booking detected at Berth A2 for tomorrow 08:00–12:00.',                                 time: '30 min ago', read: false },
  { id: 8, severity: 'warning',  category: 'Cargo',          title: 'Cargo Weight Discrepancy',     message: 'Work order WO-2024-003 shows 8% weight discrepancy. Quality check required.',                   time: '2 hr ago',   read: false },
  { id: 9, severity: 'info',     category: 'System',         title: 'System Maintenance Scheduled', message: 'Planned downtime on Jan 22 02:00–04:00 UTC for database optimization.',                        time: '1 hr ago',   read: true  },
  { id: 10,severity: 'info',     category: 'Vessel Ops',     title: 'Vessel Departure Confirmed',   message: 'MV Pacific Bridge has departed Berth C1. Berth is now available.',                              time: '2 hr ago',   read: true  },
  { id: 11,severity: 'info',     category: 'Cargo',          title: 'Customs Clearance Approved',   message: 'Container batch OOCL-2024-089 cleared customs. Ready for yard delivery.',                       time: '3 hr ago',   read: true  },
  { id: 12,severity: 'info',     category: 'Berth Mgmt',     title: 'AI Optimization Applied',      message: 'Berth assignments for next 48 hours have been optimized. Estimated +12% efficiency gain.',      time: '5 hr ago',   read: true  },
]

export const notifStats = { total: 18, critical: 5, warning: 8, info: 5 }

// ─── Analytics / Chart Data ─────────────────────────────────────
export const vesselTrafficData = [
  { day: 'Mon', arrivals: 18, departures: 16 },
  { day: 'Tue', arrivals: 22, departures: 20 },
  { day: 'Wed', arrivals: 19, departures: 17 },
  { day: 'Thu', arrivals: 25, departures: 23 },
  { day: 'Fri', arrivals: 28, departures: 26 },
  { day: 'Sat', arrivals: 24, departures: 22 },
  { day: 'Sun', arrivals: 21, departures: 19 },
]

export const cargoThroughputData = [
  { month: 'Jul', teus: 8200 },
  { month: 'Aug', teus: 9100 },
  { month: 'Sep', teus: 8700 },
  { month: 'Oct', teus: 9800 },
  { month: 'Nov', teus: 10200 },
  { month: 'Dec', teus: 9600 },
  { month: 'Jan', teus: 11000 },
]

export const delayPredictionData = [
  { name: 'Weather', value: 35, color: '#3b82f6' },
  { name: 'Equipment', value: 25, color: '#ef4444' },
  { name: 'Crew',    value: 20, color: '#eab308' },
  { name: 'Customs', value: 12, color: '#8b5cf6' },
  { name: 'Other',   value: 8,  color: '#6b7280' },
]

export const efficiencyData = [
  { hour: '00:00', efficiency: 72 },
  { hour: '04:00', efficiency: 68 },
  { hour: '08:00', efficiency: 85 },
  { hour: '12:00', efficiency: 91 },
  { hour: '16:00', efficiency: 88 },
  { hour: '20:00', efficiency: 79 },
  { hour: '24:00', efficiency: 74 },
]

// ─── Admin / Users ──────────────────────────────────────────────
export const users = [
  { id: 1, name: 'John Harbor',   email: 'john@port.com',    role: 'Port Manager',     status: 'Active',   lastLogin: 'Just now',   avatar: 'JH' },
  { id: 2, name: 'Sarah Lee',     email: 'sarah@port.com',   role: 'Terminal Operator',status: 'Active',   lastLogin: '1 hr ago',   avatar: 'SL' },
  { id: 3, name: 'Mike Johnson',  email: 'mike@port.com',    role: 'Berth Planner',    status: 'Active',   lastLogin: '2 hr ago',   avatar: 'MJ' },
  { id: 4, name: 'Anna Clark',    email: 'anna@port.com',    role: 'Shipping Agent',   status: 'Active',   lastLogin: '3 hr ago',   avatar: 'AC' },
  { id: 5, name: 'Tom Baker',     email: 'tom@port.com',     role: 'Cargo Inspector',  status: 'Inactive', lastLogin: '2 days ago', avatar: 'TB' },
  { id: 6, name: 'Chris Evans',   email: 'chris@port.com',   role: 'Security Officer', status: 'Active',   lastLogin: '30 min ago', avatar: 'CE' },
]

export const systemConfig = {
  aiOptimization: true,
  autoAlerts: true,
  maintenanceMode: false,
  dataRetentionDays: 90,
  version: '2.4.1',
  lastBackup: '2 hours ago',
  uptime: '99.8%',
}

// ─── Dashboard KPIs ─────────────────────────────────────────────
export const kpis = [
  { label: 'Active Vessels',   value: '24',   sub: '+3 from yesterday', subColor: 'text-status-green', icon: 'fa-ship',                 iconBg: 'bg-blue-100',   iconColor: 'text-blue-600' },
  { label: 'Berth Utilization',value: '87%',  sub: 'Near capacity',     subColor: 'text-status-yellow',icon: 'fa-warehouse',            iconBg: 'bg-yellow-100', iconColor: 'text-yellow-600' },
  { label: 'Cargo Throughput', value: '1,245',sub: 'TEUs today',         subColor: 'text-status-green', icon: 'fa-boxes',                iconBg: 'bg-green-100',  iconColor: 'text-green-600' },
  { label: 'Active Alerts',    value: '3',    sub: '2 high priority',   subColor: 'text-status-red',   icon: 'fa-exclamation-triangle', iconBg: 'bg-red-100',    iconColor: 'text-red-600' },
]

export const recentActivity = [
  { icon: 'fa-ship',  iconBg: 'bg-green-100',  iconColor: 'text-status-green', title: 'Vessel Arrival',      desc: 'MV Baltic Wind docked at Berth B2',          time: '08:45 AM' },
  { icon: 'fa-boxes', iconBg: 'bg-blue-100',   iconColor: 'text-blue-600',     title: 'Cargo Operation',     desc: 'Container discharge completed – 245 TEUs',   time: '07:30 AM' },
  { icon: 'fa-user',  iconBg: 'bg-yellow-100', iconColor: 'text-status-yellow',title: 'Shift Change',        desc: 'Morning crew handover completed',             time: '06:00 AM' },
  { icon: 'fa-check', iconBg: 'bg-green-100',  iconColor: 'text-status-green', title: 'Inspection Complete', desc: 'Safety inspection passed – Berth A1',         time: '05:15 AM' },
]
