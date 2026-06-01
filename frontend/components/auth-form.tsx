/**
 * Formulário de login passwordless (magic link + código OTP).
 *
 * Sem senha e sem cadastro separado: o usuário informa o email, recebe um link
 * E um código de 6 dígitos. Ele pode:
 *  - clicar o link em QUALQUER dispositivo (a aba detecta via polling); ou
 *  - digitar o código de 6 dígitos aqui mesmo.
 * O primeiro acesso já cria a conta.
 */
"use client";

import { useEffect, useRef, useState } from "react";

import { useAuth, type MagicLinkStart } from "@/components/auth-provider";
import { useToast } from "@/components/toast";

type Phase = "form" | "waiting";

export default function AuthForm() {
  const {
    mode,
    startMagicLink,
    pollUntilAuthenticated,
    verifyOtpCode,
    supabaseAvailable,
    mounted,
  } = useAuth();
  const toast = useToast();

  const [email, setEmail] = useState("");
  const [phase, setPhase] = useState<Phase>("form");
  const [submitting, setSubmitting] = useState(false);
  const [pending, setPending] = useState<MagicLinkStart | null>(null);
  const pollSignal = useRef<{ cancelled: boolean } | null>(null);

  useEffect(() => {
    return () => {
      if (pollSignal.current) pollSignal.current.cancelled = true;
    };
  }, []);

  // O redirect para /dashboard é responsabilidade reativa da página de login
  // (observa `user`). Aqui apenas avisamos o sucesso; assim evitamos a corrida
  // entre um push imperativo e o guard do dashboard (que chutava de volta ao /login).
  const finishSuccess = () => {
    toast.success("Acesso confirmado! Entrando...", { key: "login-success" });
  };

  const beginPolling = async (start: MagicLinkStart) => {
    const signal = { cancelled: false };
    pollSignal.current = signal;
    try {
      const ok = await pollUntilAuthenticated(start, signal);
      if (signal.cancelled) return;
      if (ok) finishSuccess();
      else {
        toast.warning("O link expirou. Solicite um novo acesso.", {
          key: "magic-expired",
        });
        setPhase("form");
      }
    } catch {
      if (signal.cancelled) return;
      toast.error("Link inválido ou expirado. Tente novamente.", {
        key: "magic-error",
      });
      setPhase("form");
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting) return;

    const value = email.trim();
    if (!value || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      toast.error("Informe um email válido.", { key: "auth-invalid-email" });
      return;
    }

    setSubmitting(true);
    try {
      const start = await startMagicLink(value);
      setPending(start);
      setPhase("waiting");
      toast.success(start.message, { key: "magic-sent" });
      void beginPolling(start);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Falha ao enviar o link.";
      toast.error(message, { key: "auth-error" });
    } finally {
      setSubmitting(false);
    }
  };

  const cancelWaiting = () => {
    if (pollSignal.current) pollSignal.current.cancelled = true;
    setPhase("form");
    setPending(null);
  };

  return (
    <div className="mx-auto mt-8 w-full max-w-md">
      <div className="card" data-tour="login-card">
        {phase === "form" ? (
          <>
            <div className="mb-6 text-center">
              <h1 className="text-2xl font-bold text-foreground">Entrar</h1>
              <p className="mt-1 text-sm text-muted">
                Sem senha. Informe seu email e enviamos um link + código de acesso.
              </p>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4" data-tour="login-email">
              <div>
                <label
                  htmlFor="email"
                  className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-muted"
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  autoComplete="email"
                  className="input-base"
                  placeholder="voce@exemplo.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoFocus
                />
              </div>

              <button
                type="submit"
                className="btn-primary w-full"
                disabled={submitting}
              >
                {submitting ? "Enviando..." : "Enviar link de acesso"}
              </button>
            </form>

            <p className="mt-4 rounded-lg border border-border bg-surface-2/60 px-3 py-2.5 text-xs leading-relaxed text-muted">
              É seu primeiro acesso? Não precisa criar conta: ao confirmar o link
              ou o código, sua conta é criada automaticamente.
            </p>
          </>
        ) : (
          <WaitingPanel
            start={pending}
            onCancel={cancelWaiting}
            onVerify={async (code) => {
              const ok = await verifyOtpCode(pending!, code);
              if (ok) {
                if (pollSignal.current) pollSignal.current.cancelled = true;
                finishSuccess();
              }
              return ok;
            }}
          />
        )}
      </div>

      <p className="mt-4 text-center text-xs text-muted">
        Modo atual:{" "}
        <span className="font-semibold text-accent-soft">
          {mounted && mode === "supabase" ? "Supabase Auth" : "Backend Python (local)"}
        </span>
        {mounted && !supabaseAvailable && " — Supabase indisponível (defina as envs)"}
      </p>
    </div>
  );
}

