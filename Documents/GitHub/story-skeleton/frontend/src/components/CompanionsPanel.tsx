import React from 'react'

type Companion = { id: string; name: string; trust: number }

export default function CompanionsPanel({ companions }: { companions: Companion[] }) {
  if (!companions || companions.length === 0) {
    return <div className="text-sm text-gray-500">No companions yet.</div>
  }
  return (
    <div className="space-y-3">
      {companions.map((c) => {
        const clamped = Math.min(Math.max(c.trust, 0), 1)
        return (
          <div key={c.id} className="border rounded p-2 bg-white/70 shadow-sm">
            <div className="flex items-center justify-between">
              <div className="font-semibold">{c.name || c.id.slice(0,8)}</div>
              <div className="text-xs text-gray-500">{clamped.toFixed(2)}</div>
            </div>
            <div className="mt-1 h-2 bg-gray-200 rounded overflow-hidden">
              <div className="h-full bg-emerald-500" style={{ width: `${clamped * 100}%` }} />
            </div>
          </div>
        )
      })}
    </div>
  )
}

