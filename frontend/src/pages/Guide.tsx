import { useState } from 'react'
import QuestionInput from '../components/QuestionInput'
import GuideAnswer from '../components/GuideAnswer'
import { PageTransition } from '../components/Navbar'
import { BookIcon, BrainIcon, CompanyIcon } from '../components/Icons'

const popularTopics = [
  { label: 'Start Trading', query: 'how to start trading' },
  { label: 'Demat Account', query: 'how to open demat account' },
  { label: 'MeroShare', query: 'what is meroshare' },
  { label: 'Trading Fees', query: 'charges and fees' },
  { label: 'All Brokers', query: 'view broker directory' },
]

export default function Guide() {
  const [curatedAnswer, setCuratedAnswer] = useState<{
    entry: { id: string; keywords: string[]; title: string; content: string[]; sources: { name: string; url: string }[] } | null
    llm_answer?: string | null
  } | null>(null)
  const [showCurated, setShowCurated] = useState(false)
  const [showBrokerLink, setShowBrokerLink] = useState(false)

  const handleSearch = async (query: string): Promise<string | null> => {
    setShowCurated(false)
    setShowBrokerLink(false)
    setCuratedAnswer(null)

    const trimmed = query.trim().toLowerCase()
    if (trimmed.includes('broker') || trimmed.includes('near me') || trimmed.includes('broker directory')) {
      setShowBrokerLink(true)
      return 'Broker information is available on the dedicated **Brokers page**. Click the link below to view the full directory with rankings and turnover data.'
    }

    try {
      const res = await fetch('/api/guide/search?q=' + encodeURIComponent(query))
      const data = await res.json()
      if (data?.entry || data?.llm_answer) {
        setCuratedAnswer(data)
        setShowCurated(true)
        return null
      }
      return 'No guide entry found for that query.'
    } catch {
      return 'Guide search unavailable. Please try again later.'
    }
  }

  return (
    <PageTransition>
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-xl font-bold text-text">Market Guide</h1>
          <p className="text-sm text-text-muted">
            Curated guidance for NEPSE investors from official sources (SEBON, CDSC, NEPSE)
          </p>
        </div>

        <QuestionInput
          title="Market Guide"
          welcomeMessage="Ask about NEPSE trading, brokers, and market rules — sourced from official regulators."
          quickQueries={popularTopics}
          onSubmit={handleSearch}
        />

        {showBrokerLink && (
          <div className="animate-fade-in rounded-xl bg-surface-card border border-border p-6 text-center space-y-3">
            <CompanyIcon size={28} className="text-accent mx-auto" />
            <p className="text-sm text-text-muted">
              Browse all 92 NEPSE member brokers with turnover rankings, district coverage, and TMS links.
            </p>
            <a
              href="/brokers"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors"
            >
              Open Brokers Directory
            </a>
          </div>
        )}

        {showCurated && curatedAnswer && (
          <div className="space-y-4 animate-fade-in">
            <GuideAnswer entry={curatedAnswer.entry} />
            {curatedAnswer.llm_answer && !curatedAnswer.entry && (
              <div className="rounded-xl bg-surface-card border border-border overflow-hidden">
                <div className="flex items-center gap-2 px-5 py-3 border-b border-border">
                  <BrainIcon size={16} className="text-accent" />
                  <span className="text-sm font-medium text-text">AI Guide</span>
                </div>
                <div className="px-5 py-4">
                  <p className="text-sm text-text leading-relaxed whitespace-pre-wrap">{curatedAnswer.llm_answer}</p>
                </div>
                <div className="px-5 py-2.5 bg-surface-hover border-t border-border">
                  <p className="text-[10px] text-text-muted/50">
                    Verified against curated guide. Verify important info with official sources.
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {!showBrokerLink && !showCurated && (
          <div className="text-center py-12">
            <BookIcon size={32} className="text-text-muted/30 mx-auto mb-3" />
            <p className="text-sm text-text-muted">
              Ask a question or pick a topic above to get started
            </p>
          </div>
        )}
      </div>
    </PageTransition>
  )
}