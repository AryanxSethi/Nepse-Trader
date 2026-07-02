export function SkeletonBlock({ width = '100%', height = 20, className = '' }) {
  return (
    <div
      className={`animate-shimmer rounded-md ${className}`}
      style={{ width, height }}
    />
  )
}

export function SkeletonCard({ lines = 3 }) {
  return (
    <div className="rounded-xl bg-surface-card border border-border p-4 space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonBlock key={i} height={14} width={`${70 + i * 10}%`} />
      ))}
    </div>
  )
}
