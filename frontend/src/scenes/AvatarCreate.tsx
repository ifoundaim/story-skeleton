// frontend/src/scenes/AvatarCreate.tsx
import { useState, FormEvent } from 'react'
import { useNavigate }          from 'react-router-dom'
import { motion }               from 'framer-motion'
import { useAvatar }            from '../AvatarContext'

/* ———————————————————————— types ———————————————————————— */
interface SoulSeedRes {
  playerId:    string
  soulSeedId:  string
  initSceneTag: string
}

/* ———————————————————————— component ———————————————————————— */
export default function AvatarCreate () {
  const navigate              = useNavigate()
  const { setAvatarUrl }      = useAvatar()

  const [name,        setName]        = useState('')
  const [preset,      setPreset]      = useState('Visionary Dreamer')
  const [custom,      setCustom]      = useState('')
  const [file,        setFile]        = useState<File | null>(null)
  const [preview,     setPreview]     = useState<string>('')
  const [errorMsg,    setErrorMsg]    = useState('')

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
    let res: Response
    try {
      res = await fetch('/soulseed', {
        method : 'POST',
        headers: { 'Content-Type':'application/json' },
        body   : JSON.stringify({
          playerName     : name.trim(),
          archetypePreset: preset,
          archetypeCustom: custom.trim() || null
        })
      })
    } catch { setErrorMsg('Network error'); return }

    if (!res.ok) {
      setErrorMsg('Could not create profile')
      return
    }
    const data: SoulSeedRes = await res.json()
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
    navigate('/scene')
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
