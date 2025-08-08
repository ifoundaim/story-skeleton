import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom';
import { Suspense, lazy, useEffect } from 'react';
import useSeed from './SeedContext';

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

  const fallback = (
    <div className="p-8 text-center text-gray-500">Loading…</div>
  );

  return (
    <BrowserRouter>
      <ScrollToTop />
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
