import { useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { useTheme, DEFAULT_THEME } from '../context/ThemeContext.tsx'

const FONT_OPTIONS = [
  'Inter',
  'Baskervville',
  'Libre Caslon Text',
  'Sabon',
  'EB Garamond',
  'Seraphine',
  'Copernicus',
  'Noto Sans',
]

const THEMES = [
  { name: 'Light', bgColor: '#FDFBF7', fontColor: '#1a1a1a' },
  { name: 'Bright', bgColor: '#FFFFFF', fontColor: '#1a1a1a' },
  { name: 'Dark', bgColor: '#1a1a2e', fontColor: '#e0e0e0' },
]

export default function SettingsPage() {
  const { theme, setTheme } = useTheme()
  const [local, setLocal] = useState(theme)

  const update = (partial: Partial<typeof local>) => {
    const next = { ...local, ...partial }
    setLocal(next)
    setTheme(next)
  }

  const reset = () => {
    setLocal(DEFAULT_THEME)
    setTheme(DEFAULT_THEME)
  }

  const activeThemeName = THEMES.find(t => t.bgColor === local.bgColor)?.name

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="font-serif text-2xl font-semibold" style={{ color: 'var(--op-font-color)' }}>
            Appearance
          </h2>
          <p className="text-sm mt-1" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>
            Choose your theme and font
          </p>
        </div>
        <button
          onClick={reset}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm border border-[#E8DFD0] hover:bg-[#F0EDE7] transition-colors"
          style={{ color: 'var(--op-font-color)' }}
        >
          <RotateCcw size={13} />
          Reset
        </button>
      </div>

      <div className="space-y-8">
        {/* Theme */}
        <div>
          <label className="text-xs font-medium uppercase tracking-wide mb-3 block" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>
            Theme
          </label>
          <div className="flex gap-3">
            {THEMES.map(t => (
              <button
                key={t.name}
                onClick={() => update({ bgColor: t.bgColor, fontColor: t.fontColor })}
                className={`flex-1 rounded-xl border-2 p-4 text-center transition-all ${
                  activeThemeName === t.name
                    ? 'border-gray-900 shadow-sm'
                    : 'border-[#E8DFD0] hover:border-gray-400'
                }`}
                style={{ backgroundColor: t.bgColor, color: t.fontColor }}
              >
                <div className="text-sm font-medium">{t.name}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Font Family */}
        <div>
          <label className="text-xs font-medium uppercase tracking-wide mb-3 block" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>
            Font
          </label>
          <div className="grid grid-cols-2 gap-2">
            {FONT_OPTIONS.map(f => (
              <button
                key={f}
                onClick={() => update({ fontFamily: f })}
                className={`px-4 py-2.5 rounded-lg text-sm text-left border transition-colors ${
                  local.fontFamily === f
                    ? 'border-gray-900 bg-gray-900 text-white'
                    : 'border-[#E8DFD0] hover:border-gray-400'
                }`}
                style={{ fontFamily: `'${f}', sans-serif`, color: local.fontFamily === f ? undefined : 'var(--op-font-color)' }}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
