import type { NextConfig } from "next";
import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";

// Single-source config (project_rules §15): read the shared 20_code/.env and expose the API
// base to the client. Default is EMPTY = same origin (FastAPI serves the exported bundle in
// prod, ADR-006); only an explicit NEXT_PUBLIC_API_BASE_URL entry (dev server against a
// separately running backend) overrides it. The VITE_* key belongs to the legacy Vite app.
function apiBaseFromSharedEnv(): string {
  const envPath = join(__dirname, "..", ".env");
  if (!existsSync(envPath)) return "";
  const line = readFileSync(envPath, "utf-8")
    .split(/\r?\n/)
    .find((l) => l.startsWith("NEXT_PUBLIC_API_BASE_URL="));
  return line ? (line.split("=", 2)[1] ?? "").trim() : "";
}

const nextConfig: NextConfig = {
  output: "export",
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL ?? apiBaseFromSharedEnv(),
  },
};

export default nextConfig;
