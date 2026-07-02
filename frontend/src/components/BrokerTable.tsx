import { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import type { Broker } from '../types'
import { SourceIcon, SearchIcon } from './Icons'

export default function BrokerTable({ initialQuery = '' }: { initialQuery?: string }) {
  const [brokers, setBrokers] = useState<Broker[]>([])
  const [query, setQuery] = useState(initialQuery)
  const [loading, setLoading] = useState(true)

  const fetchBrokers = useCallback(async (search: string) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/guide/brokers?search=${encodeURIComponent(search)}`)
      const data = await res.json()
      setBrokers(data.brokers || [])
    } catch {
      setBrokers([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => fetchBrokers(query), 200)
    return () => clearTimeout(t)
  }, [query, fetchBrokers])

  return (
    <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
      <div className="p-4 border-b border-border">
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by name, location, or broker number..."
            className="w-full bg-surface-hover text-text text-sm rounded-lg px-4 py-2.5 pl-9 border border-border outline-none focus:border-accent/50 transition-colors placeholder-text-muted/40"
          />
          <SearchIcon size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-muted pointer-events-none" />
        </div>
      </div>

      {loading ? (
        <div className="p-4 space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="animate-shimmer h-10 rounded" style={{ width: `${90 - i * 5}%` }} />
          ))}
        </div>
      ) : (
        <div className="overflow-x-auto max-h-96 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-surface-card">
              <tr className="border-b border-border text-text-muted text-xs">
                <th className="text-left px-4 py-2.5 font-medium">#</th>
                <th className="text-left px-4 py-2.5 font-medium">Broker Name</th>
                <th className="text-left px-4 py-2.5 font-medium">Address</th>
                <th className="text-left px-4 py-2.5 font-medium">Phone</th>
              </tr>
            </thead>
            <tbody>
              {brokers.map((b, i) => (
                <motion.tr
                  key={b.code}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.005 }}
                  className="border-b border-border/50 hover:bg-surface-hover transition-colors"
                >
                  <td className="px-4 py-2.5 text-text-muted text-xs">{b.code}</td>
                  <td className="px-4 py-2.5 text-text font-medium">{b.name}</td>
                  <td className="px-4 py-2.5 text-text-muted text-xs">{b.address}</td>
                  <td className="px-4 py-2.5 text-text-muted text-xs">{b.phone}</td>
                </motion.tr>
              ))}
              {brokers.length === 0 && (
                <tr>
                  <td colSpan={4} className="text-center text-text-muted text-sm py-8">
                    No brokers found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <div className="px-4 py-2.5 bg-surface-hover border-t border-border">
        <p className="text-[10px] text-text-muted flex items-center gap-1">
          <SourceIcon size={10} /> Source: SEBON Official List — sebon.gov.np
        </p>
      </div>
    </div>
  )
}
