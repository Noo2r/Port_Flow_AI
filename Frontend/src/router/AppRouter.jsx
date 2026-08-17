import { Suspense, lazy } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import Login from '../pages/Login'

// Route-level code splitting: every page behind the login screen is its own
// chunk, fetched only when the user actually navigates to it. Login stays a
// static import since it's the page almost everyone hits first — no reason
// to pay a network round-trip for it specifically.
const Register         = lazy(() => import('../pages/Register'))
const ResetPassword     = lazy(() => import('../pages/ResetPassword'))
const Dashboard          = lazy(() => import('../pages/Dashboard'))
const VesselMonitoring   = lazy(() => import('../pages/VesselMonitoring'))
const BerthAllocation    = lazy(() => import('../pages/BerthAllocation'))
const CargoWorkforce     = lazy(() => import('../pages/CargoWorkforce'))
const Notifications      = lazy(() => import('../pages/Notifications'))
const AIAnalytics        = lazy(() => import('../pages/AIAnalytics'))
const Predictions        = lazy(() => import('../pages/Predictions'))
const PortOperations      = lazy(() => import('../pages/PortOperations'))
const Administration      = lazy(() => import('../pages/Administration'))
const ModelEvaluation      = lazy(() => import('../pages/ModelEvaluation'))
const CongestionForecast   = lazy(() => import('../pages/CongestionForecast'))
const MaritimeMap          = lazy(() => import('../pages/MaritimeMap'))
const ChatAssistant        = lazy(() => import('../pages/ChatAssistant'))

function RouteFallback() {
  return (
    <div className="flex items-center justify-center h-screen" style={{ background: 'rgb(5, 10, 20)' }}>
      <div className="flex flex-col items-center gap-3">
        <i className="fa-solid fa-anchor text-3xl text-blue-400 animate-pulse" />
        <p className="text-sm text-gray-400">Loading…</p>
      </div>
    </div>
  )
}

function ProtectedRoute({ children }) {
  const { user } = useAuth()
  if (!localStorage.getItem('access_token') && !user) {
    return <Navigate to="/login" replace />
  }
  return children
}

const TECHNICAL_ROLES = new Set(['admin', 'port_manager', 'analyst'])

function TechnicalRoute({ children }) {
  const { user } = useAuth()
  const token = localStorage.getItem('access_token')
  const cachedUser = (() => {
    try { return JSON.parse(localStorage.getItem('user')) } catch { return null }
  })()
  const effectiveUser = user || cachedUser
  if (!token && !effectiveUser) return <Navigate to="/login" replace />
  if (effectiveUser && !TECHNICAL_ROLES.has(effectiveUser.role)) return <Navigate to="/dashboard" replace />
  return children
}

function AdminRoute({ children }) {
  const { user } = useAuth()
  const token = localStorage.getItem('access_token')
  // Use cached user from localStorage to avoid flash on page refresh
  const cachedUser = (() => {
    try { return JSON.parse(localStorage.getItem('user')) } catch { return null }
  })()
  const effectiveUser = user || cachedUser
  if (!token && !effectiveUser) return <Navigate to="/login" replace />
  if (effectiveUser && effectiveUser.role !== 'admin') return <Navigate to="/dashboard" replace />
  return children
}

export default function AppRouter() {
  return (
    <BrowserRouter>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/login"          element={<Login />} />
          <Route path="/register"       element={<Register />} />
          <Route path="/reset-password" element={<ResetPassword />} />

          <Route path="/dashboard"     element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/vessels"       element={<ProtectedRoute><VesselMonitoring /></ProtectedRoute>} />
          <Route path="/berth"         element={<ProtectedRoute><BerthAllocation /></ProtectedRoute>} />
          <Route path="/cargo"         element={<ProtectedRoute><CargoWorkforce /></ProtectedRoute>} />
          <Route path="/notifications" element={<ProtectedRoute><Notifications /></ProtectedRoute>} />
          <Route path="/analytics"     element={<TechnicalRoute><AIAnalytics /></TechnicalRoute>} />
          <Route path="/predictions"   element={<ProtectedRoute><Predictions /></ProtectedRoute>} />
          <Route path="/evaluation"    element={<TechnicalRoute><ModelEvaluation /></TechnicalRoute>} />
          <Route path="/port-ops"      element={<ProtectedRoute><PortOperations /></ProtectedRoute>} />
          <Route path="/congestion"    element={<ProtectedRoute><CongestionForecast /></ProtectedRoute>} />
          <Route path="/maritime-map"  element={<ProtectedRoute><MaritimeMap /></ProtectedRoute>} />
          <Route path="/chat"          element={<ProtectedRoute><ChatAssistant /></ProtectedRoute>} />
          <Route path="/admin"         element={<AdminRoute><Administration /></AdminRoute>} />

          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
