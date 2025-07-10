// frontend/src/main.tsx
import ReactDOM from 'react-dom/client'
import App       from './App'
import { SeedProvider }   from './SeedContext'
import { AvatarProvider } from './AvatarContext'
import './index.css'
import axios from 'axios';

// ← POST ONLY TO “/” SO VITE CAN CATCH IT
axios.defaults.baseURL = '/';

ReactDOM
  .createRoot(document.getElementById('root')!)
  .render(
    <SeedProvider>
      <AvatarProvider>
        <App />
      </AvatarProvider>
    </SeedProvider>
  )
