import { Link, useLocation } from 'react-router-dom'
import { BookOpen, Sparkles, Settings } from 'lucide-react'

export default function Sidebar() {
  const location = useLocation()

  const links = [
    { to: '/capture', label: 'Capture', icon: Sparkles },
    { to: '/priors', label: 'My Priors', icon: BookOpen },
  ]

  return (
    <aside className="w-56 border-r border-[#E8DFD0] bg-[#FAF8F4] flex flex-col">
      {/* Logo */}
      <div className="p-5 border-b border-[#E8DFD0]">
        <h1 className="font-serif text-xl font-semibold text-gray-900">
          OpenPriors
        </h1>
        <p className="text-xs text-gray-400 mt-0.5">
          Turn what you learn into what you do
        </p>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 space-y-1">
        {links.map(({ to, label, icon: Icon }) => {
          const active = location.pathname === to
          return (
            <Link
              key={to}
              to={to}
              className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? 'bg-[#EDEAE4] text-gray-900 font-medium'
                  : 'text-gray-500 hover:bg-[#F0EDE7] hover:text-gray-700'
              }`}
            >
              <Icon size={16} />
              {label}
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-[#E8DFD0]">
        <Link
          to="/setup"
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-gray-600 hover:bg-[#F0EDE7] transition-colors"
        >
          <Settings size={14} />
          Settings
        </Link>
      </div>
    </aside>
  )
}
