import { Component, ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

/**
 * Catches render-time errors in any route so a single broken page degrades to a
 * recoverable message instead of a blank white screen.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  reset = () => this.setState({ error: null })

  render() {
    if (this.state.error) {
      return (
        <div className="card mx-auto mt-10 max-w-lg text-center">
          <AlertTriangle size={40} className="mx-auto text-amber-400" />
          <h2 className="mt-4 text-lg font-semibold text-gray-100">Something went wrong</h2>
          <p className="mt-1 text-sm text-gray-400">
            This page hit an unexpected error. You can retry or navigate elsewhere.
          </p>
          <pre className="mt-3 overflow-x-auto rounded bg-gray-900 p-3 text-left text-xs text-red-400">
            {this.state.error.message}
          </pre>
          <div className="mt-4 flex justify-center gap-3">
            <button onClick={this.reset} className="btn-secondary">Retry</button>
            <a href="/" className="btn-primary">Go home</a>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
