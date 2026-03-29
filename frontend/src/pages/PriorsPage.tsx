import { useState, useEffect } from 'react'
import { Search, BookOpen } from 'lucide-react'
import PriorCard from '../components/PriorCard.tsx'

interface Prior {
  id: string
  name: string
  principle: string
  practice: string
  trigger_context: string
  source: string
  source_title: string
  created_at: string
  practice_count: number
  last_practiced: string | null
}

export default function PriorsPage() {
  const [priors, setPriors] = useState<Prior[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPriors()
  }, [])

  const fetchPriors = async () => {
    try {
      const res = await fetch('/api/priors')
      const data = await res.json()
      if (data.success) setPriors(data.priors)
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async () => {
    if (!search.trim()) {
      fetchPriors()
      return
    }
    setLoading(true)
    try {
      const res = await fetch('/api/priors/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: search }),
      })
      const data = await res.json()
      if (data.success) setPriors(data.results)
    } catch {
      // silently fail
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="font-serif text-2xl font-semibold text-gray-900">
            My Priors
          </h2>
          <p className="text-gray-500 text-sm mt-1">
            {priors.length} principle{priors.length !== 1 ? 's' : ''} extracted from your learning
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative mb-6">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder="Search your priors..."
          className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-[#E8DFD0] bg-white text-sm focus:outline-none focus:border-gray-400 placeholder:text-gray-300"
        />
      </div>

      {/* List */}
      {loading ? (
        <div className="text-center py-12 text-gray-400 text-sm">Loading...</div>
      ) : priors.length === 0 ? (
        <div className="text-center py-16">
          <BookOpen size={32} className="mx-auto text-gray-300 mb-3" />
          <p className="text-gray-400 text-sm">No priors yet.</p>
          <p className="text-gray-300 text-xs mt-1">
            Go to Capture to add what you've learned.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {priors.map(prior => (
            <div key={prior.id} className="animate-fade-in">
              <div className="text-xs text-gray-300 mb-1 ml-1">
                {formatDate(prior.created_at)}
                {prior.source_title && ` · ${prior.source_title}`}
              </div>
              <PriorCard
                prior={{
                  name: prior.name,
                  principle: prior.principle,
                  practice: prior.practice,
                  trigger: prior.trigger_context,
                  source: prior.source,
                }}
                showPracticeCount={prior.practice_count}
                showLastPracticed={prior.last_practiced ? formatDate(prior.last_practiced) : undefined}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
