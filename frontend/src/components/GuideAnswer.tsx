import { motion } from 'framer-motion'
import type { GuideEntry } from '../types'
import { BookIcon, SourceIcon, InfoIcon } from './Icons'

interface Props {
  entry: GuideEntry | null
}

/** Displays a matched guide entry with content and sources. */
export default function GuideAnswer({ entry }: Props) {
  if (!entry) {
    return (
      <div className="rounded-xl bg-surface-card border border-border p-6 text-center">
        <BookIcon size={32} className="text-text-muted/30 mx-auto mb-3" />
        <p className="text-text-muted text-sm">
          No matching guide entry found. Try a different topic or browse the popular topics above.
        </p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-xl bg-surface-card border border-border overflow-hidden"
    >
      <div className="px-5 py-4 border-b border-border">
        <h2 className="text-base font-semibold text-text flex items-center gap-2">
          <BookIcon size={18} className="text-accent" />
          {entry.title}
        </h2>
      </div>

      <div className="px-5 py-4 space-y-3">
        {entry.content.map((paragraph, i) => (
          <motion.p
            key={`p-${i}`}
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.04 }}
            className="text-sm text-text leading-relaxed"
          >
            {paragraph}
          </motion.p>
        ))}
      </div>

      <div className="px-5 py-3 bg-surface-hover border-t border-border">
        <p className="text-xs font-medium text-text-muted mb-1.5 flex items-center gap-1">
          <InfoIcon size={12} /> Sources:
        </p>
        <div className="flex flex-wrap gap-2">
          {entry.sources.map((s) => (
            <a
              key={s.url}
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-accent hover:text-accent-hover underline underline-offset-2 flex items-center gap-1"
            >
              <SourceIcon size={12} />
              {s.name}
            </a>
          ))}
        </div>
      </div>
    </motion.div>
  )
}
