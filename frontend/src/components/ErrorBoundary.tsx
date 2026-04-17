import { Component } from 'react'
import type { ReactNode, ErrorInfo } from 'react'

interface Props { children: ReactNode }
interface State { error: Error | null }

export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(_error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', info.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, fontFamily: 'var(--font-mono)', fontSize: 'var(--fs-sm)', color: 'var(--neg)' }}>
          <div style={{ marginBottom: 8, fontWeight: 600 }}>Something went wrong</div>
          <pre style={{ color: 'var(--text-3)', whiteSpace: 'pre-wrap' }}>{this.state.error.message}</pre>
          <button className="btn" style={{ marginTop: 16 }} onClick={() => this.setState({ error: null })}>
            Try again
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
