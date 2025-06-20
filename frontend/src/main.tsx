// frontend/src/main.tsx
import ReactDOM from 'react-dom/client'
import App        from './App'
import { AvatarProvider } from './AvatarContext'

// leave the line below, even if index.css is empty
import './index.css'

const rootEl = document.getElementById('root') as HTMLElement
ReactDOM.createRoot(rootEl).render(
  // You can add <React.StrictMode> here if you like
  <AvatarProvider>
    <App />
  </AvatarProvider>
)
