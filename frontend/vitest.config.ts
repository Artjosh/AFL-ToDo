import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { resolve } from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": resolve(__dirname, "."),
      // Resolve as libs de teste a partir do node_modules do frontend, já que os
      // arquivos de teste ficam fora desta pasta (../tests/frontend).
      "@testing-library/react": resolve(__dirname, "node_modules/@testing-library/react"),
      "@testing-library/jest-dom": resolve(__dirname, "node_modules/@testing-library/jest-dom"),
      "@testing-library/user-event": resolve(__dirname, "node_modules/@testing-library/user-event"),
    },
  },
  // Resolve dependências (testing-library etc.) a partir do node_modules do frontend,
  // mesmo para arquivos de teste que ficam fora desta pasta (../tests/frontend).
  optimizeDeps: {
    entries: [],
  },
  server: {
    fs: {
      // Permite carregar os arquivos de teste que ficam fora de frontend/ (em ../tests).
      allow: [resolve(__dirname, ".."), __dirname],
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["../tests/frontend/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      include: ["lib/**/*.ts", "components/**/*.tsx"],
      reporter: ["text", "text-summary"],
    },
  },
});
