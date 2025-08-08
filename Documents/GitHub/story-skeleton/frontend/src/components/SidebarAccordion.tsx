import React, { useState } from 'react'

export default function SidebarAccordion({
  sections
}: {
  sections: { id: string; title: string; content: React.ReactNode; defaultOpen?: boolean }[]
}) {
  const [openIds, setOpenIds] = useState<Set<string>>(new Set(sections.filter(s => s.defaultOpen).map(s => s.id)))

  const toggle = (id: string) => {
    setOpenIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <div className="space-y-2">
      {sections.map((s) => (
        <div key={s.id} className="border rounded bg-white/70 shadow-sm">
          <button onClick={() => toggle(s.id)} className="w-full text-left px-3 py-2 font-semibold flex items-center justify-between">
            <span>{s.title}</span>
            <span className="text-sm text-gray-500">{openIds.has(s.id) ? '▾' : '▸'}</span>
          </button>
          {openIds.has(s.id) && (
            <div className="px-3 pb-3">
              {s.content}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

