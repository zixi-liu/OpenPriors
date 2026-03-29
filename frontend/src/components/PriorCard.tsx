import { Target, Zap, Clock } from 'lucide-react'

interface Prior {
  name: string
  principle: string
  practice: string
  trigger: string
  source: string
}

interface Props {
  prior: Prior
  showPracticeCount?: number
  showLastPracticed?: string
}

export default function PriorCard({ prior, showPracticeCount, showLastPracticed }: Props) {
  return (
    <div className="card-hover bg-white rounded-xl border border-[#E8DFD0] p-4">
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <h4 className="font-medium text-gray-900 text-sm">{prior.name}</h4>
        {prior.source && (
          <span className="text-xs text-gray-400 ml-2 shrink-0">{prior.source}</span>
        )}
      </div>

      {/* Principle */}
      <p className="text-sm text-gray-600 mb-3">{prior.principle}</p>

      {/* Practice + Trigger */}
      <div className="space-y-2">
        <div className="flex items-start gap-2">
          <Target size={13} className="text-emerald-500 mt-0.5 shrink-0" />
          <span className="text-xs text-gray-500">{prior.practice}</span>
        </div>
        <div className="flex items-start gap-2">
          <Zap size={13} className="text-amber-500 mt-0.5 shrink-0" />
          <span className="text-xs text-gray-500">{prior.trigger}</span>
        </div>
      </div>

      {/* Practice stats (if available) */}
      {(showPracticeCount !== undefined || showLastPracticed) && (
        <div className="mt-3 pt-3 border-t border-[#F0EDE7] flex items-center gap-4">
          {showPracticeCount !== undefined && (
            <span className="text-xs text-gray-400">
              Practiced {showPracticeCount}x
            </span>
          )}
          {showLastPracticed && (
            <span className="flex items-center gap-1 text-xs text-gray-400">
              <Clock size={11} />
              {showLastPracticed}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
