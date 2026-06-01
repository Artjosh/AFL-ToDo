/**
 * Regressão: a identidade do contexto de Toast deve ser ESTÁVEL entre renders.
 *
 * Por quê: o dashboard usa `toast` nas dependências de callbacks (handleApiError
 * -> loadMain). Se o value do ToastProvider for recriado a cada render (ex.: ao
 * exibir um toast), esses callbacks mudam de identidade e os efeitos de fetch
 * re-executam, gerando uma cascata de requisições (loop de GET /tasks +
 * /projects) que satura o dev server. Memoizar o value evita isso.
 */
import { describe, expect, it } from "vitest";
import { render, act } from "@testing-library/react";
import { useEffect } from "react";

import { ToastProvider, useToast } from "@/components/toast";

describe("ToastProvider — estabilidade do contexto", () => {
  it("mantém a mesma identidade de `toast` mesmo após exibir notificações", () => {
    const seen: unknown[] = [];
    let fire: (() => void) | null = null;

    function Probe() {
      const toast = useToast();
      // registra a identidade do objeto de contexto a cada render
      seen.push(toast);
      useEffect(() => {
        fire = () => toast.error("erro de teste", { key: "x" });
      });
      return null;
    }

    render(
      <ToastProvider>
        <Probe />
      </ToastProvider>,
    );

    // dispara alguns toasts (causa re-render do provider pelo estado interno)
    act(() => {
      fire?.();
      fire?.();
      fire?.();
    });

    // todas as identidades observadas devem ser o MESMO objeto
    const first = seen[0];
    expect(seen.every((s) => s === first)).toBe(true);
  });
});
