/**
 * Contexto de autenticação passwordless (magic link + OTP) — padrão BFF.
 *
 * Diferença central em relação à versão anterior: o token de sessão NÃO fica
 * mais no browser (localStorage). Ele vive num cookie httpOnly gerenciado pelos
 * route handlers do Next (/api/auth/*). Aqui guardamos apenas o objeto `user`
 * e o `mode`. Toda chamada de dados passa pelo proxy same-origin (/api/py/*),
 * que injeta o token no servidor.
 *
 * Dois modos, selecionáveis no topo:
 * 1. "local"    -> backend Python envia magic link + OTP. O fim do login
 *                  (OTP/polling) é feito por /api/auth/login, que grava o cookie
 *                  de sessão no servidor. O token nunca toca o JavaScript.
 * 2. "supabase" -> a Supabase envia o link/OTP. Ao obter o access_token, ele é
 *                  enviado UMA vez a /api/auth/session, que valida e o guarda no
 *                  cookie httpOnly. A partir daí, o browser não usa mais o token.
 */
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useRouter } from "next/navigation";

import {
  checkLoginStatus,
  clearSession,
  establishSession,
  getSession,
  requestMagicLink,
  supabaseStart,
  verifyOtp as verifyOtpLocal,
} from "@/lib/api";
import { getSupabaseClient, isSupabaseConfigured } from "@/lib/supabase";
import { resetToastState } from "@/lib/toast-state";
import type { AuthMode, User } from "@/lib/types";

/** Resultado de uma solicitação de magic link, usado pela UI para o polling/OTP. */
export interface MagicLinkStart {
  selector: string | null;
  email: string;
  emailSent: boolean;
  devMagicUrl: string | null;
  devOtpCode: string | null;
  message: string;
}

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  mounted: boolean;
  mode: AuthMode;
  supabaseAvailable: boolean;
  setMode: (mode: AuthMode) => void;
  startMagicLink: (email: string) => Promise<MagicLinkStart>;
  pollUntilAuthenticated: (
    start: MagicLinkStart,
    signal: { cancelled: boolean },
  ) => Promise<boolean>;
  verifyOtpCode: (start: MagicLinkStart, code: string) => Promise<boolean>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

const MODE_STORAGE_KEY = "todo-auth-mode";

