import { useState } from 'react'

interface Goal {
  id: string
  description: string
  cadence: string
  due_date?: string
}

interface PlanCardProps {
  title: string
  goals: Goal[]
}

const cadenceLabels: Record<string, string> = {
  daily: 'Daily',
  every_2_days: 'Every 2 days',
  weekly: 'Weekly',
}

export default function PlanCard({ title, goals: initialGoals }: PlanCardProps) {
  const [goals, setGoals] = useState(initialGoals)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = () => {
    setSubmitted(true)
  }

  const updateDueDate = async (goalId: string, date: string) => {
    setGoals(prev => prev.map(g => g.id === goalId ? { ...g, due_date: date } : g))
    try {
      await fetch(`/api/osmosis/goals/${goalId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ due_date: date }),
      })
    } catch {}
  }

  return (
    <div className="rounded-xl border border-[#E3E2E0] overflow-hidden" style={{ background: 'var(--op-bg)' }}>
      {/* Header */}
      <div className="px-4 py-3 border-b border-[#E3E2E0]" style={{ background: 'rgba(0,0,0,0.02)' }}>
        <h3 className="text-base font-semibold" style={{ color: 'var(--op-font-color)' }}>{title}</h3>
        <p className="text-xs mt-0.5" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>{goals.length} goals</p>
      </div>

      {/* Goals */}
      <div className="divide-y divide-[#E3E2E0]">
        {goals.map((goal, i) => (
          <div key={goal.id} className="px-4 py-3 flex items-start gap-3">
            {/* Number */}
            <span
              className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium flex-shrink-0 mt-0.5"
              style={{ background: 'rgba(0,0,0,0.05)', color: 'var(--op-font-color)', opacity: 0.6 }}
            >
              {i + 1}
            </span>

            {/* Description + cadence */}
            <div className="flex-1 min-w-0">
              <p className="text-sm leading-relaxed" style={{ color: 'var(--op-font-color)' }}>
                {goal.description}
              </p>
              <span className="text-xs mt-1 inline-block" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>
                {cadenceLabels[goal.cadence] || goal.cadence}
              </span>
            </div>

            {/* Date picker */}
            <div className="flex-shrink-0">
              <input
                type="date"
                value={goal.due_date || ''}
                onChange={(e) => updateDueDate(goal.id, e.target.value)}
                className="text-xs px-2 py-1 rounded-lg border border-[#E3E2E0] focus:outline-none focus:border-gray-400 cursor-pointer"
                style={{ background: 'var(--op-bg)', color: 'var(--op-font-color)' }}
              />
            </div>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-[#E3E2E0] flex items-center justify-between" style={{ background: 'rgba(0,0,0,0.02)' }}>
        <p className="text-xs" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>
          {submitted ? '✅ Goals submitted — reminders are set' : `${goals.filter(g => g.due_date).length}/${goals.length} dates set`}
        </p>
        {!submitted && (
          <button
            onClick={handleSubmit}
            disabled={goals.every(g => !g.due_date)}
            className="px-4 py-1.5 text-xs font-medium rounded-lg transition-colors disabled:opacity-30"
            style={{
              background: goals.some(g => g.due_date) ? 'var(--op-font-color)' : 'transparent',
              color: goals.some(g => g.due_date) ? 'var(--op-bg)' : 'var(--op-font-color)',
              opacity: goals.some(g => g.due_date) ? 1 : 0.3,
            }}
          >
            Submit goals for reminders
          </button>
        )}
      </div>
    </div>
  )
}
