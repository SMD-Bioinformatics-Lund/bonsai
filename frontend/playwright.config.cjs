const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "tests/browser",
  testMatch: "*.spec.cjs",
  workers: 1,
  use: { browserName: "chromium", headless: true },
});
