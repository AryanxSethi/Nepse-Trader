import { WarningIcon, CloseIcon } from './Icons'

interface ErrorBannerProps {
  message: string
  onRetry?: () => void
  onDismiss?: () => void
}

export default function ErrorBanner({ message, onRetry, onDismiss }: ErrorBannerProps) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-red/30 bg-red/5 p-4" role="alert">
      <WarningIcon size={18} className="mt-0.5 shrink-0 text-red" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-red">{message}</p>
        {onRetry && (
          <button
            onClick={onRetry}
            className="mt-2 text-xs font-semibold text-accent hover:text-accent-hover transition-colors"
          >
            Try again
          </button>
        )}
      </div>
      {onDismiss && (
        <button onClick={onDismiss} className="shrink-0 text-text-muted hover:text-text transition-colors">
          <CloseIcon size={14} />
        </button>
      )}
    </div>
  )
}
