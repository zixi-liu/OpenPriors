import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import PriorCard from '../components/PriorCard.tsx'
import ChatProvider, { ChatMessages, ChatInput, useChatContext } from '../components/ChatPanel.tsx'

interface Prior {
  name: string
  principle: string
  practice: string
  trigger: string
  source: string
}

interface CaptureResult {
  title: string
  summary: string
  priors: Prior[]
}

export default function CapturePage({ sessionId, onAssetAdded }: { sessionId?: string | null; onAssetAdded?: () => void }) {
  const [titleValue, setTitleValue] = useState('')
  const titleRef = useRef<HTMLHeadingElement>(null)
  const chatSessionIdRef = useRef<string | null>(sessionId || null)

  // Upload
  const [isUploadDropdownOpen, setIsUploadDropdownOpen] = useState(false)
  const uploadDropdownRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  // Link modal
  const [linkModalOpen, setLinkModalOpen] = useState(false)
  const [linkType, setLinkType] = useState<'youtube' | 'article'>('youtube')
  const [linkUrl, setLinkUrl] = useState('')
  const linkInputRef = useRef<HTMLInputElement>(null)

  // Story/voice Q&A — same pattern as coach-ai
  const [storyModalOpen, setStoryModalOpen] = useState(false)
  const [storyQA, setStoryQA] = useState<{ question: string; answer: string }[]>([])
  const [storyCurrentQ, setStoryCurrentQ] = useState('')
  const [storyRecording, setStoryRecording] = useState(false)
  const [storyTranscript, setStoryTranscript] = useState('')
  const [storyLoadingQ, setStoryLoadingQ] = useState(false)
  const [storyGenerating, setStoryGenerating] = useState(false)
  const [storyComplete, setStoryComplete] = useState(false)
  const recognitionRef = useRef<any>(null)

  const navigate = useNavigate()

  // Results
  const [result, setResult] = useState<CaptureResult | null>(null)
  const [error, setError] = useState('')

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (uploadDropdownRef.current && !uploadDropdownRef.current.contains(e.target as Node)) {
        setIsUploadDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (linkModalOpen) setTimeout(() => linkInputRef.current?.focus(), 100)
  }, [linkModalOpen])

  // --- Upload Material ---

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setIsAnalyzing(true)
    setError('')
    setResult(null)
    try {
      const text = await file.text()
      const res = await fetch('/api/assets/upload/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text, source: file.name, session_id: chatSessionIdRef.current }),
      })
      const data = await res.json()
      if (data.success) { setResult({ title: data.title, summary: data.summary, priors: data.priors }); onAssetAdded?.() }
      else setError(data.error || 'Failed to extract priors')
    } catch { setError('Could not connect to server') }
    finally { setIsAnalyzing(false); e.target.value = '' }
  }

  const handleLinkSubmit = async () => {
    if (!linkUrl.trim()) return
    setLinkModalOpen(false)
    setIsAnalyzing(true)
    setError('')
    setResult(null)
    try {
      const res = await fetch('/api/assets/upload/url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: linkUrl, session_id: chatSessionIdRef.current }),
      })
      const data = await res.json()
      if (data.success) { setResult({ title: data.title, summary: data.summary, priors: data.priors }); onAssetAdded?.() }
      else setError(data.error || 'Failed to extract priors')
    } catch { setError('Could not connect to server') }
    finally { setIsAnalyzing(false); setLinkUrl('') }
  }

  // --- Voice Q&A (ported from coach-ai) ---

  const startStoryFlow = async () => {
    setStoryQA([])
    setStoryTranscript('')
    setStoryComplete(false)
    setStoryLoadingQ(true)
    setStoryModalOpen(true)
    try {
      const res = await fetch('/api/assets/voice/next-question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation: [] }),
      })
      const data = await res.json()
      setStoryCurrentQ(data.question)
    } catch (err) {
      console.error('Failed to get first question:', err)
    } finally {
      setStoryLoadingQ(false)
    }
  }

  const fetchNextQuestion = async (updatedQA: { question: string; answer: string }[]) => {
    setStoryLoadingQ(true)
    try {
      const res = await fetch('/api/assets/voice/next-question', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation: updatedQA }),
      })
      const data = await res.json()
      if (data.isComplete) {
        setStoryComplete(true)
        setStoryCurrentQ('')
      } else {
        setStoryCurrentQ(data.question)
      }
    } catch (err) {
      console.error('Failed to get next question:', err)
    } finally {
      setStoryLoadingQ(false)
    }
  }

  const toggleRecording = () => {
    if (storyRecording) {
      recognitionRef.current?.stop()
      setStoryRecording(false)
    } else {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      if (!SpeechRecognition) {
        alert('Speech recognition is not supported in this browser. Please use Chrome.')
        return
      }
      const recognition = new SpeechRecognition()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-US'

      let finalTranscript = ''
      recognition.onresult = (event: any) => {
        let interim = ''
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript + ' '
          } else {
            interim += event.results[i][0].transcript
          }
        }
        setStoryTranscript((finalTranscript + interim).trim())
      }
      recognition.onerror = () => setStoryRecording(false)
      recognition.onend = () => setStoryRecording(false)

      recognitionRef.current = recognition
      setStoryTranscript('')
      recognition.start()
      setStoryRecording(true)
    }
  }

  const submitAnswer = async () => {
    if (!storyTranscript.trim()) return
    const updatedQA = [...storyQA, { question: storyCurrentQ, answer: storyTranscript.trim() }]
    setStoryQA(updatedQA)
    setStoryTranscript('')
    await fetchNextQuestion(updatedQA)
  }

  const generatePriors = async () => {
    setStoryGenerating(true)
    setError('')
    setResult(null)
    try {
      const res = await fetch('/api/assets/voice/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ conversation: storyQA }),
      })
      const data = await res.json()
      if (data.success) { setResult({ title: data.title, summary: data.summary, priors: data.priors }); onAssetAdded?.() }
      else setError(data.error || 'Failed to extract priors')
    } catch { setError('Could not connect to server') }
    finally {
      setStoryGenerating(false)
      setStoryModalOpen(false)
    }
  }

  const closeStoryModal = () => {
    recognitionRef.current?.stop()
    setStoryModalOpen(false)
    setStoryQA([])
    setStoryCurrentQ('')
    setStoryTranscript('')
    setStoryComplete(false)
  }

  return (
    <ChatProvider existingSessionId={sessionId || undefined} onSessionReady={(id) => { chatSessionIdRef.current = id }}>
    <SessionTitleSync titleRef={titleRef} setTitleValue={setTitleValue} />
    <div className="h-full flex flex-col">
      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto scrollbar-hide">
      <div className="max-w-4xl mx-auto w-full px-6 pt-8 pb-8 space-y-8">
        {/* Title */}
        <div className="pt-10">
          <h1
            ref={titleRef}
            contentEditable
            suppressContentEditableWarning
            spellCheck={false}
            onBlur={() => {
              const text = titleRef.current?.textContent || ''
              setTitleValue(text)
              if (text.trim() && chatSessionIdRef.current) {
                fetch(`/api/osmosis/sessions/${chatSessionIdRef.current}`, {
                  method: 'PATCH',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ title: text.trim() }),
                }).catch(() => {})
              }
            }}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); titleRef.current?.blur() } }}
            className="text-4xl font-bold outline-none cursor-text p-0 m-0 empty:before:content-['New_Page'] empty:before:opacity-20"
            style={{ color: 'var(--op-font-color)' }}
          >
            {titleValue || ''}
          </h1>
        </div>

        {/* Action buttons */}
        <div className="ml-1 flex items-center gap-3">
          {/* Add something new — dropdown */}
          <div className="relative" ref={uploadDropdownRef}>
            <button
              onClick={() => setIsUploadDropdownOpen(!isUploadDropdownOpen)}
              disabled={isAnalyzing}
              className="flex items-center gap-2 px-4 py-2.5 border border-[#E3E2E0] rounded-lg text-sm hover:bg-[#F7F7F5] transition-colors disabled:opacity-50"
              style={{ color: 'var(--op-font-color)', minWidth: 200 }}
            >
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                <path d="M8 3v10M3 8h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
              </svg>
              Add something new
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className={`ml-auto transition-transform ${isUploadDropdownOpen ? 'rotate-180' : ''}`}>
                <path d="M3 4.5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            {isUploadDropdownOpen && (
              <div className="fixed w-56 bg-white border border-[#E3E2E0] rounded-lg shadow-lg py-1"
                style={{
                  zIndex: 9999,
                  top: uploadDropdownRef.current ? uploadDropdownRef.current.getBoundingClientRect().bottom + 4 : 0,
                  left: uploadDropdownRef.current ? uploadDropdownRef.current.getBoundingClientRect().left : 0,
                }}>
                <button onClick={() => { fileInputRef.current?.click(); setIsUploadDropdownOpen(false) }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-[#F7F7F5] transition-colors" style={{ color: 'var(--op-font-color)' }}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 1h5l4 4v9a1 1 0 01-1 1H4a1 1 0 01-1-1V2a1 1 0 011-1z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /><path d="M9 1v4h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  Upload PDF
                </button>
                <button onClick={() => { setLinkType('youtube'); setLinkModalOpen(true); setIsUploadDropdownOpen(false) }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-[#F7F7F5] transition-colors" style={{ color: 'var(--op-font-color)' }}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M14.4 4.6s-.2-1.2-.7-1.7c-.6-.7-1.3-.7-1.7-.7C9.6 2 8 2 8 2s-1.6 0-4 .2c-.3 0-1 0-1.7.7-.5.5-.6 1.7-.6 1.7S1.5 6 1.5 7.4v1.2c0 1.4.2 2.8.2 2.8s.2 1.2.7 1.7c.6.7 1.4.7 1.8.7 1.3.1 4.8.2 4.8.2s2.4 0 4-.2c.3 0 1 0 1.7-.7.5-.5.6-1.7.6-1.7s.2-1.4.2-2.8V7.4c0-1.4-.1-2.8-.1-2.8z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /><path d="M6.5 10V6l4 2-4 2z" fill="currentColor" /></svg>
                  Paste YouTube Link
                </button>
                <button onClick={() => { setLinkType('article'); setLinkModalOpen(true); setIsUploadDropdownOpen(false) }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-[#F7F7F5] transition-colors" style={{ color: 'var(--op-font-color)' }}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6.5 9.5l3-3M7 11l-1.6 1.6a2.12 2.12 0 01-3-3L4 8m5-3l1.6-1.6a2.12 2.12 0 013 3L12 8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  Paste Article Link
                </button>
              </div>
            )}
          </div>

          {/* Share a Learning */}
          <button
            onClick={() => { setStoryModalOpen(true); startStoryFlow() }}
            disabled={isAnalyzing}
            className="flex items-center gap-2 px-4 py-2.5 border border-[#E3E2E0] rounded-lg text-sm hover:bg-[#F7F7F5] transition-colors disabled:opacity-50"
            style={{ color: 'var(--op-font-color)', minWidth: 200 }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 8v0M4 5.5v5M6 3.5v9M8 5v6M10 3.5v9M12 5.5v5M14 8v0" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
            Talk about a learning
          </button>
        </div>

        <input ref={fileInputRef} type="file" accept=".pdf,.txt,.md" className="hidden" onChange={handleFileUpload} />

        {isAnalyzing && (
          <div className="flex items-center gap-2 ml-1">
            <div className="w-3.5 h-3.5 border-2 border-[#6B4F3A]/20 border-t-[#6B4F3A] rounded-full animate-spin" />
            <span className="text-sm" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>Analyzing...</span>
          </div>
        )}

        {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm ml-1">{error}</div>}

        {result && (
          <div className="animate-fade-in space-y-6 ml-1">
            <div>
              <h2 className="text-lg font-bold" style={{ color: 'var(--op-font-color)', opacity: 0.8 }}>{result.title}</h2>
              <p className="text-sm mt-1 leading-relaxed" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>{result.summary}</p>
            </div>
            <div className="space-y-3">
              {result.priors.map((prior, i) => <PriorCard key={i} prior={prior} />)}
            </div>
          </div>
        )}

        {/* Restored priors from session history */}
        {!result && <RestoredPriors />}

      </div>
      {/* Chat messages in scroll area */}
      <ChatMessages />
      </div>

      {/* Chat input — fixed at bottom */}
      <ChatInput />

      {/* Link Modal */}
      {linkModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => !isAnalyzing && setLinkModalOpen(false)} />
          <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold" style={{ color: 'var(--op-font-color)' }}>
                {linkType === 'youtube' ? 'Paste YouTube Link' : 'Paste Article Link'}
              </h3>
              <button onClick={() => { setLinkModalOpen(false); setLinkUrl('') }} className="p-1" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
              </button>
            </div>
            <p className="text-sm mb-4" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>
              {linkType === 'youtube'
                ? 'We\'ll extract the transcript and pull out key insights'
                : 'Works with Goodreads, Letterboxd, IMDB, blogs, and more'}
            </p>
            <input ref={linkInputRef} type="url" value={linkUrl} onChange={e => setLinkUrl(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && linkUrl.trim()) handleLinkSubmit() }}
              placeholder={linkType === 'youtube' ? 'https://youtube.com/watch?v=...' : 'https://www.goodreads.com/book/show/...'} disabled={isAnalyzing}
              className="w-full text-sm px-4 py-3 rounded-lg border border-[#E3E2E0] focus:outline-none focus:border-gray-400 disabled:bg-[#F7F7F5]" />
            <div className="flex justify-end gap-3 mt-5">
              <button onClick={() => { setLinkModalOpen(false); setLinkUrl('') }} className="px-4 py-2 text-sm rounded-lg hover:bg-[#F7F7F5]" style={{ color: 'var(--op-font-color)' }}>Cancel</button>
              <button onClick={handleLinkSubmit} disabled={!linkUrl.trim() || isAnalyzing}
                className="px-5 py-2 text-sm font-medium rounded-lg border border-[#E3E2E0] hover:bg-[#F0EFED] disabled:opacity-40 flex items-center gap-2"
                style={{ color: 'var(--op-font-color)' }}>
                {isAnalyzing && <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>}
                {isAnalyzing ? 'Adding...' : 'Add'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Voice Q&A Modal — same pattern as coach-ai Tell Your Story */}
      {storyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => !storyRecording && !storyGenerating && closeStoryModal()} />
          <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 flex flex-col" style={{ height: '320px' }}>
            <div className="flex items-center justify-between px-6 pt-5 pb-3">
              <div>
                <h3 className="text-lg font-semibold" style={{ color: 'var(--op-font-color)' }}>Talk about a learning</h3>
                {/* Progress dots */}
                <div className="flex gap-1.5 mt-2">
                  {[1, 2, 3].map(step => (
                    <div
                      key={step}
                      className="h-1 rounded-full transition-all"
                      style={{
                        width: step <= storyQA.length + (storyComplete ? 0 : 1) ? 24 : 16,
                        backgroundColor: step <= storyQA.length
                          ? 'var(--op-font-color)'
                          : step === storyQA.length + 1 && !storyComplete
                            ? 'var(--op-font-color)'
                            : 'var(--op-font-color)',
                        opacity: step <= storyQA.length ? 0.6 : step === storyQA.length + 1 && !storyComplete ? 0.3 : 0.1,
                      }}
                    />
                  ))}
                </div>
              </div>
              <button onClick={closeStoryModal} disabled={storyGenerating} className="p-1 disabled:opacity-50" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
              </button>
            </div>

            <div className="px-6 py-5 flex-1">
              {storyLoadingQ ? (
                <div className="flex items-center justify-center py-8">
                  <svg className="w-5 h-5 animate-spin" style={{ color: 'var(--op-font-color)', opacity: 0.4 }} fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                </div>
              ) : storyComplete ? (
                <div className="text-center py-6 space-y-4">
                  <p className="text-sm" style={{ color: 'var(--op-font-color)' }}>Great — that's enough to extract your priors!</p>
                  <button onClick={generatePriors} disabled={storyGenerating}
                    className="px-5 py-2.5 text-sm font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800 disabled:opacity-40 flex items-center gap-2 mx-auto">
                    {storyGenerating && <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>}
                    {storyGenerating ? 'Generating...' : 'Extract Priors'}
                  </button>
                </div>
              ) : storyCurrentQ ? (
                <div className="relative h-full">
                  {/* Question — top */}
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--op-font-color)' }}>{storyCurrentQ}</p>

                  {/* Transcript — middle, absolute with scroll */}
                  {storyTranscript && (
                    <div className="absolute top-10 left-0 right-0 bottom-24 overflow-y-auto scrollbar-hide">
                      <p className="text-sm italic" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>{storyTranscript}</p>
                    </div>
                  )}

                  {/* Mic + Next — absolute bottom */}
                  <div className="absolute bottom-6 left-0 right-0 flex items-center justify-center gap-4">
                    <button onClick={toggleRecording}
                      className={`w-12 h-12 rounded-full flex items-center justify-center transition-all ${
                        storyRecording ? 'bg-[#EDEDEC]' : 'bg-[#F7F7F5] hover:bg-[#EDEDEC]'
                      }`} style={{ color: 'var(--op-font-color)' }}>
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 3a4 4 0 014 4v4a4 4 0 11-8 0V7a4 4 0 014-4z" stroke="currentColor" strokeWidth="1.5" /><path d="M6 13a6 6 0 006 6m6-6a6 6 0 01-6 6m0 0v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                    </button>
                    {storyTranscript && !storyRecording && (
                      <button onClick={submitAnswer} className="px-4 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800">Next</button>
                    )}
                  </div>
                  <p className="absolute bottom-0 left-0 right-0 text-center text-xs" style={{ color: 'var(--op-font-color)', opacity: 0.3 }}>
                    {storyRecording ? 'Listening... tap to stop' : 'Tap mic to answer'}
                  </p>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

    </div>
    </ChatProvider>
  )
}

function useSessionTitle(titleRef: React.RefObject<HTMLHeadingElement | null>, setTitleValue: (v: string) => void) {
  const { sessionTitle } = useChatContext()
  useEffect(() => {
    if (sessionTitle && sessionTitle !== 'New Page' && titleRef.current) {
      titleRef.current.textContent = sessionTitle
      setTitleValue(sessionTitle)
    }
  }, [sessionTitle])
}

function SessionTitleSync({ titleRef, setTitleValue }: { titleRef: React.RefObject<HTMLHeadingElement | null>; setTitleValue: (v: string) => void }) {
  useSessionTitle(titleRef, setTitleValue)
  return null
}

function RestoredPriors() {
  const { sessionPriors } = useChatContext()
  if (!sessionPriors || sessionPriors.length === 0) return null

  // Group priors by material_title
  const grouped = new Map<string, any[]>()
  for (const p of sessionPriors) {
    const key = p.material_title || p.source_title || 'Untitled'
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key)!.push(p)
  }

  return (
    <>
      {Array.from(grouped.entries()).map(([title, priors]) => (
        <div key={title} className="animate-fade-in space-y-6 ml-1">
          <div>
            <h2 className="text-sm font-bold tracking-wider" style={{ color: 'var(--op-font-color)', opacity: 0.7 }}>{title}</h2>
          </div>
          <div className="space-y-3">
            {priors.map((prior: any, i: number) => (
              <PriorCard key={i} prior={{
                name: prior.name,
                principle: prior.principle,
                practice: prior.practice,
                trigger: prior.trigger_context,
                source: prior.source,
              }} />
            ))}
          </div>
        </div>
      ))}
    </>
  )
}
