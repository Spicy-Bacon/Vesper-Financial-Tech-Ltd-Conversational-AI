import { defineConfig } from "@playwright/test";
// Only register live tests when explicitly selected. Default runs remain offline.
const selectedLive = process.argv.some(
  (arg, index, args) =>
    arg === "--project=live-http" ||
    (arg === "live-http" && args[index - 1] === "--project"),
);
// Workers reload this config without the runner's CLI arguments.
const live =
  selectedLive ||
  (process.env.TEST_WORKER_INDEX !== undefined &&
    process.env.VESPER_PLAYWRIGHT_LIVE_SELECTED === "1");
process.env.VESPER_PLAYWRIGHT_LIVE_SELECTED = live ? "1" : "0";
// Ignore live-only settings during the existing demo/mocked test runs.
const livePortSetting = live ? (process.env.LIVE_HTTP_PORT ?? "5173") : "5173";
if (
  !/^[1-9]\d{0,4}$/.test(livePortSetting) ||
  Number(livePortSetting) > 65535
) {
  throw new Error("LIVE_HTTP_PORT must be a decimal integer from 1 to 65535.");
}
const livePort = Number(livePortSetting);
const liveURL = `http://127.0.0.1:${livePort}`;
export default defineConfig({
  testDir: "tests/browser",
  workers: 1,
  use: { channel: "chrome", headless: true },
  projects: [
    ...(live
      ? [
          {
            name: "live-http",
            testMatch: "live-http.spec.ts",
            use: {
              baseURL: liveURL,
              trace: "off" as const,
              screenshot: "off" as const,
              video: "off" as const,
            },
          },
        ]
      : []),
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
  webServer: live
    ? [
        {
          command: `npm run dev -- --port ${livePort}`,
          url: liveURL,
          reuseExistingServer: false,
          env: { VITE_API_MODE: "http" },
        },
      ]
    : [
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
