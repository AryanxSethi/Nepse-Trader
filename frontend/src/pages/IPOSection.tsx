import { useState, useEffect, useCallback, useRef, type JSX } from 'react'
import { PageTransition } from '../components/Navbar'
import ErrorBanner from '../components/ErrorBanner'
import RefreshIndicator from '../components/RefreshIndicator'
import { DocumentIcon, InfoIcon, SourceIcon, WarningIcon, ChevronLeftIcon, ChevronRightIcon } from '../components/Icons'
import { SkeletonBlock } from '../components/Skeleton'

interface IPOItem {
  company: string
  symbol: string
  issue_size: string
  open_date: string
  open_date_bs: string
  close_date: string
  close_date_bs: string
  price_range: string
  status: string
  share_type: string
  share_registrar: string
  rating: string
  sector: string
  min_units: string
  max_units: string
  price_per_unit: string
  ipo_id?: number
}

interface Pager {
  pageNo: number
  itemsPerPage: number
  totalNextPages: number
  totalPages: number
}

const guideSections = [
  {
    title: 'How to Apply for an IPO (C-ASBA)',
    steps: [
      'Log in to your Mero Share account (https://meroshare.cdsc.com.np)',
      'Go to "My Application" → "Apply for IPO/FPO"',
      'Select the company from the list of open issues',
      'Enter the number of shares (min 10, max depends on issue)',
      'Select your bank account for C-ASBA (automatic block of funds)',
      'Confirm and submit. Funds will be blocked until allotment.',
    ],
    note: 'C-ASBA (Blocking Amount Facility) automatically blocks the application amount in your bank account. No manual payment needed.',
  },
  {
    title: 'How to Check IPO Allotment',
    steps: [
      'Log in to Mero Share (https://meroshare.cdsc.com.np)',
      'Go to "My Application" → "View My Application"',
      'If shares are allotted, they will appear in your Demat account',
      'You can also check via bank SMS service or CDSC website',
    ],
    note: 'Allotment is usually published within 7-30 days after the close date.',
  },
  {
    title: 'How to Sell IPO Shares After Listing',
    steps: [
      'IPO shares are credited to your Demat account before listing',
      'On the listing day, log in to your trading platform',
      'Place a sell order at your desired price',
      'Funds are credited after T+2 settlement',
    ],
    note: 'Listing typically happens 7-15 days after allotment. Prices can be volatile on listing day.',
  },
  {
    title: 'IPO vs FPO vs Rights Issue',
    steps: [
      'IPO (Initial Public Offering): Company lists on NEPSE for the first time. General public can apply.',
      'FPO (Further Public Offering): Already-listed company issues more shares to the public.',
      'Rights Issue: Existing shareholders get priority to buy new shares at a discount.',
      'Bonus Shares: Free shares given to existing shareholders from retained earnings.',
    ],
    note: 'Each type has different rules, timelines, and application processes in Mero Share.',
  },
]

function DateCell({ bs, ad }: { bs: string; ad: string }) {
  if (!bs && !ad) return <span className="text-text-muted">-</span>
  return (
    <span className="whitespace-nowrap leading-tight">
      <span className="text-text font-medium">{bs}</span>
      <span className="text-text-muted ml-0.5 text-[10px]">BS</span>
      {ad && <span className="text-text-muted text-[10px] opacity-60 ml-0.5">{ad}</span>}
    </span>
  )
}

function statusBadge(status: string): JSX.Element | null {
  switch (status) {
    case 'open': return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-green/15 text-green">Open</span>
    case 'upcoming': return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-yellow/15 text-yellow">Upcoming</span>
    case 'closed': return <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-red/10 text-text-muted">Closed</span>
    default: return null
  }
}

const PAGE_SIZE = 20

