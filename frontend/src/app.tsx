import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Liminal from './scenes/Liminal';
import AvatarCreate from './scenes/AvatarCreate';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/liminal" replace />} />
        <Route path="/liminal" element={<Liminal />} />
        <Route path="/avatar" element={<AvatarCreate />} />
      </Routes>
    </BrowserRouter>
  );
}
