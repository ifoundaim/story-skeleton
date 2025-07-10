// frontend/src/scenes/SceneView.tsx
import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useLocation }         from 'react-router-dom'
import axios                                 from 'axios'

interface SceneFromAPI {
  sceneTag: string
  text:     string
  choices?: { tag: string; label: string }[] | null
  trust?:   number | null
}

interface Scene {
  sceneTag: string
  question: string
  options:  { tag: string; label: string }[]
  trust:    number
}

export default function SceneView() {
  const nav      = useNavigate()
  const { state } = useLocation<{ sceneTag?: string }>()

  const soulSeedId   = localStorage.getItem('soulSeedId')
  const playerId     = localStorage.getItem('playerId')
  const avatarUrl    = localStorage.getItem('avatarUrl') ?? '/default-avatar.png'
  const initSceneTag = localStorage.getItem('initSceneTag') ?? ''

  // give priority to the tag passed from Ritual
  const firstTag = state?.sceneTag ?? initSceneTag

  const [scene,    setScene]    = useState<Scene | null>(null)
  const [loading,  setLoading]  = useState(true)
  const [errorMsg, setErrorMsg] = useState('')

  const normalise = (raw: SceneFromAPI): Scene => ({
    sceneTag: raw.sceneTag,
    question: raw.text || '',
    options : Array.isArray(raw.choices) ? raw.choices : [],
    trust   : typeof raw.trust === 'number' ? raw.trust : 0,
  })

  const fetchScene = useCallback(async (tag: string) => {
    if (!soulSeedId || !playerId) {
      return nav('/avatar', { replace: true })
    }
    console.log('📤 POST /start', { playerId, soulSeedId, sceneTag: tag })
    setLoading(true)
    setErrorMsg('')
    try {
      const { data } = await axios.post<SceneFromAPI>('/start', {
        soulSeedId,
        sceneTag: tag,
      })
      console.log('✅ /start response', data)
      setScene(normalise(data))
    } catch (err) {
      console.error('❌ Failed to load the scene:', err)
      setErrorMsg('Failed to load the scene.')
    } finally {
      setLoading(false)
    }
  }, [playerId, soulSeedId, nav])

  useEffect(() => {
    if (!scene) fetchScene(firstTag)
  }, [scene, firstTag, fetchScene])

  const makeChoice = async (choiceTag: string) => {
    if (!playerId || !soulSeedId || !scene) return
    setErrorMsg('')
    try {
      console.log('📤 POST /choose', {
        playerId,
        soulSeedId,
        sceneTag: scene.sceneTag,
        choiceTag,
      })
      const { data: nextRaw } = await axios.post<SceneFromAPI>('/choose', {
        playerId,
        soulSeedId,
        sceneTag: scene.sceneTag,
        choiceTag,
      })
      console.log('✅ /choose response', nextRaw)
      const nextScene = normalise(nextRaw)

      console.log('📤 GET /trust', { soulSeedId })
      const { data: trustRaw } = await axios.get<{ trust: number }>(
        `/trust?soulSeedId=${encodeURIComponent(soulSeedId)}`
      )
      console.log('✅ /trust response', trustRaw)

      setScene({ ...nextScene, trust: trustRaw.trust })
    } catch (err) {
      console.error('❌ Something went wrong advancing the story:', err)
      setErrorMsg('Something went wrong advancing the story.')
    }
  }

  if (loading) {
    return <p className="p-8 text-center">Loading your adventure…</p>
  }

  if (errorMsg) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-red-600">{errorMsg}</p>
        <button
          onClick={() => fetchScene(scene?.sceneTag ?? firstTag)}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          Try again
        </button>
      </div>
    )
  }

  if (!scene) return null

  return (
    <div className="p-8 max-w-xl mx-auto text-center space-y-6">
      <img
        src={avatarUrl}
        alt="Your avatar"
        className="mx-auto w-32 h-32 rounded-full shadow object-cover"
      />

      <div className="flex items-center gap-2">
        <span className="font-semibold">Trust:</span>
        <div className="flex-1 h-2 bg-gray-200 rounded overflow-hidden">
          <div
            className="h-full bg-gray-600"
            style={{ width: `${Math.min(Math.max(scene.trust, 0), 1) * 100}%` }}
          />
        </div>
        <span className="w-10 text-right">{scene.trust.toFixed(1)}</span>
      </div>

      <div className="bg-green-100 p-4 rounded shadow whitespace-pre-wrap">
        {scene.question}
      </div>

      {scene.options.length ? (
        <div className="space-y-3">
          {scene.options.map(o => (
            <button
              key={o.tag}
              onClick={() => makeChoice(o.tag)}
              className="w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              {o.label}
            </button>
          ))}
        </div>
      ) : (
        <p className="italic">The End.</p>
      )}

      <button
        onClick={() => {
          localStorage.clear()
          location.href = '/'
        }}
        className="mt-6 px-4 py-2 bg-gray-200 rounded"
      >
        Restart
      </button>
    </div>
  )
}
