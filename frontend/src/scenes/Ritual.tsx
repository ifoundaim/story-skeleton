// frontend/src/scenes/Ritual.tsx
import { useState, useEffect, FormEvent } from 'react'
import { useNavigate }                   from 'react-router-dom'
import axios                              from 'axios'

export default function Ritual() {
  const navigate = useNavigate()

  const [ask,   setAsk]   = useState(() => localStorage.getItem('askText')   || '')
  const [seek,  setSeek]  = useState(() => localStorage.getItem('seekText')  || '')
  const [knock, setKnock] = useState(() => localStorage.getItem('knockText') || '')
  const [theme, setTheme] = useState(() => localStorage.getItem('theme')     || '')

  const [error,   setError]   = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)

  useEffect(() => { localStorage.setItem('askText',   ask)   }, [ask])
  useEffect(() => { localStorage.setItem('seekText',  seek)  }, [seek])
  useEffect(() => { localStorage.setItem('knockText', knock) }, [knock])
  useEffect(() => { localStorage.setItem('theme',     theme) }, [theme])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    if (!ask.trim() || !seek.trim() || !knock.trim() || !theme.trim()) {
      setError('All fields are required.')
      setLoading(false)
      return
    }

    const playerId = localStorage.getItem('playerId')
    if (!playerId) {
      setError('Missing player ID. Please create your avatar first.')
      setLoading(false)
      return navigate('/avatar', { replace: true })
    }

    try {
      console.log('📤 POST /ritual', { playerId, ask, seek, knock, theme })
      const { data } = await axios.post<{
        theme: string
        intentVector: number[]
        nextSceneTag: string
      }>('/ritual', {
        playerId,
        askText:   ask.trim(),
        seekText:  seek.trim(),
        knockText: knock.trim(),
        theme:     theme.trim(),
      })
      console.log('✅ /ritual response', data)

      // pass nextSceneTag into SceneView
      navigate('/scene', {
        replace: true,
        state: { sceneTag: data.nextSceneTag },
      })
    } catch (err: any) {
      console.error('❌ Ritual failed:', err)
      const msg = err.response?.data?.detail || 'Failed to perform ritual.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-8 max-w-xl mx-auto">
      <h1 className="text-2xl font-bold mb-6 text-center">🔮 The Ritual</h1>
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Ask */}
        <div>
          <label className="block font-medium mb-1">Ask</label>
          <textarea
            rows={2}
            value={ask}
            onChange={e => setAsk(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>

        {/* Seek */}
        <div>
          <label className="block font-medium mb-1">Seek</label>
          <textarea
            rows={2}
            value={seek}
            onChange={e => setSeek(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>

        {/* Knock */}
        <div>
          <label className="block font-medium mb-1">Knock</label>
          <textarea
            rows={2}
            value={knock}
            onChange={e => setKnock(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>

        {/* Theme */}
        <div>
          <label className="block font-medium mb-1">Theme</label>
          <input
            type="text"
            value={theme}
            onChange={e => setTheme(e.target.value)}
            className="w-full p-2 border rounded"
          />
        </div>

        {error && <p className="text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className={`w-full py-2 text-white rounded ${
            loading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {loading ? 'Summoning…' : 'Continue to Story'}
        </button>
      </form>
    </div>
  )
}
