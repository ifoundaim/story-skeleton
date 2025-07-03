// frontend/src/scenes/SceneView.tsx
import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useLocation }         from 'react-router-dom'
import axios                                 from 'axios'
import SoulMapWidget from './SoulMapWidget'
import Dialogue from './Dialogue'

interface MediaAssets {
  images: string[]
  audio: string[]
}

interface SceneFromAPI {
  sceneTag: string
  text:     string
  choices?: { tag: string; label: string }[] | null
  trust?:   number | null
  media?:   MediaAssets
}

interface Scene {
  sceneTag: string
  question: string
  options:  { tag: string; label: string }[]
  trust:    number
  npc_text?: string
  media:    MediaAssets
}

export default function SceneView() {
  const nav      = useNavigate()
  const location = useLocation();
  const state = location.state as { sceneTag?: string } | undefined;

  const soulSeedId   = localStorage.getItem('soulSeedId')
  const playerId     = localStorage.getItem('playerId')
  const avatarUrl    = localStorage.getItem('avatarUrl') ?? '/default-avatar.png'
  const initSceneTag = localStorage.getItem('initSceneTag') ?? ''

  // give priority to the tag passed from Ritual
  const firstTag = state?.sceneTag ?? initSceneTag

  const [scene,    setScene]    = useState<Scene | null>(null)
  const [loading,  setLoading]  = useState(true)
  const [errorMsg, setErrorMsg] = useState('')
  const [npcTrust, setNpcTrust] = useState(0)
  const [npcText, setNpcText] = useState('')
  const [imageLoaded, setImageLoaded] = useState(false)
  const [audioPlaying, setAudioPlaying] = useState(false)
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null)

  const normalise = (raw: SceneFromAPI): Scene => ({
    sceneTag: raw.sceneTag,
    question: raw.text || '',
    options : Array.isArray(raw.choices) ? raw.choices : [],
    trust   : typeof raw.trust === 'number' ? raw.trust : 0,
    media   : raw.media || { images: [], audio: [] }
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
      setImageLoaded(false) // Reset image loading state for new scene
    } catch (err) {
      console.error('❌ Failed to load the scene:', err)
      setErrorMsg('Failed to load the scene.')
    } finally {
      setLoading(false)
    }
  }, [playerId, soulSeedId, nav])

  useEffect(() => {
    if (!scene) fetchScene(firstTag)
    // Fetch NPC trust
    if (playerId) {
      fetch(`/npc/${playerId}`)
        .then(res => res.json())
        .then(npcs => {
          if (Array.isArray(npcs) && npcs.length > 0) setNpcTrust(npcs[0].trust)
        })
        .catch(() => setNpcTrust(0))
    }
  }, [scene, firstTag, fetchScene, playerId])

  useEffect(() => {
    setNpcText(scene?.npc_text || '')
  }, [scene])

  // Handle audio playback
  useEffect(() => {
    if (scene?.media.audio.length && scene.media.audio[0]) {
      const audio = new Audio(scene.media.audio[0])
      audio.loop = true
      setAudioElement(audio)
      
      return () => {
        audio.pause()
        audio.src = ''
      }
    }
  }, [scene?.media.audio])

  const handleImageLoad = () => {
    setImageLoaded(true)
  }

  const handleImageError = () => {
    console.warn('Failed to load scene image')
    setImageLoaded(true) // Still mark as loaded to show fallback
  }

  const toggleAudio = () => {
    if (!audioElement) return
    
    if (audioPlaying) {
      audioElement.pause()
      setAudioPlaying(false)
    } else {
      audioElement.play().catch(err => {
        console.error('Failed to play audio:', err)
      })
      setAudioPlaying(true)
    }
  }

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
    <>
      <div style={{background: 'yellow', color: 'black', padding: 8}}>DEBUG: SceneView Rendered</div>
      <div className="scene-view-container" style={{ display: 'flex' }}>
        <div className="scene-main" style={{ flex: 1 }}>
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

            {/* Scene Image */}
            {scene.media.images.length > 0 && (
              <div className="scene-image-container">
                {console.log('Scene image URL:', scene.media.images[0])}
                <img
                  src={scene.media.images[0]}
                  alt="Scene illustration"
                  className={`mx-auto max-w-full h-64 object-cover rounded-lg shadow-lg transition-opacity duration-300 ${
                    imageLoaded ? 'opacity-100' : 'opacity-0'
                  }`}
                  onLoad={handleImageLoad}
                  onError={handleImageError}
                />
                {!imageLoaded && (
                  <div className="mx-auto w-full h-64 bg-gray-200 rounded-lg flex items-center justify-center">
                    <p className="text-gray-500">Loading scene image...</p>
                  </div>
                )}
              </div>
            )}

            <div className="bg-green-100 p-4 rounded shadow whitespace-pre-wrap">
              {scene.question}
            </div>

            {/* Audio Controls */}
            {scene.media.audio.length > 0 && (
              <div className="audio-controls">
                <button
                  onClick={toggleAudio}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    audioPlaying 
                      ? 'bg-red-600 text-white hover:bg-red-700' 
                      : 'bg-green-600 text-white hover:bg-green-700'
                  }`}
                >
                  {audioPlaying ? '⏸️ Pause OST' : '▶️ Play OST'}
                </button>
              </div>
            )}

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
                window.location.href = '/'
              }}
              className="mt-6 px-4 py-2 bg-gray-200 rounded"
            >
              Restart
            </button>
          </div>
        </div>
        <div className="scene-sidebar" style={{ width: 320, marginLeft: 16, border: '2px solid red' }}>
          <SoulMapWidget playerId={playerId || 'demo'} />
          <Dialogue avatarUrl="/default-npc.png" npcText={npcText} trust={npcTrust} />
        </div>
      </div>
    </>
  )
}
