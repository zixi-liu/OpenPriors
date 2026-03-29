import { Clock } from 'lucide-react'

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
    <div className="card-hover bg-white rounded-xl border border-[#E8DFD0] p-5">
      {/* Header */}
      <h4 className="font-medium text-base mb-2" style={{ color: 'var(--op-font-color)' }}>{prior.name}</h4>

      {/* Principle */}
      <p className="text-sm mb-3 leading-relaxed" style={{ color: 'var(--op-font-color)', opacity: 0.7 }}>{prior.principle}</p>

      {/* Practice + Trigger */}
      <div className="space-y-2">
        <div className="flex items-start gap-2">
          <span className="mt-0.5 shrink-0">🎯</span>
          <span className="text-sm" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>{prior.practice}</span>
        </div>
        <div className="flex items-start gap-2">
          <span className="mt-0.5 shrink-0">⚡</span>
          <span className="text-sm" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>{prior.trigger}</span>
        </div>
      </div>

      {/* Practice stats (if available) */}
      {(showPracticeCount !== undefined || showLastPracticed) && (
        <div className="mt-3 pt-3 border-t border-[#F0EDE7] flex items-center gap-4">
          {showPracticeCount !== undefined && (
            <span className="text-xs" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>
              Practiced {showPracticeCount}x
            </span>
          )}
          {showLastPracticed && (
            <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>
              <Clock size={11} />
              {showLastPracticed}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
