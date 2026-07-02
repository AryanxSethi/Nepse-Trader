import { useState, useEffect } from 'react'

interface SectorFilterProps {
  onSelect: (sector: string | null) => void
  selected: string | null
}

const SECTOR_GROUPS: Record<string, string[]> = {
  'Banking & Finance': ['Commercial Banks', 'Development Bank Limited', 'Finance', 'Microfinance'],
  'Insurance': ['Life Insurance', 'Non-Life Insurance'],
  'Energy': ['Hydro Power'],
  'Manufacturing': ['Manufacturing And Processing'],
  'Services': ['Hotels And Tourism', 'Tradings', 'Investment'],
  'Funds': ['Mutual Fund', 'Corporate Debenture', 'Government Bond'],
  'Other': ['Others', 'Promotor Share'],
}

export default function SectorFilter({ onSelect, selected }: SectorFilterProps) {
  const [sectors, setSectors] = useState<string[]>([])
  const [expandedGroup, setExpandedGroup] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/sectors')
      .then((r) => r.json())
      .then((d) => setSectors(d.sectors || []))
      .catch(() => setSectors([]))
  }, [])

  const sectorsInGroup = (group: string) => SECTOR_GROUPS[group] || []
  const isGroupActive = (group: string) => selected && sectorsInGroup(group).includes(selected)

  return (
    <div className="space-y-1.5">
      <p className="text-[10px] text-text-muted font-medium uppercase tracking-wider">Filter by Sector</p>
      <div className="flex flex-wrap gap-1.5">
        <button
          onClick={() => { onSelect(null); setExpandedGroup(null) }}
          className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
            !selected
              ? 'bg-accent/15 text-accent border-accent/30'
              : 'bg-surface-card text-text-muted border-border hover:border-text-muted/30'
          }`}
        >
          All
        </button>
        {Object.entries(SECTOR_GROUPS).map(([group, _sectors]) => (
          <div key={group} className="relative">
            <button
              onClick={() => setExpandedGroup(expandedGroup === group ? null : group)}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
                isGroupActive(group)
                  ? 'bg-accent/15 text-accent border-accent/30'
                  : 'bg-surface-card text-text-muted border-border hover:border-text-muted/30'
              }`}
            >
              {group}
            </button>
            {expandedGroup === group && (
              <div className="absolute top-full left-0 mt-1 z-20 bg-surface-card border border-border rounded-lg shadow-xl p-1.5 min-w-[180px] space-y-0.5">
                {_sectors.map((s) => (
                  <button
                    key={s}
                    onClick={() => { onSelect(selected === s ? null : s); setExpandedGroup(null) }}
                    className={`w-full text-left px-2.5 py-1.5 rounded text-[11px] font-medium transition-colors ${
                      selected === s
                        ? 'bg-accent/15 text-accent'
                        : 'text-text-muted hover:bg-surface-hover hover:text-text'
                    }`}
                  >
                    {s}
                    <span className="float-right text-text-muted/40 text-[10px]">
                      {sectors.filter((sc) => sc === s).length > 0 ? '\u2713' : ''}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
