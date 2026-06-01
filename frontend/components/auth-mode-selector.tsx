/**
 * Seletor de modo de autenticação/backend, fixo no topo do site.
 *
 * Opções:
 * - "Python Backend": autenticação local (JWT do FastAPI).
 * - "Python Backend + Supabase Auth": login via Supabase, validado pelo backend.
 *
 * O modo Supabase só fica habilitado se as variáveis NEXT_PUBLIC_SUPABASE_* estiverem
 * configuradas. Trocar de modo só é permitido quando não há usuário logado.
 */
"use client";

import { useAuth } from "@/components/auth-provider";
import { useToast } from "@/components/toast";
import type { AuthMode } from "@/lib/types";

export default function AuthModeSelector() {
  const { mode, setMode, supabaseAvailable, user, mounted } = useAuth();
  const toast = useToast();

  const handleSelect = (next: AuthMode) => {
    if (next === mode) return;
    if (user) {
      toast.warning("Faça logout antes de trocar o modo de autenticação.", {
        key: "switch-mode-while-logged",
      });
      return;
    }
    if (next === "supabase" && !supabaseAvailable) {
      toast.error(
        "Supabase não configurado. Defina NEXT_PUBLIC_SUPABASE_URL e NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY.",
        { key: "supabase-not-configured", once: true },
      );
      return;
    }
    setMode(next);
    toast.info(
      next === "supabase"
        ? "Modo: Python Backend + Supabase Auth (magic link via Supabase)"
        : "Modo: Backend Python (magic link próprio)",
      { key: `mode-${next}` },
    );
  };

  const options: { value: AuthMode; label: string }[] = [
    { value: "local", label: "Python Backend" },
    { value: "supabase", label: "Python Backend + Supabase Auth" },
  ];

  return (
    <div className="flex items-center gap-2" data-tour="mode-selector">
      <span className="hidden text-xs font-medium uppercase tracking-wider text-muted sm:inline">
        Modo de auth
      </span>
      <div className="flex rounded-full border border-border bg-surface p-1">
        {options.map((opt) => {
          // Antes da montagem, renderiza o estado estável (modo local, nada
          // desabilitado) para casar com o HTML do servidor e evitar hydration
          // mismatch quando env/localStorage divergirem do bundle do servidor.
          const active = mounted ? mode === opt.value : opt.value === "local";
          const disabled = mounted && opt.value === "supabase" && !supabaseAvailable;
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => handleSelect(opt.value)}
              disabled={disabled}
              title={
                disabled
                  ? "Supabase não configurado (.env.local)"
                  : opt.label
              }
              className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-all ${
                active
                  ? "bg-accent text-white shadow-md shadow-accent/30"
                  : "text-muted hover:text-foreground"
              } ${disabled ? "cursor-not-allowed opacity-40" : ""}`}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
