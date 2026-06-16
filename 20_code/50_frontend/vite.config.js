import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Read VITE_* variables from the shared 20_code/.env (one .env for the repo).
  envDir: "..",
  server: {
    port: 5173,
  },
});