export default function IPOSection() {
  const [activeGuide, setActiveGuide] = useState<number | null>(null)
  const [items, setItems] = useState<IPOItem[]>([])
  const [pager, setPager] = useState<Pager | null>(null)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState('')
  const [fetchedAt, setFetchedAt] = useState<string | null>(null)
  const tableWrapperRef = useRef<HTMLDivElement>(null)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const fetchPage = useCallback(async (p: number) => {
    setLoading(true)
    setFetchError('')
    const controller = new AbortController()
    try {
      const r = await fetch(`/api/ipos?page=${p}&per_page=${PAGE_SIZE}`, { signal: controller.signal })
      if (!r.ok) throw new Error('Failed to load IPO data')
      const d = await r.json()
      setItems(d.data || [])
      setPager(d.pager || null)
      setFetchedAt(new Date().toISOString())
    } catch (e: unknown) {
      if (e instanceof Error && e.name !== 'AbortError') {
        setFetchError('Could not load IPO data.')
        setItems([])
        setPager(null)
      }
    } finally {
      setLoading(false)
    }
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const cleanup = fetchPage(page)
    return () => { cleanup.then(fn => fn?.()) }
  }, [page, fetchPage])

  const checkScroll = useCallback(() => {
    const el = tableWrapperRef.current
    if (el) {
      setCanScrollRight(el.scrollWidth > el.clientWidth && el.scrollLeft < el.scrollWidth - el.clientWidth - 5)
    }
  }, [])

  useEffect(() => {
    const el = tableWrapperRef.current
    if (!el) return
    checkScroll()
    el.addEventListener('scroll', checkScroll)
    const ro = new ResizeObserver(checkScroll)
    ro.observe(el)
    return () => {
      el.removeEventListener('scroll', checkScroll)
      ro.disconnect()
    }
  }, [items, checkScroll])

  const totalPages = pager?.totalPages ?? 1
  const pageNo = pager?.pageNo ?? 1

  const pageRange = (): (number | 'ellipsis')[] => {
    const range: (number | 'ellipsis')[] = []
    if (totalPages <= 7) {
      for (let i = 1; i <= totalPages; i++) range.push(i)
      return range
    }
    range.push(1)
    if (pageNo > 3) range.push('ellipsis')
    const start = Math.max(2, pageNo - 1)
    const end = Math.min(totalPages - 1, pageNo + 1)
    for (let i = start; i <= end; i++) range.push(i)
    if (pageNo < totalPages - 2) range.push('ellipsis')
    range.push(totalPages)
    return range
  }

  return (
    <PageTransition>
      <div className="max-w-full mx-auto px-4 py-6 space-y-6">
        <div className="flex items-center gap-3">
          <DocumentIcon size={22} className="text-accent" />
          <h1 className="text-2xl font-bold text-text">IPO / FPO</h1>
        </div>

        {fetchError && (
          <ErrorBanner message={fetchError} onRetry={() => fetchPage(page)} onDismiss={() => setFetchError('')} />
        )}

        <a
          href="https://iporesult.cdsc.com.np/"
          target="_blank"
          rel="noopener noreferrer"
          className="block rounded-xl bg-accent/10 border border-accent/25 p-4 hover:bg-accent/15 transition-colors group"
        >
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold text-text">Check IPO Allotment Result</p>
              <p className="text-xs text-text-muted mt-0.5">
                Visit the official CDSC portal to check if you got allotted
              </p>
              <ul className="text-xs text-text-muted mt-1.5 space-y-0.5 list-disc list-inside">
                <li>Select the company name</li>
                <li>Enter your 16-digit BOID (Demat number)</li>
                <li>Enter captcha and click View Result</li>
              </ul>
            </div>
            <span className="text-accent text-sm font-semibold group-hover:translate-x-0.5 transition-transform">
              Open &rarr;
            </span>
          </div>
        </a>

        <div className="rounded-xl bg-surface-card border border-border p-3 md:p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-semibold text-text">All IPO Issues</h2>
              <RefreshIndicator fetchedAt={fetchedAt} />
            </div>
            {pager && (
              <span className="text-[11px] text-text-muted">
                Page {pageNo} of {totalPages}
              </span>
            )}
          </div>

          {loading ? (
            <SkeletonBlock height={120} />
          ) : items.length === 0 ? (
            <p className="text-xs text-text-muted py-4 text-center">No IPO data available.</p>
          ) : (
            <>
              <div className="relative">
                <div
                  ref={tableWrapperRef}
                  className="overflow-x-auto scrollbar-thin"
                  style={{ scrollbarWidth: 'thin' }}
                >
                  <table className="w-full text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-border text-text-muted">
                        <th className="sticky left-0 z-10 bg-surface-card text-left py-2.5 pr-2 font-medium whitespace-nowrap min-w-[140px] shadow-[2px_0_4px_-2px_rgba(0,0,0,0.08)]">Company</th>
                        <th className="sticky left-[140px] z-10 bg-surface-card text-left py-2.5 pr-2 font-medium whitespace-nowrap min-w-[60px] shadow-[2px_0_4px_-2px_rgba(0,0,0,0.08)]">Sym</th>
                        <th className="text-left py-2.5 pr-2 font-medium whitespace-nowrap min-w-[55px]">Type</th>
                        <th className="text-left py-2.5 pr-2 font-medium whitespace-nowrap min-w-[85px]">Issue</th>
                        <th className="text-center py-2.5 pr-2 font-medium whitespace-nowrap min-w-[120px]">Open</th>
                        <th className="text-center py-2.5 pr-2 font-medium whitespace-nowrap min-w-[120px]">Close</th>
                        <th className="text-left py-2.5 pr-2 font-medium whitespace-nowrap min-w-[60px]">Price</th>
                        <th className="text-left py-2.5 pr-2 font-medium whitespace-nowrap min-w-[80px]">Rating</th>
                        <th className="text-left py-2.5 pr-2 font-medium whitespace-nowrap min-w-[130px]">Manager</th>
                        <th className="text-right py-2.5 font-medium whitespace-nowrap min-w-[60px]">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((ipo, i) => (
                        <tr key={ipo.ipo_id ?? ipo.symbol + i} className="border-b border-border/50 hover:bg-surface-hover/50 transition-colors">
                          <td className="sticky left-0 z-10 bg-surface-card py-2.5 pr-2 text-text font-medium whitespace-nowrap truncate max-w-[140px] shadow-[2px_0_4px_-2px_rgba(0,0,0,0.08)]" title={ipo.company}>{ipo.company}</td>
                          <td className="sticky left-[140px] z-10 bg-surface-card py-2.5 pr-2 text-text-muted font-mono-nums whitespace-nowrap shadow-[2px_0_4px_-2px_rgba(0,0,0,0.08)]">{ipo.symbol || '-'}</td>
                          <td className="py-2.5 pr-2 text-text capitalize whitespace-nowrap">{ipo.share_type || '-'}</td>
                          <td className="py-2.5 pr-2 text-text font-mono-nums whitespace-nowrap">{ipo.issue_size || '-'}</td>
                          <td className="py-2.5 pr-2 text-center whitespace-nowrap">
                            <DateCell bs={ipo.open_date_bs} ad={ipo.open_date} />
                          </td>
                          <td className="py-2.5 pr-2 text-center whitespace-nowrap">
                            <DateCell bs={ipo.close_date_bs} ad={ipo.close_date} />
                          </td>
                          <td className="py-2.5 pr-2 text-text font-mono-nums whitespace-nowrap">{ipo.price_range}</td>
                          <td className="py-2.5 pr-2 text-text-muted text-[11px] truncate max-w-[80px] whitespace-nowrap" title={ipo.rating}>{ipo.rating || '-'}</td>
                          <td className="py-2.5 pr-2 text-text-muted text-[11px] truncate max-w-[130px] whitespace-nowrap" title={ipo.share_registrar}>{ipo.share_registrar || '-'}</td>
                          <td className="py-2.5 text-right whitespace-nowrap">{statusBadge(ipo.status)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {canScrollRight && (
                  <div className="pointer-events-none absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-black/5 to-transparent" />
                )}
              </div>

              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-1 mt-4">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={pageNo <= 1}
                    className="p-1.5 rounded-md text-text-muted hover:text-text hover:bg-surface-hover disabled:opacity-30 disabled:pointer-events-none transition-colors"
                    aria-label="Previous page"
                  >
                    <ChevronLeftIcon size={16} />
                  </button>

                  {pageRange().map((p, i) =>
                    p === 'ellipsis' ? (
                      <span key={`e${i}`} className="px-1 text-text-muted text-xs">...</span>
                    ) : (
                      <button
                        key={p}
                        onClick={() => setPage(p)}
                        className={`min-w-[28px] h-7 rounded-md text-xs font-medium transition-colors ${
                          p === pageNo
                            ? 'bg-accent text-white'
                            : 'text-text-muted hover:text-text hover:bg-surface-hover'
                        }`}
                      >
                        {p}
                      </button>
                    )
                  )}

                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={pageNo >= totalPages}
                    className="p-1.5 rounded-md text-text-muted hover:text-text hover:bg-surface-hover disabled:opacity-30 disabled:pointer-events-none transition-colors"
                    aria-label="Next page"
                  >
                    <ChevronRightIcon size={16} />
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        <div className="rounded-xl bg-surface-card border border-border p-4">
          <h2 className="text-sm font-semibold text-text mb-3 flex items-center gap-1.5">
            <InfoIcon size={14} className="text-accent" />
            IPO Guides
          </h2>
          <div className="space-y-2">
            {guideSections.map((section, i) => (
              <div key={i} className="border border-border rounded-lg overflow-hidden">
                <button
                  onClick={() => setActiveGuide(activeGuide === i ? null : i)}
                  className="w-full flex items-center justify-between px-3 py-2.5 text-left text-xs font-medium text-text hover:bg-surface-hover transition-colors"
                >
                  {section.title}
                  <span className={`text-text-muted transition-transform duration-200 ${activeGuide === i ? 'rotate-180' : ''}`}>
                    ▼
                  </span>
                </button>
                {activeGuide === i && (
                  <div className="px-3 pb-3 space-y-2 animate-fade-in">
                    <ol className="list-decimal list-inside text-xs text-text-muted space-y-1">
                      {section.steps.map((step, j) => (
                        <li key={j}>{step}</li>
                      ))}
                    </ol>
                    {section.note && (
                      <div className="flex items-start gap-1.5 mt-2 p-2 rounded-lg bg-accent/5">
                        <SourceIcon size={12} className="text-accent shrink-0 mt-0.5" />
                        <p className="text-[11px] text-text-muted">{section.note}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </PageTransition>
  )
}
