/**
 * Testes da lógica de controle de toasts (mostrado / clicado / anti-spam).
 */
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  isSpam,
  markClicked,
  markShown,
  resetToastState,
  wasClicked,
  wasShown,
} from "@/lib/toast-state";

describe("toast-state", () => {
  beforeEach(() => {
    resetToastState();
    vi.useRealTimers();
  });

  it("marca e detecta toast já mostrado (persistido)", () => {
    expect(wasShown("welcome")).toBe(false);
    markShown("welcome");
    expect(wasShown("welcome")).toBe(true);
  });

  it("marca e detecta toast já clicado", () => {
    expect(wasClicked("cta")).toBe(false);
    markClicked("cta");
    expect(wasClicked("cta")).toBe(true);
  });

  it("anti-spam: bloqueia a mesma assinatura em janela curta", () => {
    const sig = "error:falhou";
    expect(isSpam(sig)).toBe(false); // primeira vez passa
    expect(isSpam(sig)).toBe(true); // imediatamente depois é spam
  });

  it("anti-spam: assinaturas diferentes não conflitam", () => {
    expect(isSpam("a")).toBe(false);
    expect(isSpam("b")).toBe(false);
  });

  it("anti-spam: libera novamente após a janela expirar", () => {
    vi.useFakeTimers();
    const sig = "msg";
    expect(isSpam(sig)).toBe(false);
    expect(isSpam(sig)).toBe(true);
    // avança além da janela anti-spam (4s)
    vi.advanceTimersByTime(5000);
    expect(isSpam(sig)).toBe(false);
  });

  it("resetToastState limpa mostrado e clicado", () => {
    markShown("x");
    markClicked("y");
    resetToastState();
    expect(wasShown("x")).toBe(false);
    expect(wasClicked("y")).toBe(false);
  });
});
