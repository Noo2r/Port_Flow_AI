import { Component } from 'react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, info: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, info) {
    this.setState({ info })
    console.error('[ErrorBoundary]', error, info)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, fontFamily: 'monospace', background: '#fff0f0', minHeight: '100vh' }}>
          <h1 style={{ color: 'red' }}>⚠️ App Crashed</h1>
          <h2 style={{ color: '#900' }}>{this.state.error?.message}</h2>
          <pre style={{ background: '#fee', padding: 16, borderRadius: 8, overflowX: 'auto', fontSize: 13 }}>
            {this.state.error?.stack}
          </pre>
          <h3>Component Stack:</h3>
          <pre style={{ background: '#fee', padding: 16, borderRadius: 8, fontSize: 12 }}>
            {this.state.info?.componentStack}
          </pre>
          <button
            onClick={() => this.setState({ hasError: false, error: null, info: null })}
            style={{ marginTop: 16, padding: '8px 16px', background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}
          >
            Try Again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
