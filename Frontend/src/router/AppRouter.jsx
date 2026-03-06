import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Login         from '../pages/Login'
import Dashboard     from '../pages/Dashboard'
import VesselMonitoring from '../pages/VesselMonitoring'
import BerthAllocation  from '../pages/BerthAllocation'
import CargoWorkforce   from '../pages/CargoWorkforce'
import Notifications    from '../pages/Notifications'
import AIAnalytics      from '../pages/AIAnalytics'
import Administration   from '../pages/Administration'

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login"         element={<Login />} />
        <Route path="/dashboard"     element={<Dashboard />} />
        <Route path="/vessels"       element={<VesselMonitoring />} />
        <Route path="/berth"         element={<BerthAllocation />} />
        <Route path="/cargo"         element={<CargoWorkforce />} />
        <Route path="/notifications" element={<Notifications />} />
        <Route path="/analytics"     element={<AIAnalytics />} />
        <Route path="/admin"         element={<Administration />} />
        <Route path="*"              element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
