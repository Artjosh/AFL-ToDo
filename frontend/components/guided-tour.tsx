/**
 * Tour guiado (onboarding) estilo "ats-example".
 *
 * Sequência de passos em um card com "Passo X de Y", botões Voltar/Próximo e um
 * spotlight (recorte) destacando o elemento alvo de cada passo. Aparece uma única
 * vez no primeiro acesso (controle persistido em localStorage, via toast-state):
 * explica o seletor de modo, o login passwordless (link + código) e o multi-device.
 *
 * O usuário pode reabrir pelo botão "?" (evento "restart-tour" disparado pela
 * navbar). A lógica de "já mostrado / dispensado" replica o comportamento do
 * tutorial do projeto de referência.
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { markShown, wasShown } from "@/lib/toast-state";

const TOUR_KEY = "guided-tour";

interface TourStep {
  /** Seletor do elemento alvo (data-tour=...). Vazio => card centralizado. */
  target: string | null;
  title: string;
  description: string;
  icon: string;
}

const STEPS: TourStep[] = [
  {
    target: null,
    title: "Bem-vindo ao ToDo AFL",
    description:
      "Um gerenciador de tarefas com login sem senha. Deixa eu te mostrar como funciona em alguns passos rápidos.",
    icon: "👋",
  },
  {
    target: "[data-tour='mode-selector']",
    title: "Escolha o modo de autenticação",
    description:
      "Aqui no topo você alterna entre dois backends de login: 'Backend Python' (magic link próprio) e 'Python + Supabase Auth' (login via Supabase, validado pelo backend). Em ambos, suas tarefas ficam no backend Python.",
    icon: "🔀",
  },
  {
    target: "[data-tour='login-email']",
    title: "Login sem senha",
    description:
      "Você informa só o email. Não existe cadastro: o primeiro acesso já cria sua conta automaticamente. Enviamos um link e um código de 6 dígitos.",
    icon: "✉️",
  },
  {
    target: "[data-tour='login-card']",
    title: "Multi-dispositivo",
    description:
      "Pediu o link no computador? Pode abrir no celular — esta aba detecta a confirmação sozinha (polling). Ou, se preferir, digite o código de 6 dígitos aqui mesmo.",
    icon: "📱",
  },
];

export default function GuidedTour() {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const mounted = useRef(false);

  // Abre automaticamente no primeiro acesso.
  useEffect(() => {
    if (mounted.current) return;
    mounted.current = true;
    if (!wasShown(TOUR_KEY)) {
      const t = setTimeout(() => setOpen(true), 600);
      return () => clearTimeout(t);
    }
  }, []);

  // Permite reabrir via botão "?" na navbar.
  useEffect(() => {
    const handler = () => {
      setStep(0);
      setOpen(true);
    };
    window.addEventListener("restart-tour", handler);
    return () => window.removeEventListener("restart-tour", handler);
  }, []);

  const current = STEPS[step];

  const updateRect = useCallback(() => {
    if (!open || !current?.target) {
      setRect(null);
      return;
    }
    const el = document.querySelector(current.target);
    setRect(el ? el.getBoundingClientRect() : null);
  }, [open, current]);

  useEffect(() => {
    if (!open) return;
    updateRect();
    // Reposiciona em pulsos curtos enquanto o alvo do passo ainda não existe
    // (ex.: troca de passo / reabertura), evitando card "perdido" no centro.
    let tries = 0;
    const interval = setInterval(() => {
      tries += 1;
      updateRect();
      if (tries >= 10) clearInterval(interval);
    }, 120);
    window.addEventListener("resize", updateRect);
    window.addEventListener("scroll", updateRect, true);
    return () => {
      clearInterval(interval);
      window.removeEventListener("resize", updateRect);
      window.removeEventListener("scroll", updateRect, true);
    };
  }, [open, step, updateRect]);

  const finish = useCallback(() => {
    markShown(TOUR_KEY);
    setOpen(false);
    setStep(0);
  }, []);

  if (!open) return null;

  const isLast = step === STEPS.length - 1;
  const pad = 8;

  // Posiciona o card abaixo do alvo (ou centralizado se não houver alvo).
  let cardStyle: React.CSSProperties = {
    top: "50%",
    left: "50%",
    transform: "translate(-50%, -50%)",
  };
  if (rect) {
    const below = rect.bottom + 16;
    const fitsBelow = below + 220 < window.innerHeight;
    const top = fitsBelow ? below : Math.max(16, rect.top - 236);
    const left = Math.max(
      16,
      Math.min(rect.left + rect.width / 2 - 180, window.innerWidth - 376),
    );
    cardStyle = { top, left };
  }

  return (
    <div className="fixed inset-0 z-[9998]">
      {/* Overlay com recorte (spotlight) usando box-shadow gigante */}
      {rect ? (
        <div
          className="pointer-events-none fixed rounded-xl border-2 border-accent-soft/60 transition-all duration-300"
          style={{
            left: rect.left - pad,
            top: rect.top - pad,
            width: rect.width + pad * 2,
            height: rect.height + pad * 2,
            boxShadow: "0 0 0 9999px rgba(0,0,0,0.7)",
          }}
        />
      ) : (
        <div className="fixed inset-0 bg-black/70" />
      )}

      {/* Card do passo */}
      <div
        className="fixed z-[9999] w-[340px] max-w-[calc(100vw-2rem)] rounded-2xl border border-accent-soft/30 bg-surface p-5 shadow-[0_20px_60px_rgba(0,0,0,0.6)] transition-all duration-300"
        style={cardStyle}
      >
        <div className="mb-3 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent/15 text-xl">
            {current.icon}
          </div>
          <div className="flex-1">
            <p className="text-[10px] font-bold uppercase tracking-widest text-accent-soft/70">
              Passo {step + 1} de {STEPS.length}
            </p>
            <h3 className="text-base font-bold text-foreground">{current.title}</h3>
          </div>
          <button
            type="button"
            onClick={finish}
            className="text-muted transition-colors hover:text-foreground"
            aria-label="Fechar tour"
          >
            ✕
          </button>
        </div>

        <p className="text-sm leading-relaxed text-muted">{current.description}</p>

        {/* Barra de progresso */}
        <div className="mt-4 flex gap-1.5">
          {STEPS.map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition-all ${
                i <= step ? "bg-accent" : "bg-border"
              }`}
            />
          ))}
        </div>

        <div className="mt-4 flex items-center justify-between">
          <button
            type="button"
            onClick={finish}
            className="text-xs text-muted transition-colors hover:text-foreground"
          >
            Pular
          </button>
          <div className="flex gap-2">
            {step > 0 && (
              <button
                type="button"
                onClick={() => setStep((s) => s - 1)}
                className="rounded-lg px-4 py-2 text-xs font-semibold text-muted transition-all hover:bg-surface-2 hover:text-foreground"
              >
                Voltar
              </button>
            )}
            <button
              type="button"
              onClick={() => (isLast ? finish() : setStep((s) => s + 1))}
              className="rounded-lg bg-accent px-5 py-2 text-xs font-bold text-white shadow-md shadow-accent/25 transition-all hover:bg-accent-hover"
            >
              {isLast ? "Concluir ✓" : "Próximo →"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
