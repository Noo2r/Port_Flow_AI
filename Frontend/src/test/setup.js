// Vitest + @testing-library/react global setup
import '@testing-library/jest-dom'

// jsdom doesn't implement ResizeObserver, which recharts' ResponsiveContainer
// requires to mount. Minimal no-op polyfill so any page with a chart can
// render in tests without each test file needing its own workaround.
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver = globalThis.ResizeObserver || ResizeObserverStub
