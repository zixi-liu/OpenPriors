import { useState, useRef, useCallback } from 'react'
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
  onNewSession?: () => void
  onDeleteSession?: (id: string) => void
}

export default function Sidebar({
  materials = [],
  sessions = [],
  onToggleMaterial,
  onDeleteMaterial,
  onViewMaterial,
  onNewSession,
  onDeleteSession,
}: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [width, setWidth] = useState(240)
  const [isDragging, setIsDragging] = useState(false)
  const sidebarRef = useRef<HTMLElement>(null)

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
        <div className="px-2 pb-2 mt-3">
          <div className="px-1 mb-1">
            <span className="text-sm font-bold tracking-wider" style={{ opacity: 0.7 }}>My Assets</span>
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
                  <span className="flex-1 text-xs truncate" style={{ opacity: 0.7 }}>
                    {material.title}
                  </span>
                  {onDeleteMaterial && (
                    <button
                      onClick={(e) => { e.stopPropagation(); onDeleteMaterial(material.id) }}
                      className="opacity-0 group-hover/item:opacity-100 p-0.5 rounded hover:bg-[#00000010] flex-shrink-0 mt-0.5"
                      style={{ color: 'var(--op-font-color)', opacity: 0.3 }}
                    >
                      <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                        <path d="M2.5 2.5l5 5M7.5 2.5l-5 5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                      </svg>
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* My Osmosis Sessions */}
      {!isCollapsed && (
        <div className="px-3 mt-3 mb-1">
          <span className="text-sm font-bold tracking-wider" style={{ opacity: 0.7 }}>My Sessions</span>
        </div>
      )}

      {/* New Session */}
      {!isCollapsed && (
      <div className="px-2 pb-2">
        <button
          onClick={onNewSession || (() => navigate('/capture'))}
          className="flex items-center gap-1.5 rounded text-sm hover:bg-[#00000008] transition-colors w-full px-2 py-1.5"
          style={{ color: 'var(--op-font-color)', opacity: 0.7 }}
        >
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" className="flex-shrink-0">
            <path d="M7 2v10M2 7h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          <span>New Session</span>
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
                onClick={() => navigate(`/session/${session.id}`)}
              >
                <div className="truncate pr-5">{session.title || 'Untitled Session'}</div>
                <div className="text-[10px] mt-0.5" style={{ opacity: 0.4 }}>{session.date}</div>
                {onDeleteSession && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onDeleteSession(session.id) }}
                    className="absolute right-2 top-1/2 -translate-y-1/2 p-0.5 opacity-0 group-hover/session:opacity-100 transition-opacity"
                    style={{ color: 'var(--op-font-color)', opacity: 0.2 }}
                  >
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                      <path d="M3.5 3.5l7 7M10.5 3.5l-7 7" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                    </svg>
                  </button>
                )}
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
    </aside>
  )
}