const POLL_INTERVAL_MS = 2500;
const POLL_TIMEOUT_MS = 1000 * 60 * 15; // 15 min (igual à expiração do link)

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [mounted, setMounted] = useState(false);
  const [mode, setModeState] = useState<AuthMode>("local");
  const initialized = useRef(false);

  const supabaseAvailable = isSupabaseConfigured();

  // Marca a montagem no cliente. A UI que depende de env/localStorage (mode,
  // supabaseAvailable) só passa a divergir do HTML do servidor APÓS este ponto,
  // evitando hydration mismatch.
  useEffect(() => {
    setMounted(true);
  }, []);

  const setMode = useCallback((next: AuthMode) => {
    setModeState(next);
    if (typeof window !== "undefined") {
      window.localStorage.setItem(MODE_STORAGE_KEY, next);
    }
  }, []);

  // Inicialização: recupera o modo e tenta restaurar a sessão (via cookie httpOnly).
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    const init = async () => {
      try {
        const savedMode =
          typeof window !== "undefined"
            ? (window.localStorage.getItem(MODE_STORAGE_KEY) as AuthMode | null)
            : null;
        const effectiveMode: AuthMode =
          savedMode === "supabase" && supabaseAvailable ? "supabase" : "local";
        setModeState(effectiveMode);

        // Modo supabase: se houver sessão Supabase no browser mas ainda não houver
        // cookie de sessão do BFF, estabelece o cookie a partir do access_token.
        if (effectiveMode === "supabase" && supabaseAvailable) {
          try {
            const supabase = getSupabaseClient();
            const { data } = (await supabase?.auth.getSession()) ?? { data: null };
            const accessToken = data?.session?.access_token ?? null;
            if (accessToken) {
              const { user: synced } = await establishSession(accessToken, "supabase");
              setUser(synced);
              return;
            }
          } catch {
            /* cai na restauração via cookie abaixo */
          }
        }

        // Restaura a sessão a partir do cookie httpOnly (vale para os dois modos).
        try {
          const { user: me } = await getSession();
          setUser(me);
        } catch {
          setUser(null);
        }
      } finally {
        setLoading(false);
      }
    };

    void init();
  }, [supabaseAvailable]);

  const startMagicLink = useCallback(
    async (rawEmail: string): Promise<MagicLinkStart> => {
      const email = rawEmail.trim().toLowerCase();

      if (mode === "supabase") {
        const supabase = getSupabaseClient();
        if (!supabase) throw new Error("Supabase não está configurado.");

        let selector: string | null = null;
        try {
          const started = await supabaseStart(email);
          selector = started.selector;
        } catch {
          selector = null;
        }

        const apiUrl = (
          process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
        ).replace(/\/$/, "");
        const emailRedirectTo = selector
          ? `${apiUrl}/auth/supabase/callback?selector=${encodeURIComponent(selector)}`
          : typeof window !== "undefined"
            ? window.location.origin
            : undefined;

        const { error } = await supabase.auth.signInWithOtp({
          email,
          options: { shouldCreateUser: true, emailRedirectTo },
        });
        if (error) throw new Error(error.message);

        return {
          selector,
          email,
          emailSent: true,
          devMagicUrl: null,
          devOtpCode: null,
          message: "Enviamos um link e um código pela Supabase para o seu email.",
        };
      }

      // Modo local
      const res = await requestMagicLink(email);
      return {
        selector: res.selector,
        email: res.email,
        emailSent: res.email_sent,
        devMagicUrl: res.dev_magic_url,
        devOtpCode: res.dev_otp_code,
        message: res.message,
      };
    },
    [mode],
  );

  const pollUntilAuthenticated = useCallback(
    async (start: MagicLinkStart, signal: { cancelled: boolean }) => {
      const deadline = Date.now() + POLL_TIMEOUT_MS;

      // Modo supabase SEM selector (sem backend de polling): observa a sessão local
      // do Supabase e, ao obtê-la, estabelece o cookie de sessão do BFF.
      if (mode === "supabase" && !start.selector) {
        const supabase = getSupabaseClient();
        if (!supabase) throw new Error("Supabase não está configurado.");
        while (!signal.cancelled && Date.now() < deadline) {
          const { data } = await supabase.auth.getSession();
          const accessToken = data.session?.access_token ?? null;
          if (accessToken) {
            const { user: synced } = await establishSession(accessToken, "supabase");
            if (!signal.cancelled) setUser(synced);
            return true;
          }
          await sleep(POLL_INTERVAL_MS);
        }
        return false;
      }

      // Demais casos: polling no BFF (vale para local e supabase cross-device).
      if (!start.selector) return false;
      while (!signal.cancelled && Date.now() < deadline) {
        try {
          const res = await checkLoginStatus(start.selector);
          if (res.status === "approved" && res.user) {
            if (!signal.cancelled) setUser(res.user);
            return true;
          }
        } catch (err) {
          if (err && typeof err === "object" && "status" in err) {
            const st = (err as { status: number }).status;
            if (st === 404 || st === 410) throw err;
          }
        }
        await sleep(POLL_INTERVAL_MS);
      }
      return false;
    },
    [mode],
  );

  const verifyOtpCode = useCallback(
    async (start: MagicLinkStart, code: string) => {
      if (mode === "supabase") {
        const supabase = getSupabaseClient();
        if (!supabase) throw new Error("Supabase não está configurado.");
        const { data, error } = await supabase.auth.verifyOtp({
          email: start.email,
          token: code,
          type: "email",
        });
        if (error) throw new Error(error.message);
        const accessToken = data.session?.access_token;
        if (!accessToken) throw new Error("Sessão Supabase inválida.");
        const { user: synced } = await establishSession(accessToken, "supabase");
        setUser(synced);
        return true;
      }

      // Modo local: o servidor (BFF) grava o cookie e devolve só o usuário.
      if (!start.selector) throw new Error("Pedido de login inválido.");
      const res = await verifyOtpLocal(start.selector, code);
      if (res.user) {
        setUser(res.user);
        return true;
      }
      return false;
    },
    [mode],
  );

  const logout = useCallback(async () => {
    if (mode === "supabase") {
      const supabase = getSupabaseClient();
      await supabase?.auth.signOut();
    }
    try {
      await clearSession();
    } catch {
      /* ignora */
    }
    setUser(null);
    resetToastState();
    // Navegação "dura": garante que a próxima requisição use o cookie já limpo,
    // evitando a corrida em que o middleware ainda enxerga a sessão e redireciona
    // de volta para o dashboard.
    if (typeof window !== "undefined") {
      window.location.assign("/login");
    } else {
      router.push("/login");
    }
  }, [mode, router]);

  const value: AuthContextValue = {
    user,
    loading,
    mounted,
    mode,
    supabaseAvailable,
    setMode,
    startMagicLink,
    pollUntilAuthenticated,
    verifyOtpCode,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth deve ser usado dentro de <AuthProvider>");
  }
  return ctx;
}
