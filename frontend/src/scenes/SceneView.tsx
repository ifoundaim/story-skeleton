// frontend/src/scenes/SceneView.tsx
import { useState, useEffect, useCallback } from 'react'
import { useNavigate }                       from 'react-router-dom'
import axios                                 from 'axios'

/* ──────────────────────── types from the API ───────────────────── */
interface SceneFromAPI {
  sceneTag : string
  question : string
  options? : { tag: string; label: string }[] | null
  trust?   : number | null
}

/* ─────────────────── normalised shape for React ────────────────── */
interface Scene {
  sceneTag : string
  question : string
  options  : { tag: string; label: string }[]
  trust    : number
}

/* ---------------------------------------------------------------- */
export default function SceneView() {
  const nav = useNavigate()

  const soulSeedId    = localStorage.getItem('soulSeedId')
  const playerId      = localStorage.getItem('playerId')
  const avatarUrl     = localStorage.getItem('avatarUrl')  ?? '/default-avatar.png'
  const initSceneTag  = localStorage.getItem('initSceneTag') ?? ''   // <─ NEW

  const [scene,    setScene]    = useState<Scene | null>(null)
  const [loading,  setLoading]  = useState(true)
  const [errorMsg, setErrorMsg] = useState('')

  /* ---------- helper turns raw payload into a safe object -------- */
  const normalise = (raw: SceneFromAPI): Scene => ({
    sceneTag : raw.sceneTag,
    question : raw.question ?? '',
    options  : Array.isArray(raw.options) ? raw.options : [],
    trust    : typeof raw.trust === 'number' ? raw.trust : 0,
  })

  /* ------------------------ fetch scene -------------------------- */
  const fetchScene = useCallback(async (tag: string) => {
    if (!soulSeedId) { nav('/avatar'); return }

    setLoading(true); setErrorMsg('')
    try {
      const { data } = await axios.get<SceneFromAPI>(
        `/start?soulSeedId=${soulSeedId}&sceneTag=${encodeURIComponent(tag)}`
      )
      setScene(normalise(data))
    } catch (err) {
      console.error(err)
      setErrorMsg('Failed to load the scene.')
    } finally {
      setLoading(false)
    }
  }, [soulSeedId, nav])

  /* -- init : use initial tag from /soulseed if we have no scene --- */
  useEffect(() => {
    if (!scene) fetchScene(initSceneTag)
  }, [scene, initSceneTag, fetchScene])

  /* ------------------------ choose option ------------------------ */
  const makeChoice = async (choiceTag: string) => {
    if (!playerId || !soulSeedId || !scene) return
    try {
      await axios.post('/choose', {
        playerId,
        soulSeedId,
        sceneTag : scene.sceneTag,
        choiceTag,
      })
      // backend replies with the NEXT scene after processing choice
      const { data } = await axios.get<SceneFromAPI>(
        `/trust?soulSeedId=${soulSeedId}`
      )
      setScene(normalise(data))
    } catch (err) {
      console.error(err)
      setErrorMsg('Something went wrong advancing the story.')
    }
  }

  /* --------------------------- UI states ------------------------- */
  if (loading)
    return <p className="p-8 text-center">Loading your adventure…</p>

  if (errorMsg)
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-red-600">{errorMsg}</p>
        <button onClick={() => fetchScene(scene?.sceneTag ?? initSceneTag)}
                className="px-4 py-2 bg-blue-600 text-white rounded">
          Try again
        </button>
      </div>
    )

  if (!scene) return null                     // should never happen now

  /* -------------------------- render ----------------------------- */
  return (
    <div className="p-8 max-w-xl mx-auto text-center space-y-6">
      {/* avatar */}
      <img src={avatarUrl}
           alt="Your avatar"
           className="mx-auto w-32 h-32 rounded-full shadow object-cover" />

      {/* trust bar */}
      <div className="flex items-center gap-2">
        <span className="font-semibold">Trust:</span>
        <div className="flex-1 h-2 bg-gray-200 rounded overflow-hidden">
          <div className="h-full bg-gray-600"
               style={{ width: `${Math.min(Math.max(scene.trust, 0), 1) * 100}%` }} />
        </div>
        <span className="w-10 text-right">{scene.trust.toFixed(1)}</span>
      </div>

      {/* prompt */}
      <div className="bg-green-100 p-4 rounded shadow whitespace-pre-wrap">
        {scene.question}
      </div>

      {/* options or ending */}
      {scene.options.length ? (
        <div className="space-y-3">
          {scene.options.map(o => (
            <button key={o.tag}
                    onClick={() => makeChoice(o.tag)}
                    className="w-full py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
              {o.label}
            </button>
          ))}
        </div>
      ) : (
        <p className="italic">The End.</p>
      )}

      {/* restart */}
      <button onClick={() => {
                localStorage.clear()
                location.href = '/'
              }}
              className="mt-6 px-4 py-2 bg-gray-200 rounded">
        Restart
      </button>
    </div>
  )
}
