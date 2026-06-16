import { useEffect, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export default function App() {
  const [health, setHealth] = useState({ state: "loading" });

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/health`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => setHealth({ state: "ok", data }))
      .catch((err) => setHealth({ state: "error", message: err.message }));
  }, []);

  return (
    <main>
      <h1>Plastic Gear Tooth Root Stress Tool</h1>
      <p>FE-based tooth root stress optimization of plastic gears.</p>
      <section>
        <h2>Backend status</h2>
        {health.state === "loading" && <p>Checking…</p>}
        {health.state === "ok" && (
          <p>
            ✅ API reachable — status <code>{health.data.status}</code>, version{" "}
            <code>{health.data.version}</code>
          </p>
        )}
        {health.state === "error" && (
          <p>❌ API unreachable: {health.message}</p>
        )}
      </section>
    </main>
  );
}
