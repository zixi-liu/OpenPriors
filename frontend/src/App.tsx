import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { ThemeProvider } from './context/ThemeContext.tsx'
import Sidebar from './components/Sidebar.tsx'
import MaterialViewerModal from './components/MaterialViewerModal.tsx'
import CapturePage from './pages/CapturePage.tsx'
import PriorsPage from './pages/PriorsPage.tsx'
import SettingsPage from './pages/SettingsPage.tsx'

export default function App() {
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [materials, setMaterials] = useState<{ id: string; title: string; isActive: boolean }[]>([])
  const [sessions, setSessions] = useState<{ id: string; title: string; date: string }[]>([])
  const [viewingMaterialId, setViewingMaterialId] = useState<string | null>(null)
  const [pageKey, setPageKey] = useState(0)
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/setup/status')
      .then(r => r.json())
      .then(data => setConfigured(data.configured))
      .catch(() => setConfigured(false))
  }, [])

  const fetchAssets = () => {
    fetch('/api/assets/materials')
      .then(r => r.json())
      .then(data => {
        if (data.success && data.materials) {
          setMaterials(
            data.materials.map((m: { id: string; title: string }) => ({
              id: m.id,
              title: m.title,
              isActive: true,
            }))
          )
        }
      })
      .catch(() => {})
  }

  useEffect(() => { fetchAssets() }, [])

  const fetchSessions = () => {
    fetch('/api/osmosis/sessions')
      .then(r => r.json())
      .then(data => {
        if (data.success && data.sessions) {
          setSessions(
            data.sessions.map((s: { id: string; title: string; updated_at: string }) => ({
              id: s.id,
              title: s.title,
              date: new Date(s.updated_at).toLocaleDateString(),
            }))
          )
        }
      })
      .catch(() => {})
  }

  useEffect(() => { fetchSessions() }, [])

  const toggleMaterial = (id: string) => {
    setMaterials(prev =>
      prev.map(m => m.id === id ? { ...m, isActive: !m.isActive } : m)
    )
  }

  const deleteMaterial = async (id: string) => {
    try {
      const res = await fetch(`/api/assets/materials/${id}`, { method: 'DELETE' })
      const data = await res.json()
      if (data.success) {
        setMaterials(prev => prev.filter(m => m.id !== id))
      }
    } catch { /* silently fail */ }
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
          onDeleteMaterial={deleteMaterial}
          onViewMaterial={(id) => setViewingMaterialId(id)}
          onNewPage={() => { setActiveSessionId(null); sessionStorage.removeItem('openpriors-session-id'); setPageKey(k => k + 1) }}
          onSelectSession={(id) => { setActiveSessionId(id); setPageKey(k => k + 1) }}
          onDeleteSession={async (id) => {
            try {
              await fetch(`/api/osmosis/sessions/${id}`, { method: 'DELETE' })
              setSessions(prev => prev.filter(s => s.id !== id))
            } catch {}
          }}
        />
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<Navigate to="/capture" />} />
            <Route path="/capture" element={<CapturePage key={pageKey} sessionId={activeSessionId} onAssetAdded={fetchAssets} onSessionCreated={fetchSessions} />} />
            <Route path="/priors" element={<PriorsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>

        {viewingMaterialId && (
          <MaterialViewerModal
            materialId={viewingMaterialId}
            onClose={() => setViewingMaterialId(null)}
          />
        )}
      </div>
    </ThemeProvider>
  )
}
