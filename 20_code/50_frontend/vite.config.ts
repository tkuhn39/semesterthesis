import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Read VITE_* variables from the shared 20_code/.env (one .env for the repo).
  envDir: "..",
  server: {
    port: 5173,
  },
});
