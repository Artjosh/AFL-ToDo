/**
 * Barra de navegação fixa no topo, com o seletor de modo de autenticação, o
 * botão de reabrir o tour guiado e, quando logado, o email + logout.
 */
"use client";

import Link from "next/link";

import AuthModeSelector from "@/components/auth-mode-selector";
import { useAuth } from "@/components/auth-provider";

export default function Navbar() {
  const { user, logout, mode } = useAuth();

  // O tour guiado existe na tela de login (sem usuário logado). Por isso o botão
  // "?" para reabri-lo é exibido sempre que não há sessão — visibilidade estável,
  // sem depender de eventos pontuais (que faziam o botão sumir em alguns casos).
  const showTourButton = !user;

  const restartTour = () => {
    window.dispatchEvent(new CustomEvent("restart-tour"));
  };

  return (
    <header className="fixed top-0 z-50 flex h-16 w-full items-center justify-between gap-4 border-b border-border bg-bg/80 px-4 backdrop-blur-xl sm:px-8">
      <Link href={user ? "/dashboard" : "/login"} className="flex items-center gap-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent/20 text-accent-soft">
          ✓
        </span>
        <span className="text-lg font-bold tracking-tight text-foreground">
          ToDo<span className="text-accent-soft">AFL</span>
        </span>
      </Link>

      <div className="flex items-center gap-3">
        <AuthModeSelector />
        {showTourButton && (
          <button
            type="button"
            onClick={restartTour}
            title="Ver o tour novamente"
            aria-label="Ver o tour novamente"
            className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-accent-soft/30 bg-accent-soft/10 text-xs font-bold text-accent-soft transition-all hover:scale-110 hover:bg-accent-soft/20"
          >
            ?
          </button>
        )}
        {user && (
          <div className="flex items-center gap-3">
            <span
              className="hidden max-w-[180px] truncate text-sm text-muted md:inline"
              title={`${user.email} • modo ${mode}`}
            >
              {user.email}
            </span>
            <button
              type="button"
              onClick={logout}
              className="rounded-lg border border-border bg-surface px-3 py-1.5 text-xs font-semibold text-foreground transition-colors hover:bg-surface-2"
            >
              Sair
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
