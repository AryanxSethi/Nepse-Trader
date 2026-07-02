import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useTheme } from '../context/ThemeContext'
import { HomeIcon, ChartIcon, SignalIcon, BacktestIcon, BookIcon, DocumentIcon, CompanyIcon, SunIcon, MoonIcon, TrendingUpIcon, WalletIcon } from './Icons'
import MarketStatusBanner from './MarketStatusBanner'

const links = [
  { to: '/', label: 'Overview', icon: HomeIcon },
  { to: '/market', label: 'Market', icon: TrendingUpIcon },
  { to: '/trade', label: 'Trade', icon: ChartIcon },
  { to: '/signals', label: 'Signals', icon: SignalIcon },
  { to: '/brokers', label: 'Brokers', icon: CompanyIcon },
  { to: '/backtest', label: 'Backtest', icon: BacktestIcon },
  { to: '/guide', label: 'Guide', icon: BookIcon },
  { to: '/ipo', label: 'IPO', icon: DocumentIcon },
  { to: '/portfolio', label: 'Portfolio', icon: WalletIcon },
]

export default function Navbar() {
  const { theme, toggle } = useTheme()

  return (
    <>
      <nav className="flex items-center justify-between px-4 sm:px-6 py-3 border-b border-border bg-surface-card/80 backdrop-blur-sm sticky top-0 z-50">
      <div className="flex items-center gap-2">
        <span className="text-lg font-bold text-accent">NEPSE</span>
        <span className="text-xs text-text-muted hidden sm:inline font-medium">Trader</span>
      </div>
      <div className="flex items-center gap-1">
        {links.map((link) => {
          const Icon = link.icon
          return (
            <NavLink
              key={link.to}
              to={link.to}
              end={link.to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs sm:text-sm transition-all duration-200 ${
                  isActive
                    ? 'bg-accent/15 text-accent font-semibold'
                    : 'text-text-muted hover:text-text hover:bg-surface-hover'
                }`
              }
            >
              <Icon size={14} />
              <span className="hidden sm:inline">{link.label}</span>
            </NavLink>
          )
        })}
        <div className="w-px h-5 bg-border mx-1" />
        <button
          onClick={toggle}
          className="p-2 rounded-lg text-text-muted hover:text-text hover:bg-surface-hover transition-colors active:scale-95"
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
        >
          <span className={`block transition-transform duration-300 ${theme === 'dark' ? 'rotate-0' : 'rotate-180'}`}>
            {theme === 'dark' ? <SunIcon size={20} /> : <MoonIcon size={20} />}
          </span>
        </button>
      </div>
    </nav>
      <MarketStatusBanner />
    </>
  )
}

export function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
    >
      {children}
    </motion.div>
  )
}
