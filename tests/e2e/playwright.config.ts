import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

/**
 * Configuração dos testes E2E.
 *
 * Os webServers (backend FastAPI + frontend Next) são iniciados automaticamente
 * pelo Playwright, usando um banco SQLite dedicado de teste (e2e.db) e modo dev
 * (sem SMTP), para que o link/OTP venham na resposta da API.
 *
 * Roda em headless por padrão. Para ver o navegador: `npm run test:headed`.
 */
const BACKEND_DIR = path.resolve(__dirname, "../../backend");
const FRONTEND_DIR = path.resolve(__dirname, "../../frontend");
const E2E_DB = path.resolve(__dirname, "e2e.db");

const PYTHON = path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe");

export default defineConfig({
  testDir: "./specs",
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://localhost:3100",
    headless: true,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
  ],
  webServer: [
    {
      // Backend em porta dedicada, banco de teste e modo dev (link/OTP na resposta).
      command: `"${PYTHON}" -m uvicorn app.main:app --host 127.0.0.1 --port 8100`,
      cwd: BACKEND_DIR,
      url: "http://127.0.0.1:8100/health",
      timeout: 60_000,
      reuseExistingServer: false,
      env: {
        DATABASE_URL: `sqlite:///${E2E_DB.replace(/\\/g, "/")}`,
        JWT_SECRET: "e2e-secret",
        FRONTEND_URL: "http://localhost:3100",
        BACKEND_PUBLIC_URL: "http://localhost:8100",
        SMTP_USER: "",
        SMTP_PASSWORD: "",
        SUPABASE_JWKS_URL: "",
      },
    },
    {
      command: "npm run dev -- --port 3100",
      cwd: FRONTEND_DIR,
      url: "http://localhost:3100/login",
      timeout: 120_000,
      reuseExistingServer: false,
      env: {
        NEXT_PUBLIC_API_URL: "http://localhost:8100",
        // Sem Supabase no E2E automatizado (modo local). O modo Supabase é
        // validado pelos testes de backend + verificação manual.
        NEXT_PUBLIC_SUPABASE_URL: "",
        NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: "",
      },
    },
  ],
});
