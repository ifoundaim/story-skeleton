// frontend/src/SeedContext.tsx
import {
  createContext,
  useContext,
  useMemo,
  useState,
  useCallback,
} from 'react'
import type { ReactNode } from 'react'

interface SeedCtx {
  /** True if a soulSeedId exists in memory or localStorage */
  hasSeed: boolean
  /** Store or clear a soulSeedId and broadcast the change */
  setSeed: (id: string | null) => void
}

const SeedContext = createContext<SeedCtx | undefined>(undefined)

export function SeedProvider({ children }: { children: ReactNode }) {
  const [seedId, setSeedId] = useState<string | null>(() => {
    try {
      return localStorage.getItem('soulSeedId')
    } catch {
      return null
    }
  })

  const setSeed = useCallback((id: string | null) => {
    try {
      if (id) {
        localStorage.setItem('soulSeedId', id)
      } else {
        localStorage.removeItem('soulSeedId')
      }
    } catch {
      // ignore
    }
    setSeedId(id)
  }, [])

  const value = useMemo<SeedCtx>(
    () => ({
      hasSeed: !!seedId,
      setSeed,
    }),
    [seedId, setSeed]
  )

  return <SeedContext.Provider value={value}>{children}</SeedContext.Provider>
}

export function useSeed(): SeedCtx {
  const ctx = useContext(SeedContext)
  if (!ctx) {
    throw new Error('useSeed must be used within a <SeedProvider>')
  }
  return ctx
}

// Provide a default export alias to avoid import mismatches during hot reloads
export default useSeed
