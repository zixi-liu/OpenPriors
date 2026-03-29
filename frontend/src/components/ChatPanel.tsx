import { useState, useRef, useEffect } from 'react'

interface Message {
  role: 'user' | 'assistant'
  content: string
  options?: Option[]
}

interface Option {
  title: string
  description: string
  type: string
}

interface ChatPanelProps {
  renderInput?: boolean
}

export function ChatMessages() {
  const { messages, loading, selectOption } = useChatContext()

  if (messages.length === 0 && !loading) return null

  return (
    <div className="max-w-2xl mx-auto w-full px-6 pt-6 pb-4 space-y-4">
      {messages.map((msg, i) => (
        <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
          <div className="max-w-[85%]">
            <div
              className={`rounded-2xl px-4 py-2.5 text-base leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-gray-900 text-white rounded-br-md'
                  : 'bg-[#F7F7F5] rounded-bl-md'
              }`}
              style={msg.role === 'assistant' ? { color: 'var(--op-font-color)' } : {}}
            >
              {msg.content}
            </div>

            {msg.options && msg.options.length > 0 && (
              <div className="mt-2 space-y-1.5">
                {msg.options.map((opt, j) => (
                  <button
                    key={j}
                    onClick={() => selectOption(opt)}
                    className="w-full text-left p-2.5 rounded-lg border border-[#E3E2E0] hover:bg-[#F7F7F5] transition-colors"
                  >
                    <p className="text-base font-medium" style={{ color: 'var(--op-font-color)' }}>{opt.title}</p>
                    <p className="text-sm mt-0.5" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>{opt.description}</p>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}

      {loading && (
        <div className="flex justify-start">
          <div className="bg-[#F7F7F5] rounded-2xl rounded-bl-md px-4 py-3">
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export function ChatInput() {
  const { input, setInput, loading, sendMessage } = useChatContext()
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="px-6 py-3" style={{ background: 'var(--op-bg)' }}>
      <div className="max-w-2xl mx-auto">
        <div className="relative">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your learnings..."
            disabled={loading}
            rows={1}
            className="w-full text-sm px-4 pt-3 pb-10 rounded-xl border border-[#E3E2E0] focus:outline-none focus:border-gray-400 disabled:opacity-50 resize-none"
            style={{ background: 'var(--op-bg)', color: 'var(--op-font-color)', minHeight: '56px' }}
          />
          <div className="absolute right-3 bottom-3">
            <button
              onClick={() => sendMessage()}
              disabled={loading || !input.trim()}
              className="p-2 bg-gray-900 text-white rounded-full hover:bg-gray-800 disabled:opacity-40 transition-colors"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

// ============================================================
// Chat context — shared state between ChatMessages and ChatInput
// ============================================================

import { createContext, useContext } from 'react'

interface ChatContextType {
  sessionId: string | null
  sessionTitle: string
  messages: Message[]
  sessionPriors: any[]
  input: string
  setInput: (v: string) => void
  loading: boolean
  sendMessage: (text?: string) => void
  selectOption: (option: Option) => void
}

const ChatContext = createContext<ChatContextType | null>(null)

export function useChatContext() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error('useChatContext must be used within ChatProvider')
  return ctx
}

export default function ChatProvider({ children, existingSessionId, onSessionReady }: { children: React.ReactNode; existingSessionId?: string; onSessionReady?: (id: string) => void }) {
  const [sessionId, setSessionId] = useState<string | null>(existingSessionId || null)
  const [messages, setMessages] = useState<Message[]>([])
  const [sessionTitle, setSessionTitle] = useState('')
  const [sessionPriors, setSessionPriors] = useState<any[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const createNewSession = async () => {
    const createRes = await fetch('/api/osmosis/sessions', { method: 'POST' })
    const createData = await createRes.json()
    if (!createData.success) return
    const sid = createData.session_id
    setSessionId(sid)
    sessionStorage.setItem('openpriors-session-id', sid)
    onSessionReady?.(sid)

    const chatRes = await fetch('/api/osmosis/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: sid,
        message: '[SYSTEM] User just opened a new session. Greet them briefly, mention their most recently added learning material if any, and ask what they are interested in working on today.',
      }),
    })
    const chatData = await chatRes.json()
    if (chatData.success) {
      setMessages([{ role: 'assistant', content: chatData.message, options: chatData.options }])
    }
  }

  // Load existing session or create new one
  useEffect(() => {
    const init = async () => {
      setLoading(true)

      // Check for session to load: explicit prop > sessionStorage > create new
      const loadId = existingSessionId || sessionStorage.getItem('openpriors-session-id')

      try {
        if (loadId) {
          // Load existing session messages + priors
          const res = await fetch(`/api/osmosis/sessions/${loadId}`)
          const data = await res.json()
          if (data.success && data.messages) {
            setSessionId(loadId)
            sessionStorage.setItem('openpriors-session-id', loadId)
            onSessionReady?.(loadId)
            if (data.session?.title) setSessionTitle(data.session.title)
            setMessages(data.messages.map((m: any) => ({
              role: m.role,
              content: m.content,
              options: m.options || undefined,
            })))
            if (data.priors) setSessionPriors(data.priors)
          } else {
            // Session not found — fall through to create new
            sessionStorage.removeItem('openpriors-session-id')
            await createNewSession()
          }
        } else {
          await createNewSession()
        }
      } catch {
        setMessages([{ role: 'assistant', content: "Hey! What would you like to work on today?" }])
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  const sendMessage = async (text?: string) => {
    const userMsg = (text || input).trim()
    if (!userMsg || loading || !sessionId) return
    setInput('')

    const newMessages: Message[] = [...messages, { role: 'user', content: userMsg }]
    setMessages(newMessages)
    setLoading(true)

    try {
      const res = await fetch('/api/osmosis/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: userMsg }),
      })
      const data = await res.json()
      if (data.success) {
        setMessages([...newMessages, { role: 'assistant', content: data.message, options: data.options }])
      }
    } catch {
      setMessages([...newMessages, { role: 'assistant', content: 'Something went wrong.' }])
    } finally {
      setLoading(false)
    }
  }

  const selectOption = (option: Option) => {
    sendMessage(`I'd like to: ${option.title}`)
  }

  return (
    <ChatContext.Provider value={{ sessionId, sessionTitle, messages, sessionPriors, input, setInput, loading, sendMessage, selectOption }}>
      {children}
    </ChatContext.Provider>
  )
}
