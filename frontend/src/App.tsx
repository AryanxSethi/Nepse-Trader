import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { ThemeProvider } from './context/ThemeContext'
import Navbar from './components/Navbar'
import ErrorBoundary from './components/ErrorBoundary'
import { SkeletonCard } from './components/Skeleton'

const Home = lazy(() => import('./pages/Home'))
const Trade = lazy(() => import('./pages/Trade'))
const Signals = lazy(() => import('./pages/Signals'))
const Backtest = lazy(() => import('./pages/Backtest'))
const Guide = lazy(() => import('./pages/Guide'))
const IPOSection = lazy(() => import('./pages/IPOSection'))
const Brokers = lazy(() => import('./pages/Brokers'))
const LiveMarket = lazy(() => import('./pages/LiveMarket'))
const Portfolio = lazy(() => import('./pages/Portfolio'))
const NotFound = lazy(() => import('./pages/NotFound'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 15_000,
      retry: 2,
      retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10000),
      refetchOnWindowFocus: false,
    },
  },
})

function AnimatedRoutes() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
      <Suspense fallback={<div className="max-w-5xl mx-auto px-4 py-6"><SkeletonCard lines={4} /></div>}>
        <Routes location={location} key={location.pathname}>
          <Route path="/" element={<Home />} />
          <Route path="/trade" element={<Trade />} />
          <Route path="/signals" element={<Signals />} />
          <Route path="/brokers" element={<Brokers />} />
          <Route path="/market" element={<LiveMarket />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/guide" element={<Guide />} />
          <Route path="/ipo" element={<IPOSection />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </Suspense>
    </AnimatePresence>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div className="min-h-screen bg-surface">
            <Navbar />
            <ErrorBoundary>
              <AnimatedRoutes />
            </ErrorBoundary>
            <Toaster
              position="bottom-right"
              richColors
              closeButton
              toastOptions={{
                style: { background: 'var(--bg-card)', color: 'var(--text)', border: '1px solid var(--border)' },
              }}
            />
          </div>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
