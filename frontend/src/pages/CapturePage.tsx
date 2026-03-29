import { useState, useRef, useEffect } from 'react'
import PriorCard from '../components/PriorCard.tsx'

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

export default function CapturePage() {
  const [titleValue, setTitleValue] = useState('')
  const titleRef = useRef<HTMLHeadingElement>(null)

  // Upload
  const [isUploadDropdownOpen, setIsUploadDropdownOpen] = useState(false)
  const uploadDropdownRef = useRef<HTMLDivElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  // Link modal
  const [linkModalOpen, setLinkModalOpen] = useState(false)
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

  // Osmosis
  const [osmosisModalOpen, setOsmosisModalOpen] = useState(false)

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
      const res = await fetch('/api/priors/capture/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text, source: file.name }),
      })
      const data = await res.json()
      if (data.success) setResult({ title: data.title, summary: data.summary, priors: data.priors })
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
      const res = await fetch('/api/priors/capture/url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: linkUrl }),
      })
      const data = await res.json()
      if (data.success) setResult({ title: data.title, summary: data.summary, priors: data.priors })
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
      const res = await fetch('/api/voice/socratic/next-question', {
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
      const res = await fetch('/api/voice/socratic/next-question', {
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
    const combined = storyQA.map(qa => `Q: ${qa.question}\nA: ${qa.answer}`).join('\n\n')
    try {
      const res = await fetch('/api/priors/capture/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: combined, source: 'voice reflection' }),
      })
      const data = await res.json()
      if (data.success) setResult({ title: data.title, summary: data.summary, priors: data.priors })
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
    <div className="flex-1 overflow-y-auto scrollbar-hide">
      <div className="max-w-4xl mx-auto w-full px-6 pt-8 pb-8 space-y-8">
        {/* Title */}
        <div className="pt-10">
          <h1
            ref={titleRef}
            contentEditable
            suppressContentEditableWarning
            spellCheck={false}
            onBlur={() => setTitleValue(titleRef.current?.textContent || '')}
            onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); titleRef.current?.blur() } }}
            className="text-4xl font-bold outline-none cursor-text p-0 m-0"
            style={{ color: 'var(--op-font-color)' }}
          >
            {titleValue || ''}
          </h1>
          {!titleValue && (
            <span className="text-4xl font-bold pointer-events-none select-none absolute"
              style={{ color: 'var(--op-font-color)', opacity: 0.2, marginTop: '-2.5rem' }}>
              Untitled
            </span>
          )}
        </div>

        {/* Action buttons */}
        <div className="ml-1 flex items-center gap-3 flex-wrap">
          {/* Upload Material dropdown */}
          <div className="relative" ref={uploadDropdownRef}>
            <button
              onClick={() => setIsUploadDropdownOpen(!isUploadDropdownOpen)}
              disabled={isAnalyzing}
              className="flex items-center gap-2 px-4 py-2.5 border border-[#E3E2E0] rounded-lg text-sm hover:bg-[#F7F7F5] transition-colors disabled:opacity-50 min-w-[170px]"
              style={{ color: 'var(--op-font-color)' }}
            >
              {isAnalyzing ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              ) : (
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                  <path d="M8 10V3m0 0L5 6m3-3l3 3M3 13h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
              {isAnalyzing ? 'Analyzing...' : 'Upload Material'}
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" className={`transition-transform ${isUploadDropdownOpen ? 'rotate-180' : ''}`}>
                <path d="M3 4.5l3 3 3-3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </button>
            {isUploadDropdownOpen && (
              <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-[#E3E2E0] rounded-lg shadow-lg py-1 z-50">
                <button onClick={() => { fileInputRef.current?.click(); setIsUploadDropdownOpen(false) }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-[#F7F7F5] transition-colors" style={{ color: 'var(--op-font-color)' }}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 1h5l4 4v9a1 1 0 01-1 1H4a1 1 0 01-1-1V2a1 1 0 011-1z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" /><path d="M9 1v4h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  Upload PDF
                </button>
                <button onClick={() => { setLinkModalOpen(true); setIsUploadDropdownOpen(false) }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 text-sm hover:bg-[#F7F7F5] transition-colors" style={{ color: 'var(--op-font-color)' }}>
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6.5 9.5l3-3M7 11l-1.6 1.6a2.12 2.12 0 01-3-3L4 8m5-3l1.6-1.6a2.12 2.12 0 013 3L12 8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
                  Paste Website Link
                </button>
              </div>
            )}
          </div>

          <button onClick={() => { setStoryModalOpen(true); startStoryFlow() }}
            className="flex items-center gap-2 px-4 py-2.5 border border-[#E3E2E0] rounded-lg text-sm hover:bg-[#F7F7F5] transition-colors" style={{ color: 'var(--op-font-color)' }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M8 2.5a3.5 3.5 0 013.5 3.5v2a3.5 3.5 0 11-7 0V6A3.5 3.5 0 018 2.5z" stroke="currentColor" strokeWidth="1.5" /><path d="M5 11.5A4.5 4.5 0 008 13a4.5 4.5 0 003-1.5M8 13v2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
            Share What You Learned
          </button>

          <button onClick={() => setOsmosisModalOpen(true)}
            className="flex items-center gap-2 px-4 py-2.5 border border-[#E3E2E0] rounded-lg text-sm hover:bg-[#F7F7F5] transition-colors" style={{ color: 'var(--op-font-color)' }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M2 4h12M2 8h8M2 12h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /><path d="M13 9l-1.5 1.5L13 12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
            Osmosis Session
          </button>
        </div>

        <input ref={fileInputRef} type="file" accept=".pdf,.txt,.md" className="hidden" onChange={handleFileUpload} />

        {isAnalyzing && (
          <div className="flex items-center gap-2 py-4 ml-1">
            <div className="w-4 h-4 border-2 border-[#6B4F3A]/20 border-t-[#6B4F3A] rounded-full animate-spin" />
            <span className="text-sm" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>Extracting priors from your material...</span>
          </div>
        )}

        {error && <div className="p-3 rounded-lg bg-red-50 text-red-600 text-sm ml-1">{error}</div>}

        {result && (
          <div className="animate-fade-in space-y-6 ml-1">
            <div>
              <h2 className="text-sm font-bold tracking-wider" style={{ color: 'var(--op-font-color)', opacity: 0.7 }}>Extracted Priors</h2>
              <p className="text-sm mt-1" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>{result.summary}</p>
            </div>
            <div className="space-y-3">
              {result.priors.map((prior, i) => <PriorCard key={i} prior={prior} />)}
            </div>
          </div>
        )}
      </div>

      {/* Link Modal */}
      {linkModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => !isAnalyzing && setLinkModalOpen(false)} />
          <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold" style={{ color: 'var(--op-font-color)' }}>Paste Website Link</h3>
              <button onClick={() => { setLinkModalOpen(false); setLinkUrl('') }} className="p-1" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
              </button>
            </div>
            <p className="text-sm mb-4" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>Paste an article, blog post, or any web page</p>
            <input ref={linkInputRef} type="url" value={linkUrl} onChange={e => setLinkUrl(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && linkUrl.trim()) handleLinkSubmit() }}
              placeholder="https://..." disabled={isAnalyzing}
              className="w-full text-sm px-4 py-3 rounded-lg border border-[#E3E2E0] focus:outline-none focus:border-gray-400 disabled:bg-[#F7F7F5]" />
            <div className="flex justify-end gap-3 mt-5">
              <button onClick={() => { setLinkModalOpen(false); setLinkUrl('') }} className="px-4 py-2 text-sm rounded-lg hover:bg-[#F7F7F5]" style={{ color: 'var(--op-font-color)' }}>Cancel</button>
              <button onClick={handleLinkSubmit} disabled={!linkUrl.trim() || isAnalyzing}
                className="px-5 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800 disabled:opacity-40 flex items-center gap-2">
                {isAnalyzing && <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>}
                {isAnalyzing ? 'Adding...' : 'Extract'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Voice Q&A Modal — same pattern as coach-ai Tell Your Story */}
      {storyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => !storyRecording && !storyGenerating && closeStoryModal()} />
          <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 flex flex-col" style={{ height: '400px' }}>
            <div className="flex items-center justify-between px-6 pt-5 pb-3">
              <div>
                <h3 className="text-lg font-semibold" style={{ color: 'var(--op-font-color)' }}>Share What You Learned</h3>
                <p className="text-xs mt-0.5" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>Question {storyQA.length + (storyComplete ? 0 : 1)} of 3</p>
              </div>
              <button onClick={closeStoryModal} disabled={storyGenerating} className="p-1 disabled:opacity-50" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none"><path d="M5 5l10 10M15 5L5 15" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
              </button>
            </div>

            {storyQA.length > 0 && (
              <div className="px-6 max-h-40 overflow-y-auto space-y-3 pb-3 border-b border-[#E3E2E0]">
                {storyQA.map((qa, i) => (
                  <div key={i} className="space-y-1">
                    <p className="text-xs font-medium" style={{ color: 'var(--op-font-color)', opacity: 0.4 }}>Q{i + 1}</p>
                    <p className="text-sm" style={{ color: 'var(--op-font-color)' }}>{qa.question}</p>
                    <p className="text-sm italic" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>{qa.answer}</p>
                  </div>
                ))}
              </div>
            )}

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
                <div className="space-y-5">
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--op-font-color)' }}>{storyCurrentQ}</p>
                  {storyTranscript && (
                    <p className="text-sm italic bg-[#F7F7F5] rounded-lg px-3 py-2" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>{storyTranscript}</p>
                  )}
                  <div className="flex items-center justify-center gap-4">
                    <button onClick={toggleRecording}
                      className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${
                        storyRecording ? 'bg-red-50 text-red-500 ring-4 ring-red-100' : 'bg-[#F7F7F5] hover:bg-[#EDEDEC]'
                      }`} style={storyRecording ? {} : { color: 'var(--op-font-color)' }}>
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 3a4 4 0 014 4v4a4 4 0 11-8 0V7a4 4 0 014-4z" stroke="currentColor" strokeWidth="1.5" /><path d="M6 13a6 6 0 006 6m6-6a6 6 0 01-6 6m0 0v3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" /></svg>
                    </button>
                    {storyTranscript && !storyRecording && (
                      <button onClick={submitAnswer} className="px-4 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800">Next</button>
                    )}
                  </div>
                  <p className="text-center text-xs" style={{ color: 'var(--op-font-color)', opacity: 0.3 }}>
                    {storyRecording ? 'Listening... tap to stop' : 'Tap mic to answer'}
                  </p>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* Osmosis Session Modal */}
      {osmosisModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOsmosisModalOpen(false)} />
          <div className="relative bg-white rounded-xl shadow-xl w-full max-w-md mx-4 p-8 text-center">
            <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--op-font-color)' }}>Osmosis Session</h3>
            <p className="text-sm mb-6" style={{ color: 'var(--op-font-color)', opacity: 0.5 }}>
              AI will help you connect your learning materials with your daily life and goals. Coming soon.
            </p>
            <button onClick={() => setOsmosisModalOpen(false)} className="px-4 py-2 text-sm rounded-lg bg-gray-900 text-white hover:bg-gray-800">Close</button>
          </div>
        </div>
      )}
    </div>
  )
}
