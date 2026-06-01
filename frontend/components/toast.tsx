/**
 * Sistema de toasts.
 *
 * Inspirado na lógica visual e comportamental do projeto ats-example:
 * - estilo visual escuro com acentos roxos e bordas suaves;
 * - controla se um toast já foi mostrado (toasts "once");
 * - controla se um toast já foi clicado;
 * - evita spam de notificações repetidas (mesma assinatura em janela curta).
 *
 * A lógica de "mostrado / clicado / anti-spam" fica em lib/toast-state.ts.
 */
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import {
  isSpam,
  markClicked,
  markShown,
  wasShown,
} from "@/lib/toast-state";

export type ToastVariant = "success" | "error" | "info" | "warning";

export interface ToastOptions {
  /** Chave estável: se informada com `once`, o toast só aparece uma vez. */
  key?: string;
  /** Mostra apenas uma vez (persistido). Requer `key`. */
  once?: boolean;
  /** Duração em ms antes de sumir automaticamente. */
  duration?: number;
  /** Callback ao clicar no corpo do toast. */
  onClick?: () => void;
}

interface ToastItem {
  id: string;
  message: string;
  variant: ToastVariant;
  duration: number;
  leaving: boolean;
  trackKey?: string;
  onClick?: () => void;
}

interface ToastContextValue {
  notify: (message: string, variant?: ToastVariant, options?: ToastOptions) => void;
  success: (message: string, options?: ToastOptions) => void;
  error: (message: string, options?: ToastOptions) => void;
  info: (message: string, options?: ToastOptions) => void;
  warning: (message: string, options?: ToastOptions) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

const MAX_TOASTS = 4;
const DEFAULT_DURATION = 4000;

const VARIANT_STYLES: Record<ToastVariant, { border: string; icon: string; iconColor: string }> = {
  success: { border: "border-l-success", icon: "✓", iconColor: "text-success" },
  error: { border: "border-l-danger", icon: "✕", iconColor: "text-danger" },
  warning: { border: "border-l-warning", icon: "!", iconColor: "text-warning" },
  info: { border: "border-l-accent-soft", icon: "i", iconColor: "text-accent-soft" },
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timers = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const remove = useCallback((id: string) => {
    // Marca como "saindo" para animar, depois remove de fato.
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, leaving: true } : t)),
    );
    const timeout = setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
      timers.current.delete(id);
    }, 200);
    timers.current.set(`${id}-out`, timeout);
  }, []);

  const notify = useCallback(
    (message: string, variant: ToastVariant = "info", options: ToastOptions = {}) => {
      const { key, once, duration = DEFAULT_DURATION, onClick } = options;

      // Toast "once": não repete se já foi mostrado antes.
      if (once && key && wasShown(key)) {
        return;
      }

      // Anti-spam: bloqueia conteúdo idêntico em janela curta.
      const signature = key ?? `${variant}:${message}`;
      if (isSpam(signature)) {
        return;
      }

      if (once && key) {
        markShown(key);
      }

      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const item: ToastItem = {
        id,
        message,
        variant,
        duration,
        leaving: false,
        trackKey: key,
        onClick,
      };

      setToasts((prev) => {
        const next = [...prev, item];
        // Limita a quantidade visível para evitar empilhamento (anti-spam visual).
        return next.slice(-MAX_TOASTS);
      });

      const timeout = setTimeout(() => remove(id), duration);
      timers.current.set(id, timeout);
    },
    [remove],
  );

  const handleClick = useCallback(
    (item: ToastItem) => {
      if (item.trackKey) {
        markClicked(item.trackKey);
      }
      item.onClick?.();
      remove(item.id);
    },
    [remove],
  );

  useEffect(() => {
    const map = timers.current;
    return () => {
      map.forEach((t) => clearTimeout(t));
      map.clear();
    };
  }, []);

  // IMPORTANTE: memoizar o value evita recriar as funções a cada render.
  // Sem isto, todo toast exibido muda a identidade de `toast`, o que faz os
  // consumidores (ex.: dashboard) recriarem callbacks e RE-EXECUTAREM efeitos de
  // fetch — gerando uma cascata de requisições (loop de GET /tasks + /projects).
  const value = useMemo<ToastContextValue>(
    () => ({
      notify,
      success: (m, o) => notify(m, "success", o),
      error: (m, o) => notify(m, "error", o),
      info: (m, o) => notify(m, "info", o),
      warning: (m, o) => notify(m, "warning", o),
    }),
    [notify],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Container dos toasts (canto inferior direito) */}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[9999] flex w-[360px] max-w-[calc(100vw-2rem)] flex-col gap-2">
        {toasts.map((t) => {
          const styles = VARIANT_STYLES[t.variant];
          return (
            <div
              key={t.id}
              role="status"
              onClick={() => handleClick(t)}
              className={`pointer-events-auto cursor-pointer rounded-xl border border-border ${styles.border} border-l-4 bg-surface/95 px-4 py-3 shadow-[0_12px_40px_rgba(0,0,0,0.5)] backdrop-blur-md ${
                t.leaving ? "animate-toast-out" : "animate-toast-in"
              }`}
            >
              <div className="flex items-start gap-3">
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-surface-2 text-xs font-bold ${styles.iconColor}`}
                >
                  {styles.icon}
                </span>
                <p className="flex-1 text-sm leading-snug text-foreground">
                  {t.message}
                </p>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    remove(t.id);
                  }}
                  className="text-muted transition-colors hover:text-foreground"
                  aria-label="Fechar notificação"
                >
                  ✕
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error("useToast deve ser usado dentro de <ToastProvider>");
  }
  return ctx;
}
