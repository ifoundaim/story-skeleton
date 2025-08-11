// frontend/src/scenes/SceneView.tsx
import { useState, useEffect, useCallback } from 'react'
import { useNavigate, useLocation }         from 'react-router-dom'
import { motion, AnimatePresence }          from 'framer-motion'
import axios                                 from 'axios'
import SoulMapWidget from './SoulMapWidget'
import Dialogue from './Dialogue'
import EmotionGraph from './EmotionGraph'
import NPCChat from '../components/NPCChat'
import SidebarAccordion from '../components/SidebarAccordion'
import NPCProfilesPanel from '../components/NPCProfilesPanel'
import CompanionsPanel from '../components/CompanionsPanel'
import DeltaBadge from '../components/DeltaBadge'

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
  npc_text_dynamic?: string
  npc_dialogue?: { npc_id: string; text: string }[]
  dialogue_type?: string
  soulmap_delta?: Record<string, number> | null
  npcs_present?: string[]
  present_name_map?: Record<string, string>
  beat_id?: string
  beat_tags?: string[]
  scene_phase?: string
}

interface Scene {
  sceneTag: string
  question: string
  options:  { tag: string; label: string }[]
  trust:    number
  npc_text?: string
  npc_text_dynamic?: string
  npc_dialogue?: { npc_id: string; text: string }[]
  dialogue_type?: string
  media:    MediaAssets
  soulmap_delta?: Record<string, number> | null
  npcs_present: string[]
  present_name_map?: Record<string, string>
  beat_id?: string
  beat_tags?: string[]
  scene_phase?: string
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
  const [npcInfoById, setNpcInfoById] = useState<Record<string, { name: string; trust: number }>>({})
  const [npcText, setNpcText] = useState('')
  const [imageLoaded, setImageLoaded] = useState(false)
  const [audioPlaying, setAudioPlaying] = useState(false)
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null)
  const [showMemory, setShowMemory] = useState(false)
  const [memoryRecap, setMemoryRecap] = useState<string | null>(null)
  const [memoryLoading, setMemoryLoading] = useState(false)

  // Add test dialogue state
  const [testDialogue, setTestDialogue] = useState<string | null>(null)
  const [testDialogueLoading, setTestDialogueLoading] = useState(false)

  // Animation states
  const [isTransitioning, setIsTransitioning] = useState(false)
  // @ts-ignore - nextScene is used for transition state management
  const [nextScene, setNextScene] = useState<Scene | null>(null)
  const [sceneKey, setSceneKey] = useState(0) // Force re-render of scene content
  
  // Delta badge states
  const [deltaBadges, setDeltaBadges] = useState<Array<{trait: string, value: number, id: string}>>([])
  
  // Soulmap refresh state
  const [soulmapRefreshKey, setSoulmapRefreshKey] = useState(0)

  // Animation variants
  const sceneVariants = {
    initial: { 
      opacity: 0, 
      y: 20,
      scale: 0.95
    },
    animate: { 
      opacity: 1, 
      y: 0,
      scale: 1,
      transition: {
        duration: 0.6,
        ease: [0.25, 0.46, 0.45, 0.94]
      }
    },
    exit: { 
      opacity: 0, 
      y: -20,
      scale: 0.95,
      transition: {
        duration: 0.4,
        ease: [0.25, 0.46, 0.45, 0.94]
      }
    }
  }

  const imageVariants = {
    initial: { 
      opacity: 0, 
      scale: 0.8,
      filter: 'blur(4px)'
    },
    animate: { 
      opacity: 1, 
      scale: 1,
      filter: 'blur(0px)',
      transition: {
        duration: 0.8,
        ease: [0.25, 0.46, 0.45, 0.94],
        delay: 0.2
      }
    }
  }

  const choiceVariants = {
    initial: { 
      opacity: 0, 
      y: 10 
    },
    animate: { 
      opacity: 1, 
      y: 0,
      transition: {
        duration: 0.4,
        ease: 'easeOut'
      }
    },
    hover: { 
      scale: 1.02,
      y: -2,
      boxShadow: '0 8px 25px rgba(0,0,0,0.15)',
      transition: {
        duration: 0.2,
        ease: 'easeInOut'
      }
    },
    tap: { 
      scale: 0.98,
      transition: {
        duration: 0.1
      }
    }
  }

  const normalise = (raw: SceneFromAPI): Scene => ({
    sceneTag: raw.sceneTag,
    question: raw.text || '',
    options : Array.isArray(raw.choices) ? raw.choices : [],
    trust   : typeof raw.trust === 'number' ? raw.trust : 0,
    npc_text_dynamic: raw.npc_text_dynamic,
    npc_dialogue: Array.isArray(raw.npc_dialogue) ? raw.npc_dialogue : [],
    dialogue_type: raw.dialogue_type || 'single',
    media   : raw.media || { images: [], audio: [] },
    npcs_present: Array.isArray(raw.npcs_present) ? raw.npcs_present : [],
    present_name_map: raw.present_name_map || {},
    beat_id: raw.beat_id,
    beat_tags: Array.isArray(raw.beat_tags) ? raw.beat_tags : [],
    scene_phase: raw.scene_phase
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
      const normalized = normalise(data)
      setScene(normalized)
      // Persist current scene tag to survive refreshes
      try { localStorage.setItem('lastSceneTag', normalized.sceneTag) } catch {}
      setImageLoaded(false) // Reset image loading state for new scene
      setSceneKey(prev => prev + 1) // Force re-render for animations
    } catch (err) {
      console.error('❌ Failed to load the scene:', err)
      setErrorMsg('Failed to load the scene.')
    } finally {
      setLoading(false)
    }
  }, [playerId, soulSeedId, nav])

  const fetchMemory = useCallback(async () => {
    if (!playerId) return
    setMemoryLoading(true)
    try {
      const { data } = await axios.get(`/memory/${playerId}`)
      setMemoryRecap(data.recap || '')
    } catch (err) {
      setMemoryRecap('Failed to load memory recap.')
    } finally {
      setMemoryLoading(false)
    }
  }, [playerId])

  // Add test dialogue function
  const testNpcDialogue = async () => {
    if (!playerId) return
    setTestDialogueLoading(true)
    try {
      const { data } = await axios.get(`/test/npc-dialogue/${playerId}`)
      setTestDialogue(data.dialogue)
      console.log('✅ Test NPC dialogue generated:', data.dialogue)
    } catch (err) {
      console.error('❌ Failed to generate test NPC dialogue:', err)
      setTestDialogue('Failed to generate test dialogue')
    } finally {
      setTestDialogueLoading(false)
    }
  }

  useEffect(() => {
    if (!scene) fetchScene(firstTag)
    // Fetch NPC trust
    if (playerId) {
      fetch(`/npc/${playerId}`)
        .then(res => res.json())
        .then(npcs => {
          if (Array.isArray(npcs) && npcs.length > 0) {
            setNpcTrust(npcs[0].trust)
            const map: Record<string, { name: string; trust: number }> = {}
            for (const n of npcs) {
              map[String(n.id)] = { name: n.name || String(n.id).slice(0,8), trust: typeof n.trust === 'number' ? n.trust : 0 }
            }
            setNpcInfoById(map)
          }
        })
        .catch(() => {
          setNpcTrust(0)
          setNpcInfoById({})
        })
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

  useEffect(() => {
    if (showMemory && memoryRecap === null && !memoryLoading) {
      fetchMemory()
    }
  }, [showMemory, memoryRecap, memoryLoading, fetchMemory])

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

  // Helper: detect UUID-like strings (to avoid showing raw codes as names)
  const isUuidLike = (s?: string) => !!s && /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i.test(s)

  const makeChoice = async (choiceTag: string) => {
    if (!playerId || !soulSeedId || !scene || isTransitioning) return
    
    setErrorMsg('')
    setIsTransitioning(true)
    
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
      const nextSceneData = normalise(nextRaw)
      try { localStorage.setItem('lastSceneTag', nextSceneData.sceneTag) } catch {}

      console.log('📤 GET /trust', { soulSeedId })
      const { data: trustRaw } = await axios.get<{ trust: number }>(
        `/trust?soulSeedId=${encodeURIComponent(soulSeedId)}`
      )
      console.log('✅ /trust response', trustRaw)

      const finalNextScene = { ...nextSceneData, trust: trustRaw.trust }
      setNextScene(finalNextScene)
      
      // Handle soulmap delta badges
      if (nextRaw.soulmap_delta) {
        const deltas = Object.entries(nextRaw.soulmap_delta)
          .filter(([, value]) => Math.abs(value) > 0.01)
          .map(([trait, value]) => ({
            trait: trait.replace(/_/g, ' '),
            value: value as number,
            id: `${trait}-${Date.now()}-${Math.random()}`
          }))
        
        if (deltas.length > 0) {
          setDeltaBadges(deltas)
          
          // Clear badges after 2 seconds to give time to see them
          setTimeout(() => {
            setDeltaBadges([])
          }, 2000)
          
          // Refresh soulmap data after a short delay to show updated values
          setTimeout(() => {
            setSoulmapRefreshKey(prev => prev + 1)
          }, 1000) // Refresh soulmap 1 second after badges appear
        }
      }
      
      // Delay scene update to allow for delta badges to be visible
      setTimeout(() => {
        setScene(finalNextScene)
        setImageLoaded(false) // Reset image loading for new scene
        setSceneKey(prev => prev + 1) // Force re-render
        setNextScene(null)
        setIsTransitioning(false)
      }, 2500) // Wait 2.5 seconds to ensure badges are visible for 2 seconds
      
    } catch (err) {
      console.error('❌ Something went wrong advancing the story:', err)
      setErrorMsg('Something went wrong advancing the story.')
      setIsTransitioning(false)
      setNextScene(null)
    }
  }

  // On mount, restore last scene if we have it and no state was passed
  useEffect(() => {
    if (!scene) {
      const saved = localStorage.getItem('lastSceneTag')
      const tagToLoad = saved || firstTag
      if (tagToLoad) {
        fetchScene(tagToLoad)
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (loading) {
    return (
      <div className="p-8 text-center">
        <p>Loading your adventure…</p>
        <div style={{background: 'red', color: 'white', padding: 4, marginTop: 8}}>DEBUG: Loading state</div>
      </div>
    )
  }

  if (errorMsg) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-red-600">{errorMsg}</p>
        <div style={{background: 'red', color: 'white', padding: 4}}>DEBUG: Error state</div>
        <button
          onClick={() => fetchScene(scene?.sceneTag ?? firstTag)}
          className="px-4 py-2 bg-blue-600 text-white rounded"
        >
          Try again
        </button>
      </div>
    )
  }

  if (!scene) {
    return (
      <div className="p-8 text-center">
        <div style={{background: 'red', color: 'white', padding: 4}}>DEBUG: No scene state</div>
      </div>
    )
  }

  return (
    <>
      <div style={{background: 'yellow', color: 'black', padding: 8}}>DEBUG: SceneView Rendered</div>
      <div className="scene-view-container min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-100 flex flex-col lg:flex-row">
        <div className="scene-main flex-1 min-h-0">
          <AnimatePresence mode="wait">
            <motion.div 
              key={sceneKey}
              variants={sceneVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              className="p-4 md:p-8 max-w-2xl mx-auto text-center space-y-4 md:space-y-6 h-full overflow-y-auto"
              style={{ scrollBehavior: 'smooth' }}
            >
            <motion.img
              src={avatarUrl}
              alt="Your avatar"
              className="mx-auto w-24 h-24 md:w-32 md:h-32 rounded-full shadow-lg object-cover"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.1, duration: 0.5 }}
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
              <div className="scene-image-container relative">
                <motion.img
                  src={scene.media.images[0]}
                  alt="Scene illustration"
                  variants={imageVariants}
                  initial="initial"
                  animate={imageLoaded ? "animate" : "initial"}
                  className="mx-auto w-full max-w-md h-48 md:h-64 object-cover rounded-lg shadow-lg"
                  onLoad={handleImageLoad}
                  onError={handleImageError}
                  style={{ willChange: 'transform, opacity, filter' }}
                />
                {!imageLoaded && (
                  <motion.div 
                    initial={{ opacity: 1 }}
                    animate={{ opacity: imageLoaded ? 0 : 1 }}
                    className="absolute inset-0 mx-auto w-full h-64 bg-gray-200 rounded-lg flex items-center justify-center"
                  >
                    <p className="text-gray-500">Loading scene image...</p>
                  </motion.div>
                )}
                
                {/* Delta Badges Container - Overlay on Image */}
                <div 
                  className="absolute inset-0 flex items-center justify-center pointer-events-none z-50"
                  aria-live="polite"
                >
                  <AnimatePresence>
                    {deltaBadges.map((badge) => (
                      <DeltaBadge
                        key={badge.id}
                        trait={badge.trait}
                        value={badge.value}
                      />
                    ))}
                  </AnimatePresence>
                </div>
              </div>
            )}
            
            {/* Delta Badges Container - For when no image is present */}
            {scene.media.images.length === 0 && (
              <div 
                className="relative flex items-center justify-center pointer-events-none z-50"
                aria-live="polite"
              >
                <AnimatePresence>
                  {deltaBadges.map((badge) => (
                    <DeltaBadge
                      key={badge.id}
                      trait={badge.trait}
                      value={badge.value}
                    />
                  ))}
                </AnimatePresence>
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
              <motion.div 
                className="space-y-3"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.4, staggerChildren: 0.1 }}
              >
                {scene.options.map((o, index) => (
                  <motion.button
                    key={o.tag}
                    variants={choiceVariants}
                    initial="initial"
                    animate="animate"
                    whileHover="hover"
                    whileTap="tap"
                    onClick={() => makeChoice(o.tag)}
                    disabled={isTransitioning}
                    className={`w-full py-3 px-4 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg font-medium shadow-md transition-all duration-200 ${
                      isTransitioning ? 'opacity-50 cursor-not-allowed' : 'hover:from-blue-700 hover:to-blue-800'
                    }`}
                    style={{ 
                      willChange: 'transform, box-shadow',
                      animationDelay: `${index * 0.1}s`
                    }}
                  >
                    {o.label}
                  </motion.button>
                ))}
              </motion.div>
            ) : (
              <motion.p 
                className="italic text-gray-600"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
              >
                The End.
              </motion.p>
            )}

            <motion.button
              onClick={() => {
                localStorage.clear()
                window.location.href = '/'
              }}
              className="mt-6 px-4 py-2 bg-gray-200 rounded hover:bg-gray-300 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Restart
            </motion.button>

            {/* Start fresh via Director: clears server story state then navigates to Ritual */}
            <motion.button
              onClick={async () => {
                try {
                  const soulSeedId = localStorage.getItem('soulSeedId') || ''
                  if (soulSeedId) {
                    await fetch('/restart', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ soulSeedId })
                    })
                  }
                  // Keep profile; client-side navigate to Ritual to regenerate story via Director
                  nav('/ritual', { replace: true })
                } catch (e) {
                  console.error('Failed to restart via Director', e)
                  nav('/ritual', { replace: true })
                }
              }}
              className="mt-3 ml-2 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              Start Fresh (Director)
            </motion.button>
            </motion.div>
          </AnimatePresence>
        </div>
        <div className="scene-sidebar w-full lg:w-80 lg:max-w-sm p-4 lg:ml-4 bg-white/50 backdrop-blur-sm rounded-lg lg:rounded-none border-t lg:border-t-0 lg:border-l border-gray-200 relative">
          <SidebarAccordion
            sections={[
              {
                id: 'beat-info',
                title: 'Story Beat (Debug)',
                defaultOpen: false,
                content: (
                  <div className="text-sm space-y-2">
                    {scene.beat_id && (
                      <div>
                        <span className="font-semibold text-gray-600">Beat ID:</span>
                        <div className="bg-blue-50 px-2 py-1 rounded text-blue-800 font-mono text-xs mt-1">
                          {scene.beat_id}
                        </div>
                      </div>
                    )}
                    {scene.scene_phase && (
                      <div>
                        <span className="font-semibold text-gray-600">Phase:</span>
                        <div className="bg-green-50 px-2 py-1 rounded text-green-800 font-mono text-xs mt-1">
                          {scene.scene_phase}
                        </div>
                      </div>
                    )}
                    {scene.beat_tags && scene.beat_tags.length > 0 && (
                      <div>
                        <span className="font-semibold text-gray-600">Tags:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {scene.beat_tags.map((tag, idx) => (
                            <span key={idx} className="bg-purple-50 text-purple-700 px-2 py-1 rounded text-xs">
                              {tag}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                    {!scene.beat_id && !scene.scene_phase && (!scene.beat_tags || scene.beat_tags.length === 0) && (
                      <div className="text-gray-500 italic text-xs">
                        No beat information available (likely legacy/LLM-generated scene)
                      </div>
                    )}
                  </div>
                )
              },
              {
                id: 'profiles',
                title: 'NPCs in Scene',
                defaultOpen: true,
                content: (
                  <NPCProfilesPanel presentNpcIds={scene.npcs_present || []} npcInfoById={npcInfoById} nameMap={scene.present_name_map} />
                )
              },
              {
                id: 'chat',
                title: 'NPC Chat',
                content: (
                  <div>
                    {/* NPC Chat panels for NPCs present via dialogue entries */}
                    {Array.isArray(scene.npc_dialogue) && scene.npc_dialogue.length > 0 && playerId && (
                      <div className="mt-2 space-y-3">
                        {scene.npc_dialogue.slice(0,2).map((entry, idx) => (
                          <NPCChat
                            key={`${entry.npc_id}-${idx}`}
                            playerId={playerId}
                            npcId={entry.npc_id}
                             npcName={scene.present_name_map?.[entry.npc_id] || (!isUuidLike(npcInfoById[entry.npc_id]?.name) ? npcInfoById[entry.npc_id]?.name : entry.npc_id.slice(0,8))}
                            sceneTag={scene.sceneTag}
                          />
                        ))}
                      </div>
                    )}
                    {/* If no dialogue, still render chat boxes for present NPCs */}
                    {(!scene.npc_dialogue || scene.npc_dialogue.length === 0) && scene.npcs_present && scene.npcs_present.length > 0 && playerId && (
                      <div className="mt-2 space-y-3">
                        {scene.npcs_present.slice(0,2).map((npcId, idx) => (
                          <NPCChat
                            key={`${npcId}-${idx}`}
                            playerId={playerId}
                            npcId={npcId}
                              npcName={scene.present_name_map?.[npcId] || (!isUuidLike(npcInfoById[npcId]?.name) ? npcInfoById[npcId]?.name : npcId.slice(0,8))}
                            sceneTag={scene.sceneTag}
                          />
                        ))}
                      </div>
                    )}
                  </div>
                )
              },
              {
                id: 'soulmap',
                title: 'Soul Map',
                content: <SoulMapWidget playerId={playerId || 'demo'} refreshKey={soulmapRefreshKey} />
              },
              {
                id: 'companions',
                title: 'Companions',
                content: (
                  <CompanionsPanel companions={(Object.entries(npcInfoById).map(([id, info]) => ({ id, name: info.name, trust: info.trust })))} />
                )
              },
              {
                id: 'emotions',
                title: 'Emotion Graph',
                content: <EmotionGraph playerId={playerId || 'demo'} />
              },
              {
                id: 'memory',
                title: 'Memory Recap',
                content: (
                  <div>
                    <button
                      className="mt-2 mb-2 px-3 py-1 bg-yellow-200 rounded hover:bg-yellow-300 w-full text-left"
                      onClick={() => setShowMemory(m => !m)}
                    >
                      {showMemory ? 'Hide Memory' : 'View Memory'}
                    </button>
                    {showMemory && (
                      <div className="bg-white border border-yellow-400 rounded p-3 mb-2 max-h-64 overflow-y-auto text-sm whitespace-pre-line">
                        {memoryLoading ? 'Loading memory recap...' : (memoryRecap || 'No recap available.')}
                      </div>
                    )}
                  </div>
                )
              }
            ]}
          />
        </div>
      </div>
    </>
  )
}
