// frontend/src/app.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Liminal      from './scenes/Liminal';
import AvatarCreate from './scenes/AvatarCreate';
import AvatarBuilder from './scenes/AvatarBuilder';
import SceneView    from './scenes/SceneView';

/**
 * Root application router.
 *  • “/scene” is only reachable if a soulSeedId is stored.
 *  • “/”   always sends the user to the liminal screen first.
 */
export default function App() {
  const hasSeed = Boolean(localStorage.getItem('soulSeedId'));

  return (
    <BrowserRouter>
      <Routes>
        {/* landing --> liminal intro */}
        <Route path="/" element={<Navigate to="/liminal" replace />} />

        {/* intro / avatar creation */}
        <Route path="/liminal" element={<Liminal />} />
        <Route path="/avatar" element={<AvatarCreate />} />
        <Route path="/avatar/builder" element={<AvatarBuilder />} />

        {/* guarded story view */}
        <Route
          path="/scene"
          element={hasSeed ? <SceneView /> : <Navigate to="/avatar" replace />}
        />
      </Routes>
    </BrowserRouter>
  );
}
