import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom';
import { Suspense, lazy, useEffect } from 'react';
import { useSeed } from './SeedContext.tsx';

/* ─── lazy-loaded pages ─────────────────────────────────────────────── */
const Liminal      = lazy(() => import('./scenes/Liminal'));
const AvatarCreate = lazy(() => import('./scenes/AvatarCreate'));
const AvatarBuilder = lazy(() => import('./scenes/AvatarBuilder'));
const Ritual       = lazy(() => import('./scenes/Ritual'));
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

  /* simple  «…loading»  fallback while chunks load */
  const fallback = (
    <div className="p-8 text-center text-gray-500">Loading…</div>
  );

  return (
    <BrowserRouter>
      <ScrollToTop />
      <Suspense fallback={fallback}>
        <Routes>
          {/* default → avatar */}
          <Route path="/" element={<Navigate to="/avatar" replace />} />

          <Route path="/liminal" element={<Liminal />} />
          <Route path="/avatar" element={<AvatarCreate />} />
          <Route path="/avatar/builder" element={<AvatarBuilder />} />

          <Route
            path="/ritual"
            element={hasSeed ? <Ritual /> : <Navigate to="/avatar" replace />}
          />
          <Route
            path="/scene"
            element={hasSeed ? <SceneView /> : <Navigate to="/avatar" replace />}
          />

          {/* catch-all → home (avoids “relative splat” warning) */}
          <Route path="/*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
