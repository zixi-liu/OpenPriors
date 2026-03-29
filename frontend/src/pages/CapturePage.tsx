import { useState, useRef } from 'react'
import { FileText, Link2, Mic, MicOff, Upload, Loader2 } from 'lucide-react'
import PriorCard from '../components/PriorCard.tsx'

type Tab = 'text' | 'url' | 'voice'

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
  const [tab, setTab] = useState<Tab>('text')
  const [textInput, setTextInput] = useState('')
  const [urlInput, setUrlInput] = useState('')
  const [sourceHint, setSourceHint] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<CaptureResult | null>(null)
  const [error, setError] = useState('')

  // Voice state
  const [recording, setRecording] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const tabs = [
    { id: 'text' as Tab, label: 'Text', icon: FileText },
    { id: 'url' as Tab, label: 'URL', icon: Link2 },
    { id: 'voice' as Tab, label: 'Voice', icon: Mic },
  ]

  const captureText = async () => {
    if (!textInput.trim()) return
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const res = await fetch('/api/priors/capture/text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: textInput, source: sourceHint || undefined }),
      })
      const data = await res.json()
      if (data.success) {
        setResult({ title: data.title, summary: data.summary, priors: data.priors })
        setTextInput('')
        setSourceHint('')
      } else {
        setError(data.error || 'Failed to extract priors')
      }
    } catch {
      setError('Could not connect to server')
    } finally {
      setLoading(false)
    }
  }

  const captureUrl = async () => {
    if (!urlInput.trim()) return
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const res = await fetch('/api/priors/capture/url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: urlInput }),
      })
      const data = await res.json()
      if (data.success) {
        setResult({ title: data.title, summary: data.summary, priors: data.priors })
        setUrlInput('')
      } else {
        setError(data.error || 'Failed to extract priors')
      }
    } catch {
      setError('Could not connect to server')
    } finally {
      setLoading(false)
    }
  }

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream)
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/wav' })
        stream.getTracks().forEach(t => t.stop())
        await uploadAudio(blob)
      }

      mediaRecorder.start()
      setRecording(true)
    } catch {
      setError('Could not access microphone')
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    setRecording(false)
  }

  const uploadAudio = async (blob: Blob) => {
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('audio', blob, 'recording.wav')
      if (sourceHint) formData.append('source', sourceHint)

      const res = await fetch('/api/voice/capture/audio', {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (data.success) {
        setResult({ title: data.title, summary: data.summary, priors: data.priors })
      } else {
        setError(data.error || 'Failed to process audio')
      }
    } catch {
      setError('Could not connect to server')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-6 py-10">
      {/* Header */}
      <div className="mb-8">
        <h2 className="font-serif text-2xl font-semibold text-gray-900">
          Capture a Prior
        </h2>
        <p className="text-gray-500 text-sm mt-1">
          Share what you recently learned. We'll extract actionable principles you can practice.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-[#F0EDE7] rounded-lg p-1 w-fit">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm transition-colors ${
              tab === id
                ? 'bg-white text-gray-900 font-medium shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Input area */}
      <div className="bg-white rounded-xl border border-[#E8DFD0] p-5 mb-6">
        {tab === 'text' && (
          <div className="space-y-3">
            <textarea
              value={textInput}
              onChange={e => setTextInput(e.target.value)}
              placeholder="Paste your notes, book highlights, key takeaways, or just describe what you learned..."
              rows={8}
              className="w-full resize-none text-sm leading-relaxed bg-transparent focus:outline-none placeholder:text-gray-300"
            />
            <input
              type="text"
              value={sourceHint}
              onChange={e => setSourceHint(e.target.value)}
              placeholder="Source (optional) — e.g., 'Atomic Habits by James Clear'"
              className="w-full text-sm px-3 py-2 rounded-lg border border-[#E8DFD0] bg-[#FDFBF7] focus:outline-none focus:border-gray-400 placeholder:text-gray-300"
            />
            <button
              onClick={captureText}
              disabled={loading || !textInput.trim()}
              className="px-5 py-2 rounded-lg bg-gray-900 text-white text-sm font-medium hover:bg-gray-800 disabled:opacity-40 transition-colors flex items-center gap-2"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
              Extract Priors
            </button>
          </div>
        )}

        {tab === 'url' && (
          <div className="space-y-3">
            <input
              type="url"
              value={urlInput}
              onChange={e => setUrlInput(e.target.value)}
              placeholder="Paste a URL — article, blog post, YouTube video..."
              onKeyDown={e => e.key === 'Enter' && captureUrl()}
              className="w-full text-sm px-3 py-2.5 rounded-lg border border-[#E8DFD0] bg-[#FDFBF7] focus:outline-none focus:border-gray-400 placeholder:text-gray-300"
            />
            <button
              onClick={captureUrl}
              disabled={loading || !urlInput.trim()}
              className="px-5 py-2 rounded-lg bg-gray-900 text-white text-sm font-medium hover:bg-gray-800 disabled:opacity-40 transition-colors flex items-center gap-2"
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : <Link2 size={14} />}
              Extract from URL
            </button>
          </div>
        )}

        {tab === 'voice' && (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Hit record and talk about what you just learned. Ramble freely — we'll extract the key insights.
            </p>
            <input
              type="text"
              value={sourceHint}
              onChange={e => setSourceHint(e.target.value)}
              placeholder="What were you learning from? (optional)"
              className="w-full text-sm px-3 py-2 rounded-lg border border-[#E8DFD0] bg-[#FDFBF7] focus:outline-none focus:border-gray-400 placeholder:text-gray-300"
            />
            <div className="flex items-center gap-4">
              <button
                onClick={recording ? stopRecording : startRecording}
                disabled={loading}
                className={`relative w-14 h-14 rounded-full flex items-center justify-center transition-colors ${
                  recording
                    ? 'bg-red-500 text-white'
                    : 'bg-gray-900 text-white hover:bg-gray-800'
                }`}
              >
                {recording && (
                  <span className="absolute inset-0 rounded-full bg-red-500 animate-pulse-ring" />
                )}
                {recording ? <MicOff size={20} /> : <Mic size={20} />}
              </button>
              <span className="text-sm text-gray-400">
                {recording ? 'Recording... tap to stop' : loading ? 'Processing...' : 'Tap to start recording'}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-3 rounded-lg bg-red-50 text-red-600 text-sm">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex items-center gap-3 mb-6 text-gray-400 text-sm">
          <Loader2 size={16} className="animate-spin" />
          Extracting priors from your input...
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="animate-fade-in">
          <div className="mb-4">
            <h3 className="font-serif text-lg font-semibold text-gray-900">
              {result.title}
            </h3>
            <p className="text-sm text-gray-500 mt-1">{result.summary}</p>
          </div>
          <div className="space-y-3">
            {result.priors.map((prior, i) => (
              <PriorCard key={i} prior={prior} />
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-4">
            {result.priors.length} priors saved to ~/.openpriors/priors/
          </p>
        </div>
      )}
    </div>
  )
}

function Sparkles({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" />
    </svg>
  )
}
