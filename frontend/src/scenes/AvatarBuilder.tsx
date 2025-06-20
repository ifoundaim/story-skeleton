import { useState } from 'react'
import { useAvatar } from '../AvatarContext'

export default function AvatarBuilder () {
  const { setAvatarUrl } = useAvatar()
  const [prompt, setPrompt] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [hair, setHair] = useState(0.5)
  const [eyes, setEyes] = useState(0.5)
  const [body, setBody] = useState(0.5)
  const [outfit, setOutfit] = useState(0.5)
  const [acc, setAcc] = useState(0.5)
  const [preview, setPreview] = useState('')

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
  }

  const handleCreate = async () => {
    const fd = new FormData()
    fd.append('playerId', localStorage.getItem('playerId') || 'guest')
    fd.append('prompt', prompt)
    fd.append('hair', hair.toString())
    fd.append('eyes', eyes.toString())
    fd.append('body', body.toString())
    fd.append('outfit', outfit.toString())
    fd.append('accessories', acc.toString())
    if (file) fd.append('reference', file)

    const res = await fetch('/avatar/create', { method:'POST', body: fd })
    if (res.ok) {
      const data = await res.json()
      setAvatarUrl(data.pngUrl)
      setPreview(data.pngUrl)
    }
  }

  return (
    <div className="space-y-4 p-4 max-w-xl mx-auto">
      <h1 className="text-2xl font-semibold text-center">Avatar Builder</h1>
      <textarea
        className="w-full border p-2"
        rows={3}
        placeholder="Describe your avatar"
        value={prompt}
        onChange={e=>setPrompt(e.target.value)}
      />
      <input type="file" accept="image/*" onChange={handleFile} />
      <div>
        Hair: <input type="range" min={0} max={1} step={0.01} value={hair} onChange={e=>setHair(parseFloat(e.target.value))} />
      </div>
      <div>
        Eyes: <input type="range" min={0} max={1} step={0.01} value={eyes} onChange={e=>setEyes(parseFloat(e.target.value))} />
      </div>
      <div>
        Body: <input type="range" min={0} max={1} step={0.01} value={body} onChange={e=>setBody(parseFloat(e.target.value))} />
      </div>
      <div>
        Outfit: <input type="range" min={0} max={1} step={0.01} value={outfit} onChange={e=>setOutfit(parseFloat(e.target.value))} />
      </div>
      <div>
        Accessories: <input type="range" min={0} max={1} step={0.01} value={acc} onChange={e=>setAcc(parseFloat(e.target.value))} />
      </div>
      <button className="py-2 px-4 bg-blue-600 text-white" onClick={handleCreate}>
        Generate Avatar
      </button>
      {preview && <img src={preview} alt="preview" className="w-48 h-48" />}
    </div>
  )
}
