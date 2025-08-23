import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom';
import { Suspense, lazy, useEffect, useState } from 'react';
import useSeed from './SeedContext';
import ConsequenceToaster from './components/ConsequenceToaster';
import { useConsequenceToasts } from './hooks/useConsequenceToasts';
import { SettingsProvider } from './contexts/SettingsContext';
import SettingsPanel from './components/SettingsPanel';

/* ─── lazy-loaded pages ─────────────────────────────────────────────── */
const AvatarCreate = lazy(() => import('./scenes/AvatarCreate'));
const AvatarBuilder = lazy(() => import('./scenes/AvatarBuilder'));
const Ritual       = lazy(() => import('./scenes/Ritual'));
const Liminal      = lazy(() => import('./scenes/Liminal'));
const SceneView    = lazy(() => import('./scenes/SceneView'));

/* ─── util: always scroll to top on route change ────────────────────── */
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);
  return null;
}

/* ─── app ───────────────────────────────────────────────────────────── */
export default function App() {
  const { hasSeed } = useSeed();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const fallback = (
    <div className="p-8 text-center text-gray-500">Loading…</div>
  );

  return (
    <SettingsProvider>
      <AppContent hasSeed={hasSeed} isSettingsOpen={isSettingsOpen} setIsSettingsOpen={setIsSettingsOpen} fallback={fallback} />
    </SettingsProvider>
  );
}

function AppContent({ hasSeed, isSettingsOpen, setIsSettingsOpen, fallback }: { 
  hasSeed: boolean; 
  isSettingsOpen: boolean; 
  setIsSettingsOpen: (open: boolean) => void; 
  fallback: React.ReactNode;
}) {
  const { toasts, dismissToast } = useConsequenceToasts();

  return (
    <BrowserRouter>
      <ScrollToTop />
      <ConsequenceToaster toasts={toasts} onToastDismiss={dismissToast} />
        
        {/* Settings Button */}
        <button
          onClick={() => setIsSettingsOpen(true)}
          className="fixed bottom-4 left-4 z-40 p-3 bg-gray-800 text-white rounded-full shadow-lg hover:bg-gray-700 transition-colors"
          aria-label="Open settings"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </button>

        <SettingsPanel isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />
        
        <Suspense fallback={fallback}>
          <Routes>
          {/* Default: if they've got a seed, go straight to liminal; otherwise start avatar */}
          <Route
            path="/"
            element={
              hasSeed
                ? <Navigate to="/liminal" replace />
                : <Navigate to="/avatar" replace />
            }
          />

          {/* Avatar creation */}
          <Route
            path="/avatar"
            element={<AvatarCreate />}
          />
          <Route path="/avatar/builder" element={<AvatarBuilder />} />
          <Route
            path="/liminal"
            element={
              hasSeed
                ? <Liminal />
                : <Navigate to="/avatar" replace />
            }
          />

          {/* Ritual: only after creating avatar */}
          <Route
            path="/ritual"
            element={
              hasSeed
                ? <Ritual />
                : <Navigate to="/avatar" replace />
            }
          />

          {/* Liminal: entry point once profile + ritual are done */}
          <Route
            path="/liminal"
            element={
              hasSeed
                ? <Liminal />
                : <Navigate to="/avatar" replace />
            }
          />

          {/* Full scene explorer */}
          <Route
            path="/scene"
            element={
              hasSeed
                ? <SceneView />
                : <Navigate to="/avatar" replace />
            }
          />

          {/* Catch-all: send back to “home” logic */}
          <Route
            path="/*"
            element={
              hasSeed
                ? <Navigate to="/liminal" replace />
                : <Navigate to="/avatar" replace />
            }
          />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
