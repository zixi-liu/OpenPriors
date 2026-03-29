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

export default function ChatPanel() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Create session and get greeting on mount
  useEffect(() => {
    const init = async () => {
      setLoading(true)
      try {
        const createRes = await fetch('/api/osmosis/sessions', { method: 'POST' })
        const createData = await createRes.json()
        if (!createData.success) return
        const sid = createData.session_id
        setSessionId(sid)

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
      } catch {
        setMessages([{ role: 'assistant', content: "Hey! What would you like to work on today?" }])
      } finally {
        setLoading(false)
        setTimeout(() => inputRef.current?.focus(), 100)
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <>
      {/* Messages */}
      {messages.length > 0 && (
        <div className="max-w-2xl mx-auto w-full px-6 pt-6 pb-4 space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className="max-w-[85%]">
                <div
                  className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
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
                        <p className="text-sm font-medium" style={{ color: 'var(--op-font-color)' }}>{opt.title}</p>
                        <p className="text-xs mt-0.5" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>{opt.description}</p>
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
      )}

      {/* Input — sticky bottom */}
      <div className="sticky bottom-0 px-6 py-3" style={{ background: 'var(--op-bg)' }}>
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
              {input.trim() ? (
                <button
                  onClick={() => sendMessage()}
                  disabled={loading}
                  className="p-2 bg-gray-900 text-white rounded-full hover:bg-gray-800 disabled:opacity-40 transition-colors"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                  </svg>
                </button>
              ) : (
                <span className="text-xs" style={{ color: 'var(--op-font-color)', opacity: 0.3 }}>
                  Enter to send
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
