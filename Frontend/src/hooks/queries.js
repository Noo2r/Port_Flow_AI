/**
 * Shared frontend data layer (React Query).
 *
 * Before this module existed, every page called services/api.js directly
 * inside its own useApi()/useEffect, so navigating Dashboard -> AIAnalytics
 * -> back to Dashboard re-fetched analyticsApi.metrics() three times even
 * though nothing changed, and two pages open in different tabs (or just two
 * components on the same page) had no way to share a single in-flight
 * request. These hooks give every page that needs the same resource the
 * same cached, deduplicated query — call it from N components, it fires
 * one network request.
 *
 * Query key convention: [resource, ...params] — e.g. ['vessels', 0, 500].
 * Two call sites with the same key share the same cache entry, so
 * Dashboard's berthsApi.list(0, 120) and BerthAllocation's
 * berthsApi.list(0, 500) are intentionally kept as separate keys (different
 * params = legitimately different data), while two components both calling
 * useAnalyticsMetrics() collapse into one request.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api, {
  analyticsApi, authApi, berthsApi, congestionApi, etaApi, notificationsApi,
  portOpsApi, portsApi, predictionsApi, vesselsApi, visitsApi, workOrdersApi,
} from '../services/api'

// ── Vessels ───────────────────────────────────────────────────────────────────
export function useVessels(skip = 0, limit = 100) {
  return useQuery({
    queryKey: ['vessels', skip, limit],
    queryFn: () => vesselsApi.list(skip, limit),
  })
}

export function useCreateVessel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => vesselsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vessels'] }),
  })
}

export function useUpdateVessel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => vesselsApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vessels'] }),
  })
}

export function useDeleteVessel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => vesselsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['vessels'] }),
  })
}

// ── Ports ─────────────────────────────────────────────────────────────────────
export function usePorts(skip = 0, limit = 4000) {
  return useQuery({
    queryKey: ['ports', skip, limit],
    queryFn: () => portsApi.list(skip, limit),
  })
}

// ── Berths ────────────────────────────────────────────────────────────────────
export function useBerths(skip = 0, limit = 100) {
  return useQuery({
    queryKey: ['berths', skip, limit],
    queryFn: () => berthsApi.list(skip, limit),
  })
}

export function useUpdateBerth() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => berthsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['berths'] })
      qc.invalidateQueries({ queryKey: ['portOps'] })
      qc.invalidateQueries({ queryKey: ['analytics'] })
    },
  })
}

// ── Visits ────────────────────────────────────────────────────────────────────
function visitsKey(params) {
  // Stable key regardless of property insertion order.
  return ['visits', JSON.stringify(Object.entries(params).sort())]
}

export function useVisits(params = {}) {
  return useQuery({
    queryKey: visitsKey(params),
    queryFn: () => visitsApi.list(params),
  })
}

export function useCreateVisit() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => visitsApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['visits'] })
      qc.invalidateQueries({ queryKey: ['berths'] })
      qc.invalidateQueries({ queryKey: ['analytics'] })
      qc.invalidateQueries({ queryKey: ['portOps'] })
    },
  })
}

export function useUpdateVisit() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => visitsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['visits'] })
      qc.invalidateQueries({ queryKey: ['berths'] })
      qc.invalidateQueries({ queryKey: ['analytics'] })
      qc.invalidateQueries({ queryKey: ['portOps'] })
    },
  })
}

export function useDeleteVisit() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => visitsApi.delete(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['visits'] })
      qc.invalidateQueries({ queryKey: ['berths'] })
      qc.invalidateQueries({ queryKey: ['analytics'] })
      qc.invalidateQueries({ queryKey: ['portOps'] })
    },
  })
}

// ── Analytics ─────────────────────────────────────────────────────────────────
export function useAnalyticsMetrics() {
  return useQuery({
    queryKey: ['analytics', 'metrics'],
    queryFn: () => analyticsApi.metrics(),
  })
}

export function useAnalyticsCharts(days = 14) {
  return useQuery({
    queryKey: ['analytics', 'charts', days],
    queryFn: () => analyticsApi.charts(days),
  })
}

// ── Port Operations (Stage-2 Berth Optimizer) ─────────────────────────────────
export function usePortKpis() {
  return useQuery({
    queryKey: ['portOps', 'kpis'],
    queryFn: () => portOpsApi.portKpis(),
  })
}

export function useBerthStatus() {
  return useQuery({
    queryKey: ['portOps', 'berthStatus'],
    queryFn: () => portOpsApi.berthStatus(),
  })
}

export function usePortAllocations() {
  return useQuery({
    queryKey: ['portOps', 'allocations'],
    queryFn: () => portOpsApi.allocations(),
  })
}

export function usePortOpsHealth() {
  return useQuery({
    queryKey: ['portOps', 'health'],
    queryFn: () => portOpsApi.health(),
  })
}

// ── Predictions (Stage 1 history) ─────────────────────────────────────────────
function predictionsKey(params) {
  return ['predictions', JSON.stringify(Object.entries(params).sort())]
}

export function usePredictions(params = {}) {
  return useQuery({
    queryKey: predictionsKey(params),
    queryFn: () => predictionsApi.list(params),
  })
}

// ── ETA model (Stage 1) ────────────────────────────────────────────────────────
export function useEtaModelInfo() {
  return useQuery({
    queryKey: ['eta', 'modelInfo'],
    queryFn: () => etaApi.modelInfo(),
  })
}

export function useEtaEvaluation() {
  return useQuery({
    queryKey: ['eta', 'evaluation'],
    queryFn: () => etaApi.evaluation(),
  })
}

// Combined ETA + Berth prediction (Stage 1 -> Stage 2). Writes a Visit row and
// a Berth status change server-side, so it invalidates the same downstream
// queries as useCreateVisit — every page reading vessel/berth/KPI state must
// see the new allocation immediately, not just the Predictions page.
export function usePredictEtaAndBerth() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (payload) => etaApi.predictWithBerth(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['predictions'] })
      qc.invalidateQueries({ queryKey: ['visits'] })
      qc.invalidateQueries({ queryKey: ['berths'] })
      qc.invalidateQueries({ queryKey: ['analytics'] })
      qc.invalidateQueries({ queryKey: ['portOps'] })
    },
  })
}

export function useSetActiveEtaModel() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (modelName) => etaApi.setActiveModel(modelName),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['eta', 'modelInfo'] }),
  })
}

// ── Congestion model (Stage 3) ─────────────────────────────────────────────────
export function useCongestionModelInfo() {
  return useQuery({
    queryKey: ['congestion', 'modelInfo'],
    queryFn: () => congestionApi.modelInfo(),
  })
}

export function useCongestionEvaluation() {
  return useQuery({
    queryKey: ['congestion', 'evaluation'],
    queryFn: () => congestionApi.evaluation(),
  })
}

export function useCongestionPortOverview() {
  return useQuery({
    queryKey: ['congestion', 'portOverview'],
    queryFn: () => congestionApi.portOverview(),
  })
}

// Congestion prediction is a pure stateless inference call (no DB writes),
// so unlike usePredictEtaAndBerth it invalidates nothing else.
export function useCongestionPredict() {
  return useMutation({
    mutationFn: (payload) => congestionApi.predict(payload),
  })
}

// ── Work Orders ───────────────────────────────────────────────────────────────
function workOrdersKey(params) {
  return ['workOrders', JSON.stringify(Object.entries(params).sort())]
}

export function useWorkOrders(params = {}) {
  return useQuery({
    queryKey: workOrdersKey(params),
    queryFn: () => workOrdersApi.list(params),
  })
}

export function useCreateWorkOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => workOrdersApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workOrders'] }),
  })
}

export function useUpdateWorkOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => workOrdersApi.update(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workOrders'] }),
  })
}

export function useDeleteWorkOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id) => workOrdersApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workOrders'] }),
  })
}

// ── Notifications ─────────────────────────────────────────────────────────────
export function useNotifications() {
  return useQuery({
    queryKey: ['notifications'],
    queryFn: () => notificationsApi.list(),
  })
}

// ── Admin: Users ──────────────────────────────────────────────────────────────
export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => api.get('/api/v1/auth/users'),
  })
}

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data) => authApi.adminCreateUser(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}

export function useUpdateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }) => api.patch(`/api/v1/auth/users/${id}`, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })
}
