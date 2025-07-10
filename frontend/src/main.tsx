import ReactDOM from 'react-dom/client';
import App from './App';
import { AvatarProvider } from './AvatarContext';
import { SeedProvider } from './SeedContext.tsx';   // ✅ this now resolves

import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <SeedProvider>
    <AvatarProvider>
      <App />
    </AvatarProvider>
  </SeedProvider>
);