// frontend/src/scenes/AvatarCreate.tsx
import { useState, FormEvent } from 'react'
import { motion }               from 'framer-motion'
import axios                    from 'axios'
import { useAvatar }            from '../AvatarContext'

/* ———————————————————————— types ———————————————————————— */
interface SoulSeedRes {
  playerId:    string
  soulSeedId:  string
  initSceneTag: string
}

/* ———————————————————————— component ———————————————————————— */
export default function AvatarCreate () {
  const { setAvatarUrl }      = useAvatar()

  const [name,        setName]        = useState('')
  const [preset,      setPreset]      = useState('Visionary Dreamer')
  const [custom,      setCustom]      = useState('')
  const [file,        setFile]        = useState<File | null>(null)
  const [preview,     setPreview]     = useState<string>('')
  const [errorMsg,    setErrorMsg]    = useState('')
  const [successMsg,  setSuccessMsg]  = useState('')

  /* — uploads — */
  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    setPreview(URL.createObjectURL(f))
  }

  /* — submit — */
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setErrorMsg('')

    if (!name.trim())          { setErrorMsg('Name required');    return }
    if (!preset && !custom)    { setErrorMsg('Pick an archetype'); return }

    /* 1 / create soul-seed profile */
    let res
    try {
      res = await axios.post('/soulseed', {
        playerName     : name.trim(),
        archetypePreset: preset,
        archetypeCustom: custom.trim() || null,
        avatarReferenceUrl: null
      })
    } catch { setErrorMsg('Network error'); return }

    const data: SoulSeedRes = res.data
    localStorage.setItem('soulSeedId', data.soulSeedId)
    localStorage.setItem('playerId',   data.playerId)

    /* 2 / upload avatar (optional) */
    let avatarURL = ''
    if (file) {
      const fd = new FormData()
      fd.append('playerId', data.playerId)
      fd.append('file', file)
      try {
        const r = await fetch('/avatar/upload', { method:'POST', body: fd })
        if (r.ok) {
          const j = await r.json(); avatarURL = j.url
          localStorage.setItem('avatarUrl', avatarURL)
          setAvatarUrl(avatarURL)
        }
      } catch {/* ignore upload failure */}
    }

    /* 3 / go to story */
    setSuccessMsg('Avatar Created!')
    // navigation occurs in live app after confirmation
  }

  /* ———————————————————————— render ———————————————————————— */
  return (
    <motion.div
      initial={{ opacity:0, y:10 }}
      animate={{ opacity:1, y:0 }}
      exit={{ opacity:0, y:-10 }}
      transition={{ duration:0.4 }}
      className="max-w-xl mx-auto p-8 space-y-6"
    >
      <h1 className="text-2xl font-semibold text-center">Avatar Creation</h1>

      {/* form */}
      <form onSubmit={handleSubmit} className="space-y-4">

        {/* name */}
        <div className="space-y-1">
          <label className="block font-medium">Name</label>
          <input
            type="text"
            placeholder="Your Name"
            value={name}
            onChange={e=>setName(e.target.value)}
            className="w-full px-3 py-2 border rounded"
          />
        </div>

        {/* archetype preset */}
        <div className="space-y-1">
          <label className="block font-medium">Choose an archetype</label>
          <select
            value={preset}
            onChange={e=>setPreset(e.target.value)}
            className="w-full px-3 py-2 border rounded"
          >
            <option>Visionary Dreamer</option>
            <option>Stoic Guardian</option>
            <option>Curious Wanderer</option>
            <option>Ingenious Tactician</option>
          </select>
        </div>

        {/* custom archetype */}
        <div className="space-y-1">
          <label className="block font-medium">
            Describe your own archetype (optional)
          </label>
          <textarea
            rows={3}
            value={custom}
            onChange={e=>setCustom(e.target.value)}
            className="w-full px-3 py-2 border rounded"
          />
        </div>

        {/* avatar file */}
        <div className="space-y-1">
          <label className="block font-medium">Avatar image</label>
          <input
            type="file"
            accept="image/*"
            onChange={handleFile}
          />
          {preview && (
            <img
              src={preview}
              alt="preview"
              className="w-24 h-24 rounded-full mt-2 object-cover"
            />
          )}
        </div>

        {/* error */}
        {errorMsg && <p className="text-red-600">{errorMsg}</p>}
        {successMsg && <p className="text-green-600">{successMsg}</p>}

        {/* submit */}
        <button
          type="submit"
          className="w-full py-2 bg-blue-600 text-white rounded shadow hover:bg-blue-700"
        >
          Confirm Avatar
        </button>
      </form>
    </motion.div>
  )
}
