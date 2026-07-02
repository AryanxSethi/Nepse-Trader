import { ReactNode } from 'react'

interface EmptyStateProps {
  icon?: ReactNode
  message: string
  action?: { label: string; onClick: () => void }
}

export default function EmptyState({ icon, message, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
      {icon && <div className="text-text-muted/40">{icon}</div>}
      <p className="text-sm text-text-muted max-w-xs">{message}</p>
      {action && (
        <button
          onClick={action.onClick}
          className="text-xs font-semibold text-accent hover:text-accent-hover transition-colors"
        >
          {action.label}
        </button>
      )}
    </div>
  )
}
