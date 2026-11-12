import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource-variable/inter";
import App from "./App";
import { migrateLegacyStorage } from "./lib/storageMigration";
import { ConfirmProvider } from "./components/ConfirmProvider";
import "./index.css";

// Migrate legacy browser keys before any React effect can read release state.
// This keeps old DebateAI/Backchannel preferences visible on first render.
migrateLegacyStorage(window.localStorage);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfirmProvider>
      <App />
    </ConfirmProvider>
  </React.StrictMode>
);