function WaitingPanel({
  start,
  onCancel,
  onVerify,
}: {
  start: MagicLinkStart | null;
  onCancel: () => void;
  onVerify: (code: string) => Promise<boolean>;
}) {
  const toast = useToast();
  const [code, setCode] = useState("");
  const [verifying, setVerifying] = useState(false);

  if (!start) return null;

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (verifying) return;
    if (!/^\d{6}$/.test(code)) {
      toast.error("Digite o código de 6 dígitos.", { key: "otp-format" });
      return;
    }
    setVerifying(true);
    try {
      const ok = await onVerify(code);
      if (!ok) {
        toast.error("Código incorreto. Tente novamente.", { key: "otp-wrong" });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Código inválido.";
      toast.error(message, { key: "otp-error" });
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="text-center">
      <div className="mx-auto mb-4 flex h-14 w-14 animate-pulse items-center justify-center rounded-full bg-accent/15 text-2xl text-accent-soft">
        ✉
      </div>
      <h1 className="text-xl font-bold text-foreground">Verifique seu acesso</h1>
      <p className="mt-2 text-sm text-muted">
        {start.emailSent ? (
          <>
            Enviamos um link e um código para{" "}
            <strong className="text-foreground">{start.email}</strong>. Clique o
            link em qualquer dispositivo, ou digite o código abaixo.
          </>
        ) : (
          <>
            Modo dev (sem SMTP): use o link ou o código abaixo. O link funciona
            em qualquer dispositivo.
          </>
        )}
      </p>

      {/* Dev: mostra link e código (quando o backend os expõe — útil em dev). */}
      {(start.devMagicUrl || start.devOtpCode) && (
        <div className="mt-4 space-y-2 rounded-lg border border-border bg-surface-2 p-3 text-left">
          {start.emailSent && (
            <p className="text-[11px] font-semibold uppercase tracking-wider text-warning">
              Atalho de desenvolvimento
            </p>
          )}
          {start.devOtpCode && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                Código (dev)
              </p>
              <p className="text-lg font-bold tracking-[0.3em] text-accent-soft">
                {start.devOtpCode}
              </p>
            </div>
          )}
          {start.devMagicUrl && (
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-muted">
                Link (dev)
              </p>
              <a
                href={start.devMagicUrl}
                target="_blank"
                rel="noreferrer"
                className="block break-all text-xs font-medium text-accent-soft hover:underline"
              >
                {start.devMagicUrl}
              </a>
            </div>
          )}
        </div>
      )}

      {/* Campo de OTP */}
      <form onSubmit={handleVerify} className="mt-5 space-y-3" data-tour="otp-input">
        <input
          inputMode="numeric"
          maxLength={6}
          className="input-base text-center text-lg font-bold tracking-[0.4em]"
          placeholder="••••••"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
        />
        <button type="submit" className="btn-primary w-full" disabled={verifying}>
          {verifying ? "Verificando..." : "Entrar com o código"}
        </button>
      </form>

      <div className="mt-4 flex items-center justify-center gap-2 text-sm text-muted">
        <span className="h-2 w-2 animate-ping rounded-full bg-accent-soft" />
        Aguardando confirmação do link...
      </div>

      <button type="button" onClick={onCancel} className="btn-ghost mt-4 w-full">
        Usar outro email
      </button>
    </div>
  );
}
