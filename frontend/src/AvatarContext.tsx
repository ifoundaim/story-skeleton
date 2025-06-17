import { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type AvatarContextValue = {
  avatarUrl: string | null;
  setAvatarUrl: (url: string) => void;
};

const AvatarContext = createContext<AvatarContextValue | undefined>(undefined);

export function AvatarProvider({ children }: { children: ReactNode }) {
  const [avatarUrl, setAvatarUrlState] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem('avatarUrl');
    if (stored) {
      setAvatarUrlState(stored);
    }
  }, []);

  const setAvatarUrl = (url: string) => {
    localStorage.setItem('avatarUrl', url);
    setAvatarUrlState(url);
  };

  return (
    <AvatarContext.Provider value={{ avatarUrl, setAvatarUrl }}>
      {children}
    </AvatarContext.Provider>
  );
}

export function useAvatar() {
  const ctx = useContext(AvatarContext);
  if (ctx) {
    return ctx;
  }
  const stored = localStorage.getItem('avatarUrl');
  const setAvatarUrl = (url: string) => {
    localStorage.setItem('avatarUrl', url);
  };
  return { avatarUrl: stored, setAvatarUrl };
}

export default AvatarContext;
