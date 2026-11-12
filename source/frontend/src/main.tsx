import React from "react";
import ReactDOM from "react-dom/client";
import "@fontsource-variable/inter";
import App from "./App";
import { migrateLegacyStorage } from "./lib/storageMigration";
import { ConfirmProvider } from "./components/ConfirmProvider";
import "./index.css";

// Migrate legacy browser keys before any React effect can read release state.
// Storage can be blocked in private/embedded contexts; that must not prevent
// the DebateAI shell from mounting.
try {
  migrateLegacyStorage(window.localStorage);
} catch {
  // Preferences are optional; continue with in-memory defaults.
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfirmProvider>
      <App />
    </ConfirmProvider>
  </React.StrictMode>
);
