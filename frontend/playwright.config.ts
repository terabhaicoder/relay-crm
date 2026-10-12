import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join } from "node:path";
const external = process.env.PLAYWRIGHT_BASE_URL;
const isolatedDirectory = external
  ? undefined
  : mkdtempSync(join(tmpdir(), "relay-e2e-"));
export default defineConfig({
  testDir: "./tests",
  testMatch: "**/*.spec.ts",
  fullyParallel: true,
  timeout: 90_000,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: external ?? "http://127.0.0.1:3017",
    trace: "retain-on-failure",
  },
  webServer: external
    ? undefined
    : {
        command: "python3 ../scripts/dev.py --port 3017 --api-port 8017",
        url: "http://127.0.0.1:3017",
        reuseExistingServer: false,
        timeout: 120_000,
        env: {
          ENVIRONMENT: "test",
          DATABASE_URL: `sqlite:///${join(isolatedDirectory!, "e2e.db")}`,
          UPLOAD_DIR: join(isolatedDirectory!, "uploads"),
          SIGNUP_ENABLED: "true",
          DEMO_SEED: "false",
          NEXT_DIST_DIR: `.next-e2e-${basename(isolatedDirectory!)}`,
        },
      },
});
