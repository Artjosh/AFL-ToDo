import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Limpa o DOM e o localStorage entre os testes.
afterEach(() => {
  cleanup();
  try {
    window.localStorage.clear();
  } catch {
    // ignore
  }
});
