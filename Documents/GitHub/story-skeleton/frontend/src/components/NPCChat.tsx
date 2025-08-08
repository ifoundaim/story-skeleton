import { useState, useRef, useEffect } from 'react'

type Msg = { role: 'user'|'assistant'; content: string }

export default function NPCChat({ playerId, npcId, npcName, sceneTag }: { playerId: string; npcId: string; npcName?: string; sceneTag: string; }) {
  const [messages, setMessages] = useState<Msg[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)

  useEffect(() => { listRef.current?.scrollTo({ top: listRef.current.scrollHeight }) }, [messages])

  async function send() {
    if (!input.trim() || busy) return
    const user = { role: 'user' as const, content: input.trim() }
    setMessages(m => [...m, user])
    setInput('')
    setBusy(true)
    try {
      const res = await fetch('/npc/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ playerId, npcId, sceneTag, message: user.content })
      })
      const json = await res.json()
      const assistant = { role: 'assistant' as const, content: json.reply }
      setMessages(m => [...m, assistant])
    } catch {
      setMessages(m => [...m, { role: 'assistant', content: '(connection error)'}])
    } finally {
      setBusy(false)
    }
  }

  function onKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' && !busy) send()
  }

  return (
    <div className="rounded border p-3 bg-white/70 shadow-sm">
      <div className="font-semibold mb-2">{npcName || npcId.slice(0,8)}</div>
      <div ref={listRef} className="h-40 overflow-y-auto space-y-2 pr-1">
        {messages.map((m, i) => (
          <div key={i} className={m.role==='user' ? 'text-right' : 'text-left'}>
            <span className={m.role==='user' ? 'inline-block bg-blue-100 px-2 py-1 rounded' : 'inline-block bg-gray-100 px-2 py-1 rounded'}>
              {m.content}
            </span>
          </div>
        ))}
      </div>
      <div className="mt-2 flex gap-2">
        <input
          className="flex-1 border rounded px-2 py-1"
          placeholder={`Chat with ${npcName}…`}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={onKey}
          disabled={busy}
        />
        <button className="px-3 py-1 rounded bg-blue-600 text-white disabled:opacity-50" onClick={send} disabled={busy}>Send</button>
      </div>
    </div>
  )
}

