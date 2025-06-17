import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { AvatarProvider } from "./AvatarContext";
import "./index.css";     // leave even if index.css is empty

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AvatarProvider>
      <App />
    </AvatarProvider>
  </React.StrictMode>
);
