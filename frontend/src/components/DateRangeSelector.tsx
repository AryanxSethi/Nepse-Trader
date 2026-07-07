const presets = [
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: 'MAX', days: 99999 },
]

interface Props {
  selected: number
  onChange: (days: number) => void
}

/** Button group for selecting predefined date ranges (1W, 1M, 3M, etc.). */
export default function DateRangeSelector({ selected, onChange }: Props) {
  return (
    <div className="flex gap-1 flex-wrap">
      {presets.map((p) => (
        <button
          key={p.label}
          onClick={() => onChange(p.days)}
          className={`px-3 py-1 rounded-lg text-xs font-medium transition-all duration-200 ${
            selected === p.days
              ? 'bg-accent text-white shadow-sm'
              : 'bg-surface-card text-text-muted hover:bg-surface-hover hover:text-text border border-border'
          }`}
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}
