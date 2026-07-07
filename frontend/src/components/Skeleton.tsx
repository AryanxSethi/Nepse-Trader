/** Generic shimmer placeholder block for loading states. */
/** Animated placeholder block for loading states. */
export function SkeletonBlock({ width = '100%', height = 20, className = '' }: { width?: string | number; height?: number; className?: string }) {
  return (
    <div
      className={`animate-shimmer rounded-md ${className}`}
      style={{ width, height }}
    />
  )
}

/** Skeleton card with variable number of shimmer lines. */
/** Skeleton card with multiple line placeholders. */
export function SkeletonCard({ lines = 3 }) {
  return (
    <div className="rounded-xl bg-surface-card border border-border p-4 space-y-3">
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonBlock key={i} height={14} width={`${70 + i * 10}%`} />
      ))}
    </div>
  )
}

/** Skeleton table placeholder with configurable rows and columns. */
/** Skeleton table with header and rows of placeholders. */
export function SkeletonTable({ rows = 8, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
      <div className="px-4 py-3 border-b border-border">
        <SkeletonBlock height={12} width={120} />
      </div>
      <div className="p-4 space-y-3">
        <div className="flex gap-4 pb-2 border-b border-border/50">
          <SkeletonBlock height={10} width={60} />
          <SkeletonBlock height={10} width={50} />
          <SkeletonBlock height={10} width={50} />
          <SkeletonBlock height={10} width={50} />
          <SkeletonBlock height={10} width={60} />
        </div>
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex gap-4">
            {Array.from({ length: cols }).map((_, j) => (
              <SkeletonBlock
                key={j}
                height={11}
                width={`${j === 0 ? 70 : j === cols - 1 ? 80 : 55}px`}
              />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

/** Skeleton placeholder matching CompanyInfo layout. */
/** Skeleton for company info detail rows. */
export function SkeletonCompanyInfo({ rows = 12 }: { rows?: number }) {
  return (
    <div className="rounded-xl bg-surface-card border border-border p-4">
      <SkeletonBlock height={14} width={90} className="mb-3" />
      <div className="space-y-1.5">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center justify-between py-1 px-3">
            <SkeletonBlock height={10} width={100} />
            <SkeletonBlock height={10} width={`${60 + (i % 5) * 8}px`} />
          </div>
        ))}
      </div>
    </div>
  )
}

/** Skeleton placeholder mimicking StockChart with toolbar and bars. */
/** Skeleton placeholder for a chart with toolbar and bars. */
export function SkeletonChart({ height = 420 }: { height?: number }) {
  return (
    <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-border">
        <SkeletonBlock height={20} width={48} className="rounded" />
        <SkeletonBlock height={20} width={36} className="rounded" />
        <div className="w-px h-4 bg-border mx-1" />
        <SkeletonBlock height={18} width={48} className="rounded" />
        <SkeletonBlock height={18} width={48} className="rounded" />
        <SkeletonBlock height={18} width={36} className="rounded" />
      </div>
      <div className="p-6 flex items-end justify-around" style={{ height: height - 50 }}>
        {[40, 65, 45, 70, 50, 80, 55, 75, 45, 60, 85, 50, 70, 55, 65].map((h, i) => (
          <div key={i} className="flex flex-col items-center gap-1">
            <SkeletonBlock height={4} width={6} className="rounded-full" />
            <SkeletonBlock height={h} width={6} className="rounded-sm" />
            <SkeletonBlock height={4} width={6} className="rounded-full" />
          </div>
        ))}
      </div>
    </div>
  )
}

/** Horizontal carousel of skeleton index cards. */
/** Skeleton for a horizontal indices carousel. */
export function SkeletonIndicesCarousel({ count = 6 }: { count?: number }) {
  return (
    <div className="flex gap-3 overflow-hidden pb-1">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="shrink-0 w-40 rounded-xl bg-surface-card border border-border p-3">
          <SkeletonBlock height={10} width={`${60 + (i % 3) * 10}%`} />
          <SkeletonBlock height={18} width={70} className="mt-2" />
          <SkeletonBlock height={10} width={50} className="mt-1" />
        </div>
      ))}
    </div>
  )
}
