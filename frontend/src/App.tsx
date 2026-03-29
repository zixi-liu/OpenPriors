import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { ThemeProvider } from './context/ThemeContext.tsx'
import Sidebar from './components/Sidebar.tsx'
import CapturePage from './pages/CapturePage.tsx'
import PriorsPage from './pages/PriorsPage.tsx'
import SettingsPage from './pages/SettingsPage.tsx'

export default function App() {
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [materials, setMaterials] = useState<{ id: string; title: string; isActive: boolean }[]>([])
  const [sessions] = useState<{ id: string; title: string; date: string }[]>([])

  useEffect(() => {
    fetch('/api/setup/status')
      .then(r => r.json())
      .then(data => setConfigured(data.configured))
      .catch(() => setConfigured(false))
  }, [])

  useEffect(() => {
    fetch('/api/priors')
      .then(r => r.json())
      .then(data => {
        if (data.success && data.priors) {
          const uniqueSources = new Map<string, string>()
          for (const p of data.priors) {
            if (p.source_title && !uniqueSources.has(p.source_title)) {
              uniqueSources.set(p.source_title, p.id)
            }
          }
          setMaterials(
            Array.from(uniqueSources.entries()).map(([title, id]) => ({
              id,
              title,
              isActive: true,
            }))
          )
        }
      })
      .catch(() => {})
  }, [])

  const toggleMaterial = (id: string) => {
    setMaterials(prev =>
      prev.map(m => m.id === id ? { ...m, isActive: !m.isActive } : m)
    )
  }

  if (configured === null) {
    return (
      <ThemeProvider>
        <div className="h-screen flex items-center justify-center" style={{ background: 'var(--op-bg)' }}>
          <span style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>Loading...</span>
        </div>
      </ThemeProvider>
    )
  }

  if (!configured) {
    return (
      <ThemeProvider>
        <div className="h-screen flex items-center justify-center" style={{ background: 'var(--op-bg)', color: 'var(--op-font-color)' }}>
          <div className="text-center max-w-md px-6">
            <h1 className="font-serif text-3xl font-semibold mb-3">OpenPriors</h1>
            <p className="text-sm mb-8" style={{ opacity: 0.5 }}>
              Turn what you learn into what you do.
            </p>
            <div className="rounded-xl border border-[#E3E2E0] p-6 text-left" style={{ background: 'var(--op-bg)' }}>
              <p className="text-sm mb-3" style={{ opacity: 0.7 }}>Run this in your terminal to get started:</p>
              <code className="block px-4 py-3 rounded-lg bg-gray-900 text-green-400 text-sm font-mono">
                python setup.py
              </code>
              <p className="text-xs mt-4" style={{ opacity: 0.4 }}>
                This will configure your LLM provider and API key. Your key is stored locally at ~/.openpriors/config.json
              </p>
            </div>
          </div>
        </div>
      </ThemeProvider>
    )
  }

  return (
    <ThemeProvider>
      <div className="h-screen flex" style={{ background: 'var(--op-bg)', color: 'var(--op-font-color)', fontFamily: 'var(--op-font-family)' }}>
        <Sidebar
          materials={materials}
          sessions={sessions}
          onToggleMaterial={toggleMaterial}
        />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Navigate to="/capture" />} />
            <Route path="/capture" element={<CapturePage />} />
            <Route path="/priors" element={<PriorsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </ThemeProvider>
  )
}
