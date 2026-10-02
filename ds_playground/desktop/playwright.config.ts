import { defineConfig } from "@playwright/test";

// The built renderer is served on the `tauri dev` origin, which a harness spawned with --dev admits.
export default defineConfig({
  testDir: "tests",
  use: { baseURL: "http://localhost:1420" },
  webServer: { command: "pnpm build && pnpm preview", url: "http://localhost:1420" },
});
