import { useState } from 'react'
import { Key } from 'lucide-react'

interface Props {
  onComplete: () => void
}

const providers = [
  { id: 'gemini', name: 'Google Gemini', placeholder: 'AIza...' },
  { id: 'openai', name: 'OpenAI', placeholder: 'sk-...' },
  { id: 'anthropic', name: 'Anthropic', placeholder: 'sk-ant-...' },
]

export default function SetupPage({ onComplete }: Props) {
  const [provider, setProvider] = useState('gemini')
  const [apiKey, setApiKey] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async () => {
    if (!apiKey.trim()) {
      setError('Please enter your API key')
      return
    }
    setLoading(true)
    setError('')

    try {
      const res = await fetch('/api/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, api_key: apiKey }),
      })
      const data = await res.json()
      if (data.success) {
        onComplete()
      } else {
        setError('Setup failed. Please check your API key.')
      }
    } catch {
      setError('Could not connect to server.')
    } finally {
      setLoading(false)
    }
  }

  const selectedProvider = providers.find(p => p.id === provider)!

  return (
    <div className="h-screen flex items-center justify-center bg-[#FDFBF7]">
      <div className="w-full max-w-md px-6">
        {/* Header */}
        <div className="text-center mb-10">
          <h1 className="font-serif text-3xl font-semibold text-gray-900 mb-2">
            OpenPriors
          </h1>
          <p className="text-gray-500 text-sm">
            Turn what you learn into what you do.
            <br />
            Add your API key to get started.
          </p>
        </div>

        {/* Provider selection */}
        <div className="mb-5">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">
            LLM Provider
          </label>
          <div className="flex gap-2">
            {providers.map(p => (
              <button
                key={p.id}
                onClick={() => setProvider(p.id)}
                className={`flex-1 py-2 px-3 rounded-lg text-sm border transition-colors ${
                  provider === p.id
                    ? 'border-gray-900 bg-gray-900 text-white'
                    : 'border-[#E8DFD0] text-gray-600 hover:border-gray-400'
                }`}
              >
                {p.name}
              </button>
            ))}
          </div>
        </div>

        {/* API Key input */}
        <div className="mb-6">
          <label className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2 block">
            API Key
          </label>
          <div className="relative">
            <Key size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder={selectedProvider.placeholder}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              className="w-full pl-9 pr-4 py-2.5 rounded-lg border border-[#E8DFD0] bg-white text-sm focus:outline-none focus:border-gray-400 transition-colors"
            />
          </div>
        </div>

        {error && (
          <p className="text-red-500 text-sm mb-4">{error}</p>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={loading}
          className="w-full py-2.5 rounded-lg bg-gray-900 text-white text-sm font-medium hover:bg-gray-800 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Setting up...' : 'Get Started'}
        </button>

        <p className="text-xs text-gray-400 text-center mt-4">
          Your key is stored locally at ~/.openpriors/config.json
        </p>
      </div>
    </div>
  )
}
