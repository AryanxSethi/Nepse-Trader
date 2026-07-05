import { Link } from 'react-router-dom'
import { PageTransition } from '../components/Navbar'
import { ChartIcon } from '../components/Icons'

export default function NotFound() {
  return (
    <PageTransition>
      <div className="max-w-lg mx-auto px-4 py-24 text-center space-y-6">
        <ChartIcon size={48} className="text-text-muted/20 mx-auto" />
        <h1 className="text-4xl font-bold text-text">404</h1>
        <p className="text-text-muted">This page doesn't exist, or the stock you're looking for hasn't listed yet.</p>
        <Link
          to="/"
          className="inline-block px-5 py-2 rounded-lg bg-accent text-white text-sm font-medium hover:bg-accent-hover transition-colors"
        >
          Back to Market
        </Link>
      </div>
    </PageTransition>
  )
}