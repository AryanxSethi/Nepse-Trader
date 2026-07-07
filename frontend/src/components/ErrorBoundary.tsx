import { Component, type ReactNode, type ErrorInfo } from 'react'
import { WarningIcon } from './Icons'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

/** Catches React errors and displays a fallback UI. */
export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback
      return (
        <div className="rounded-xl bg-red/10 border border-red/20 p-4 flex items-start gap-3 m-4">
          <WarningIcon size={18} className="text-red shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red">Something went wrong</p>
            <p className="text-xs text-red/70 mt-1">{this.state.error?.message || 'An unexpected error occurred'}</p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="text-xs text-accent hover:text-accent-hover mt-2 underline underline-offset-2"
            >
              Try again
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
