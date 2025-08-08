// frontend/src/scenes/AvatarCreate.tsx
import { useState } from 'react'
import type { FormEvent } from 'react'
import { useNavigate }         from 'react-router-dom'
import { motion }              from 'framer-motion'
import axios                   from 'axios'

import { useAvatar } from '../AvatarContext'
import useSeed from '../SeedContext'

interface SoulSeedRes {
  playerId:     string
  soulSeedId:   string
  initSceneTag: string
}

export default function AvatarCreate() {
  const nav              = useNavigate()
  const { setAvatarUrl } = useAvatar()
  const { hasSeed, setSeed } = useSeed()

  const [name,    setName]    = useState('')
  const [preset,  setPreset]  = useState('Visionary Dreamer')
  const [custom,  setCustom]  = useState('')
  const [file,    setFile]    = useState<File | null>(null)
  const [preview, setPreview] = useState('')
  const [err,     setErr]     = useState('')
  const [busy,    setBusy]    = useState(false)

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) {
      setFile(f)
      setPreview(URL.createObjectURL(f))
    }
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setErr('')
    setBusy(true)

    // 1) Validation
    if (!name.trim()) {
      setErr('Name is required')
      setBusy(false)
      return
    }
    if (!preset && !custom.trim()) {
      setErr('Pick or describe an archetype')
      setBusy(false)
      return
    }

    /* 2 ─ create soul-seed */
    let seed: SoulSeedRes
    try {
      console.log('📤 POST /soulseed', {
        playerName:       name.trim(),
        archetypePreset:  preset,
        archetypeCustom:  custom.trim() || null,
        avatarReferenceUrl: null,
      })
      const { data } = await axios.post<SoulSeedRes>(
        '/soulseed',
        {
          playerName       : name.trim(),
          archetypePreset  : preset,
          archetypeCustom  : custom.trim() || null,
          avatarReferenceUrl: null,
        }
      )
      seed = data
      console.log('✅ soul-seed response:', data)

      // —– persist into localStorage (so SceneView can read them) —–
      localStorage.setItem('playerId',     seed.playerId)
      localStorage.setItem('soulSeedId',   seed.soulSeedId)
      localStorage.setItem('initSceneTag', seed.initSceneTag)

      // —– flip your React context + localStorage flag —–
      setSeed(seed.soulSeedId)
      console.log('▶ hasSeed in context now:', hasSeed)
    } catch (err) {
      console.error('❌ soul-seed creation failed:', err)
      setErr('Failed to create profile, please retry.')
      setBusy(false)
      return
    }

    /* 3 ─ avatar upload (optional) */
    if (file) {
      const fd = new FormData()
      fd.append('playerId', seed.playerId)
      fd.append('file', file)

      try {
        console.log('📤 uploading avatar file…', file)
        const resp = await axios.post<{ url: string }>(
          '/avatar/upload',
          fd,
          { headers: { 'Content-Type': 'multipart/form-data' } }
        )
        console.log('✅ upload response:', resp.data)
        setAvatarUrl(resp.data.url)
        localStorage.setItem('avatarUrl', resp.data.url)
      } catch (uploadErr) {
        console.error('❌ avatar upload failed:', uploadErr)
        // don't block the flow on upload failure
      }
    }

    /* 4 ─ ritual step */
    nav('/ritual', { replace: true })
  }

  return (
    <motion.div
      initial={{ opacity:0, y:10 }}
      animate={{ opacity:1, y:0 }}
      exit={{ opacity:0, y:-10 }}
      transition={{ duration:0.35 }}
      className="max-w-xl mx-auto p-8 space-y-6"
    >
      <h1 className="text-2xl font-semibold text-center">Avatar Creation</h1>

      <form onSubmit={onSubmit} className="space-y-4">
        {/* Name */}
        <div>
          <label className="block mb-1 font-medium">Name</label>
          <input
            className="w-full px-3 py-2 border rounded"
            placeholder="Your name"
            value={name}
            onChange={e => setName(e.target.value)}
          />
        </div>

        {/* Preset */}
        <div>
          <label className="block mb-1 font-medium">Choose an archetype</label>
          <select
            className="w-full px-3 py-2 border rounded"
            value={preset}
            onChange={e => setPreset(e.target.value)}
          >
            <option>Visionary Dreamer</option>
            <option>Stoic Guardian</option>
            <option>Curious Wanderer</option>
            <option>Ingenious Tactician</option>
          </select>
        </div>

        {/* Custom */}
        <div>
          <label className="block mb-1 font-medium">
            Describe your own archetype (optional)
          </label>
          <textarea
            rows={3}
            className="w-full px-3 py-2 border rounded"
            value={custom}
            onChange={e => setCustom(e.target.value)}
          />
        </div>

        {/* Upload */}
        <div>
          <label className="block mb-1 font-medium">Avatar image (optional)</label>
          <input type="file" accept="image/*" onChange={onFile} />
          {preview && (
            <img
              src={preview}
              className="w-24 h-24 rounded-full mt-2 object-cover"
            />
          )}
        </div>

        {err && <p className="text-red-600">{err}</p>}

        <button
          disabled={busy}
          className={`w-full py-2 text-white rounded shadow ${
            busy
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700'
          }`}
        >
          {busy ? 'Creating…' : 'Confirm Avatar'}
        </button>
      </form>
    </motion.div>
  )
}
