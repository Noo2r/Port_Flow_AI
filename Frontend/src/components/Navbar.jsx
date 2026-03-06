import { useNavigate } from 'react-router-dom'

export default function Navbar({ title, subtitle, children }) {
  const navigate = useNavigate()
  return (
    <div className="bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{title}</h1>
          {subtitle && <p className="text-gray-600 text-sm">{subtitle}</p>}
        </div>
        <div className="flex items-center space-x-4">
          {children}
          <button
            onClick={() => navigate('/notifications')}
            className="relative"
          >
            <i className="fa-solid fa-bell text-gray-400 text-lg" />
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-status-red rounded-full" />
          </button>
          <div className="text-right">
            <p className="text-sm font-medium text-gray-900">Last Updated</p>
            <p className="text-xs text-gray-500">2 minutes ago</p>
          </div>
        </div>
      </div>
    </div>
  )
}
