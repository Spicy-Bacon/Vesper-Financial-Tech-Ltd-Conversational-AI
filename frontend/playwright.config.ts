import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/browser",
  workers: 1,
  use: { channel: "chrome", headless: true },
  projects: [
    {
      name: "demo",
      testMatch: "conversation.spec.ts",
      use: { baseURL: "http://127.0.0.1:5173" },
    },
    {
      name: "http",
      testMatch: "http.spec.ts",
      use: { baseURL: "http://127.0.0.1:5174" },
    },
  ],
  webServer: [
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5173",
      reuseExistingServer: false,
      env: { VITE_API_MODE: "demo" },
    },
    {
      command: "npm run dev -- --port 5174",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      env: { VITE_API_MODE: "http" },
    },
  ],
  reporter: "list",
});
