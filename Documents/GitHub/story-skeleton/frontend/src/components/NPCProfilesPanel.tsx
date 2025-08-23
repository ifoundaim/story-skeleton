

type Info = { name: string; trust: number }

const isUuidLike = (s?: string) => !!s && /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i.test(s)

export default function NPCProfilesPanel({ presentNpcIds, npcInfoById, nameMap }: { presentNpcIds: string[]; npcInfoById: Record<string, Info>; nameMap?: Record<string, string> }) {
  // Only show entries that are actually present in the scene AND have a resolved, non-UUID-like name.
  const displayNpcIds = (presentNpcIds || []).filter((id) => {
    // Must be in presentNpcIds (actually present in scene)
    if (!presentNpcIds.includes(id)) {
      return false
    }
    // Must have a resolved, non-UUID-like name
    const candidate = nameMap?.[id] || npcInfoById[id]?.name || ''
    return candidate && !isUuidLike(candidate)
  })

  if (!displayNpcIds.length) {
    return <div className="text-sm text-gray-500">None</div>
  }

  return (
    <div className="space-y-3">
      {displayNpcIds.map((id) => {
        const name = nameMap?.[id] || npcInfoById[id]?.name || ''
        const info = npcInfoById[id]
        const trust = info ? Math.min(Math.max(info.trust, 0), 1) : 0
        return (
          <div key={id} className="border rounded p-2 bg-white/70 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="font-semibold">{name}</div>
              <div className="text-xs text-gray-500">{trust.toFixed(2)}</div>
            </div>
            <div className="mt-1 h-2 bg-gray-200 rounded overflow-hidden">
              <div className="h-full bg-blue-500" style={{ width: `${trust * 100}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

