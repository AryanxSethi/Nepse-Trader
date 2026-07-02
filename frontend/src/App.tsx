import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from './context/ThemeContext'
import Navbar from './components/Navbar'
import ErrorBoundary from './components/ErrorBoundary'
import Home from './pages/Home'
import Trade from './pages/Trade'
import Signals from './pages/Signals'
import Backtest from './pages/Backtest'
import Guide from './pages/Guide'
import IPOSection from './pages/IPOSection'
import Brokers from './pages/Brokers'
import LiveMarket from './pages/LiveMarket'
import Portfolio from './pages/Portfolio'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
})

function AnimatedRoutes() {
  const location = useLocation()
  return (
    <AnimatePresence mode="wait">
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
      </Routes>
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
          </div>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}
