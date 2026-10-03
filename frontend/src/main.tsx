import { createRoot } from "react-dom/client";
import App from "./App";
import { createAdapter } from "./api/client";
import "./style.css";
const root = createRoot(document.getElementById("root")!);
try {
  const adapter = createAdapter();
  root.render(<App adapter={adapter} />);
} catch {
  root.render(
    <main className="start-panel">
      <h1>Check the frontend configuration</h1>
      <p role="alert">
        Set VITE_API_MODE to demo or http, then restart Vite. No conversation
        has been started.
      </p>
    </main>,
  );
}
