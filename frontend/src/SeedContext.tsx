// frontend/src/SeedContext.tsx
import {
  createContext,
  useContext,
  useMemo,
  ReactNode,
  useState,
  useCallback,
} from 'react';

type SeedCtx = {
  /** Has the user created a Soul-Seed yet? */
  hasSeed: boolean;
  /** Store (or clear) a new seedId and broadcast the change */
  setSeed: (id: string | null) => void;
};

const Ctx = createContext<SeedCtx | undefined>(undefined);

export function SeedProvider({ children }: { children: ReactNode }) {
  const [seedId, setSeedId] = useState<string | null>(
    () => localStorage.getItem('soulSeedId')
  );

  const setSeed = useCallback((id: string | null) => {
    if (id) {
      localStorage.setItem('soulSeedId', id);
    } else {
      localStorage.removeItem('soulSeedId');
    }
    setSeedId(id);
  }, []);

  /* memo avoids re-renders unless value really changes */
  const value = useMemo(
    () => ({ hasSeed: !!seedId, setSeed }),
    [seedId, setSeed]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSeed() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useSeed must be used inside <SeedProvider>');
  return ctx;
}
