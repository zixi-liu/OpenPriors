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
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [greeted, setGreeted] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  // Auto-greet on mount
  useEffect(() => {
    if (greeted) return
    setGreeted(true)
    setLoading(true)

    fetch('/api/osmosis/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        conversation: [],
        message: '[SYSTEM] User just opened a new session. Greet them briefly, mention their most recently added learning material if any, and ask what they are interested in working on today.',
      }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          setMessages([{ role: 'assistant', content: data.message, options: data.options }])
        }
      })
      .catch(() => {
        setMessages([{ role: 'assistant', content: "Hey! What would you like to work on today?" }])
      })
      .finally(() => {
        setLoading(false)
        setTimeout(() => inputRef.current?.focus(), 100)
      })
  }, [])

  const sendMessage = async (text?: string) => {
    const userMsg = (text || input).trim()
    if (!userMsg || loading) return
    setInput('')

    const newMessages: Message[] = [...messages, { role: 'user', content: userMsg }]
    setMessages(newMessages)
    setLoading(true)

    try {
      const conversation = newMessages.slice(0, -1).map(m => ({ role: m.role, content: m.content }))
      const res = await fetch('/api/osmosis/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation, message: userMsg }),
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
    <div className="mt-6 ml-1 border border-[#E3E2E0] rounded-xl overflow-hidden flex flex-col" style={{ maxHeight: '60vh' }}>
      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scrollbar-hide">
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

      {/* Input */}
      <div className="border-t border-[#E3E2E0] px-3 py-3">
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your learnings..."
            disabled={loading}
            rows={1}
            className="flex-1 text-sm px-3 py-2 rounded-lg border border-[#E3E2E0] focus:outline-none focus:border-gray-400 disabled:opacity-50 resize-none"
            style={{ background: 'var(--op-bg)', color: 'var(--op-font-color)' }}
          />
          <button
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            className="px-3 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800 disabled:opacity-40 transition-colors"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M14 2L7 9M14 2l-4.5 12-2-5.5L2 6.5 14 2z" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
