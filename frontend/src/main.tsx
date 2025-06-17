import "./index.css";

import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
<<<<<<< HEAD
=======
import { AvatarProvider } from "./AvatarContext";
import "./index.css";     // leave even if index.css is empty
>>>>>>> 21591e2d54e369f7ecd73f9b9dec1f71d79d7af7

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AvatarProvider>
      <App />
    </AvatarProvider>
  </React.StrictMode>
);
