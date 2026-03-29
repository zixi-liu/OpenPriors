import { useState, useRef, useCallback, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'

interface LearningMaterial {
  id: string
  title: string
  isActive: boolean
}

interface OsmosisSession {
  id: string
  title: string
  date: string
}

interface SidebarProps {
  materials: LearningMaterial[]
  sessions: OsmosisSession[]
  onToggleMaterial?: (id: string) => void
  onDeleteMaterial?: (id: string) => void
  onViewMaterial?: (id: string) => void
  onNewPage?: () => void
  onSelectSession?: (id: string) => void
  onDeleteSession?: (id: string) => void
}

export default function Sidebar({
  materials = [],
  sessions = [],
  onToggleMaterial,
  onDeleteMaterial,
  onViewMaterial,
  onNewPage,
  onSelectSession,
  onDeleteSession,
}: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [width, setWidth] = useState(240)
  const [isDragging, setIsDragging] = useState(false)
  const [menuOpen, setMenuOpen] = useState<string | null>(null)
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 })
  const sidebarRef = useRef<HTMLElement>(null)

  const openMenu = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    if (menuOpen === id) { setMenuOpen(null); return }
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    setMenuPos({ top: rect.top, left: rect.right - 12 })
    setMenuOpen(id)
  }

  useEffect(() => {
    const handler = () => setMenuOpen(null)
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
    const startX = e.clientX
    const startWidth = width

    const onMouseMove = (ev: MouseEvent) => {
      const newWidth = Math.min(400, Math.max(180, startWidth + ev.clientX - startX))
      setWidth(newWidth)
    }
    const onMouseUp = () => {
      setIsDragging(false)
      document.removeEventListener('mousemove', onMouseMove)
      document.removeEventListener('mouseup', onMouseUp)
    }
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }, [width])

  return (
    <aside
      ref={sidebarRef}
      className="group relative flex-shrink-0 border-r border-[#EBEBEA] flex flex-col"
      style={{
        width: isCollapsed ? 48 : width,
        transition: isDragging ? 'none' : 'width 0.2s',
        background: 'var(--op-bg)',
        color: 'var(--op-font-color)',
      }}
    >
      {/* Logo + Toggle */}
      <div className="flex items-center gap-1 p-2">
        <a
          href="/"
          className={`flex items-center gap-2 hover:opacity-80 transition-opacity ${isCollapsed ? 'justify-center w-full' : ''}`}
        >
          {!isCollapsed && (
            <span className="text-sm font-medium relative top-[2px] font-serif">OpenPriors</span>
          )}
        </a>
        {!isCollapsed && (
          <button
            onClick={() => setIsCollapsed(true)}
            className="ml-auto p-1 rounded hover:bg-[#00000008]"
            style={{ color: 'var(--op-font-color)', opacity: 0.7 }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        )}
        {isCollapsed && (
          <button
            onClick={() => setIsCollapsed(false)}
            className="absolute top-2 right-1 p-1 rounded hover:bg-[#00000008] opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ color: 'var(--op-font-color)', opacity: 0.7 }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M6 3l5 5-5 5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        )}
      </div>

      {/* My Assets */}
      {!isCollapsed && (
        <div className="px-2 pb-2 mt-3" style={{ minHeight: '12rem' }}>
          <div className="px-1 mb-1">
            <span className="text-base font-bold tracking-wider" style={{ opacity: 0.7 }}>My Assets</span>
          </div>
          {materials.length === 0 ? (
            <p className="text-xs px-1" style={{ opacity: 0.3 }}>No assets yet</p>
          ) : (
            <div className="space-y-0.5 mt-2 max-h-[11rem] overflow-y-auto scrollbar-hide">
              {materials.map((material) => (
                <div
                  key={material.id}
                  className="group/item flex items-start gap-1.5 px-1 py-1 rounded hover:bg-[#00000008] cursor-pointer"
                  onClick={() => onViewMaterial?.(material.id)}
                >
                  <button
                    onClick={(e) => { e.stopPropagation(); onToggleMaterial?.(material.id) }}
                    className={`w-3.5 h-3.5 rounded border flex-shrink-0 flex items-center justify-center transition-colors mt-0.5 ${
                      material.isActive
                        ? 'bg-[#6B4F3A] border-[#6B4F3A]'
                        : 'border-black/20 hover:border-black/40'
                    }`}
                  >
                    {material.isActive && (
                      <svg width="8" height="8" viewBox="0 0 8 8" fill="none">
                        <path d="M1.5 4l2 2 3-3.5" stroke="white" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    )}
                  </button>
                  <span className="flex-1 text-sm truncate" style={{ opacity: 0.7 }}>
                    {material.title}
                  </span>
                  <div className="flex-shrink-0">
                    <button
                      onMouseDown={(e) => openMenu(e, material.id)}
                      className="opacity-0 group-hover/item:opacity-100 p-1 rounded hover:bg-[#00000010]"
                      style={{ color: 'var(--op-font-color)', opacity: 0.4 }}
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* My Projects + New Page */}
      {!isCollapsed && (
        <div className="px-3 mt-3 mb-1 flex items-center justify-between">
          <span className="text-base font-bold tracking-wider" style={{ opacity: 0.7 }}>My Projects</span>
          <button
            onClick={() => { onNewPage?.(); navigate('/capture') }}
            className="flex items-center justify-center rounded-lg border border-[#E3E2E0] hover:bg-[#00000008] transition-colors w-7 h-7"
            style={{ color: 'var(--op-font-color)', opacity: 0.5 }}
          >
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
          </button>
        </div>
      )}

      {/* Session list */}
      {!isCollapsed && (
        <div className="flex-1 overflow-y-auto py-1 scrollbar-hide">
          {sessions.length === 0 && (
            <p className="text-xs px-3 py-4 text-center" style={{ opacity: 0.4 }}>No sessions yet</p>
          )}
          {sessions.map((session) => {
            const isActive = location.pathname.includes(session.id)
            return (
              <div
                key={session.id}
                className={`group/session relative w-full text-left px-3 py-2 text-sm transition-colors cursor-pointer ${
                  isActive ? 'bg-[#EDEDEC] font-medium' : 'hover:bg-[#00000008]'
                }`}
                style={{ opacity: isActive ? 1 : 0.7 }}
                onClick={() => { onSelectSession?.(session.id); navigate('/capture') }}
              >
                <div className="truncate pr-5">{session.title || 'New Page'}</div>
                <div className="text-[10px] mt-0.5" style={{ opacity: 0.4 }}>{session.date}</div>
                <div className="absolute right-2 top-1/2 -translate-y-1/2">
                  <button
                    onMouseDown={(e) => openMenu(e, session.id)}
                    className="p-1 opacity-0 group-hover/session:opacity-100 transition-opacity rounded hover:bg-[#00000010]"
                    style={{ color: 'var(--op-font-color)', opacity: 0.4 }}
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="2"/><circle cx="12" cy="12" r="2"/><circle cx="19" cy="12" r="2"/></svg>
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Settings */}
      <div className="mt-auto px-2 py-2 border-t border-[#EBEBEA]">
        <button
          onClick={() => navigate('/settings')}
          className={`flex items-center gap-1.5 rounded text-sm hover:bg-[#00000008] transition-colors ${
            isCollapsed ? 'justify-center w-full p-1.5' : 'w-full px-2 py-1.5'
          }`}
          style={{
            color: 'var(--op-font-color)',
            opacity: location.pathname === '/settings' ? 1 : 0.5,
            fontWeight: location.pathname === '/settings' ? 500 : 400,
          }}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="flex-shrink-0">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
          {!isCollapsed && <span>Settings</span>}
        </button>
      </div>

      {/* Drag handle */}
      {!isCollapsed && (
        <div
          onMouseDown={handleMouseDown}
          className="absolute top-0 right-0 w-1 h-full cursor-col-resize"
        />
      )}

      {/* Shared context menu */}
      {menuOpen && (
        <div
          className="fixed w-36 border border-[#E3E2E0] rounded-lg shadow-lg py-1"
          style={{ zIndex: 9999, top: menuPos.top, left: menuPos.left, background: 'var(--op-bg)' }}
          onMouseDown={(e) => e.stopPropagation()}
        >
          <button
            onClick={() => { navigator.clipboard.writeText(menuOpen); setMenuOpen(null) }}
            className="w-full flex items-center gap-2 text-left px-3 py-1.5 text-xs hover:bg-[#F7F7F5]"
            style={{ color: 'var(--op-font-color)' }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 12v8a2 2 0 002 2h12a2 2 0 002-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>
            Share
          </button>
          <button
            onClick={() => {
              const isMaterial = materials.some(m => m.id === menuOpen)
              if (isMaterial) onDeleteMaterial?.(menuOpen)
              else onDeleteSession?.(menuOpen)
              setMenuOpen(null)
            }}
            className="w-full flex items-center gap-2 text-left px-3 py-1.5 text-xs hover:bg-[#F7F7F5]"
            style={{ color: 'var(--op-font-color)' }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
            Move to trash
          </button>
        </div>
      )}
    </aside>
  )
}
