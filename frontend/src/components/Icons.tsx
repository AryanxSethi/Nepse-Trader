type IconProps = { size?: number; className?: string }

function Icon({ children, size = 16, className = '' }: IconProps & { children: React.ReactNode }) {
  return <span className={`inline-flex items-center justify-center ${className}`} style={{ width: size, height: size }}>{children}</span>
}

/** Search magnifying glass icon. */
export function SearchIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" />
      </svg>
    </Icon>
  )
}

/** Sun icon for light mode toggle. */
export function SunIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="5" /><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
      </svg>
    </Icon>
  )
}

/** Moon icon for dark mode toggle. */
export function MoonIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3a9 9 0 1 0 9 9c0-.46 0-.92-.04-1.36a7 7 0 0 1-8.6-8.6A9 9 0 0 0 12 3z" />
      </svg>
    </Icon>
  )
}

/** Line chart icon. */
export function ChartIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 3v18h18" /><path d="M7 16l4-8 4 4 4-6" />
      </svg>
    </Icon>
  )
}

/** Home house icon. */
export function HomeIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    </Icon>
  )
}

/** Book icon for guide/educational content. */
export function BookIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
      </svg>
    </Icon>
  )
}

/** Zigzag chart icon for backtesting. */
export function BacktestIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    </Icon>
  )
}

/** Signal/bars icon for trading signals. */
export function SignalIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 20V10" /><path d="M18 20V4" /><path d="M6 20v-4" />
      </svg>
    </Icon>
  )
}

/** Brain icon for AI/analyst features. */
export function BrainIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.04-4.44 2.5 2.5 0 0 1 0-5 2.5 2.5 0 0 1 2.04-4.44A2.5 2.5 0 0 1 9.5 2z" />
        <path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.04-4.44 2.5 2.5 0 0 0 0-5 2.5 2.5 0 0 0-2.04-4.44A2.5 2.5 0 0 0 14.5 2z" />
      </svg>
    </Icon>
  )
}

/** Trending upward arrow icon. */
export function TrendingUpIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 6 13.5 15.5 8.5 10.5 1 18" /><polyline points="17 6 23 6 23 12" />
      </svg>
    </Icon>
  )
}

/** Trending downward arrow icon. */
export function TrendingDownIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" /><polyline points="17 18 23 18 23 12" />
      </svg>
    </Icon>
  )
}

/** Chat bubble icon. */
export function ChatIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    </Icon>
  )
}

/** Info circle icon. */
export function InfoIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="12" cy="12" r="10" /><path d="M12 16v-4" /><path d="M12 8h.01" />
      </svg>
    </Icon>
  )
}

/** Triangle warning/exclamation icon. */
export function WarningIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    </Icon>
  )
}

/** Close/X icon. */
export function CloseIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
      </svg>
    </Icon>
  )
}

/** Building/company icon. */
export function CompanyIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="4" y="2" width="16" height="20" rx="2" ry="2" /><path d="M9 22v-4h6v4" /><path d="M8 6h.01" /><path d="M16 6h.01" /><path d="M8 10h.01" /><path d="M16 10h.01" /><path d="M8 14h.01" /><path d="M16 14h.01" />
      </svg>
    </Icon>
  )
}

/** Link/source chain icon. */
export function SourceIcon({ size = 16, className = '' }: IconProps) {
  return (
    <Icon size={size} className={className}>
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" /><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
      </svg>
    </Icon>
  )
}

/** Upward chevron arrow icon. */
export function ArrowUpIcon({ size = 16, className = '' }: IconProps) {
  return <Icon size={size} className={className}>
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="18 15 12 9 6 15" /></svg>
  </Icon>
}

/** Downward chevron arrow icon. */
export function ArrowDownIcon({ size = 16, className = '' }: IconProps) {
  return <Icon size={size} className={className}>
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9" /></svg>
  </Icon>
}

/** Rightward chevron arrow icon. */
export function ArrowRightIcon({ size = 16, className = '' }: IconProps) {
  return <Icon size={size} className={className}>
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
  </Icon>
}

/** Left-pointing chevron icon. */
export function ChevronLeftIcon({ size = 16, className = '' }: IconProps) {
  return <Icon size={size} className={className}>
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6" /></svg>
  </Icon>
}

/** Right-pointing chevron icon. */
export function ChevronRightIcon({ size = 16, className = '' }: IconProps) {
  return <Icon size={size} className={className}>
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6" /></svg>
  </Icon>
}

/** Document/file icon. */
export function DocumentIcon({ size = 16, className = '' }: IconProps) {
  return <Icon size={size} className={className}>
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  </Icon>
}

/** Comparison bars icon. */
export function CompareIcon({ size = 16, className = '' }: IconProps) {
  return <Icon size={size} className={className}>
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="20" x2="18" y2="10" />
      <line x1="12" y1="20" x2="12" y2="4" />
      <line x1="6" y1="20" x2="6" y2="14" />
    </svg>
  </Icon>
}

/** Wallet icon for portfolio. */
export function WalletIcon({ size = 16, className = '' }: IconProps) {
  return <Icon size={size} className={className}>
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 12V7H5a2 2 0 0 1 0-4h14v4" /><path d="M3 5v14a2 2 0 0 0 2 2h16v-5" /><path d="M18 12a2 2 0 0 0 0 4h4v-4Z" />
    </svg>
  </Icon>
}

/** Grid/table icon. */
export function TableIcon({ size = 16, className = '' }: IconProps) {
  return <Icon size={size} className={className}>
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <line x1="3" y1="9" x2="21" y2="9" />
      <line x1="3" y1="15" x2="21" y2="15" />
      <line x1="9" y1="3" x2="9" y2="21" />
    </svg>
  </Icon>
}


