import { Routes, Route, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar.tsx'
import SetupPage from './pages/SetupPage.tsx'
import CapturePage from './pages/CapturePage.tsx'
import PriorsPage from './pages/PriorsPage.tsx'

export default function App() {
  const [configured, setConfigured] = useState<boolean | null>(null)

  useEffect(() => {
    fetch('/api/setup/status')
      .then(r => r.json())
      .then(data => setConfigured(data.configured))
      .catch(() => setConfigured(false))
  }, [])

  if (configured === null) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#FDFBF7]">
        <div className="text-gray-400">Loading...</div>
      </div>
    )
  }

  if (!configured) {
    return <SetupPage onComplete={() => setConfigured(true)} />
  }

  return (
    <div className="h-screen flex bg-[#FDFBF7]">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <Routes>
          <Route path="/" element={<Navigate to="/capture" />} />
          <Route path="/capture" element={<CapturePage />} />
          <Route path="/priors" element={<PriorsPage />} />
        </Routes>
      </main>
    </div>
  )
}
