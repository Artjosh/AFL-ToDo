/**
 * Configuração server-side do BFF (Backend-for-Frontend).
 *
 * Estas funções rodam SOMENTE no servidor do Next (route handlers / middleware).
 * O token de sessão fica num cookie httpOnly e nunca é exposto ao browser; o
 * Next é o único que conhece o token e o repassa ao FastAPI como Bearer.
 */

/** Nome do cookie httpOnly que guarda o token de sessão (JWT local ou Supabase). */
export const SESSION_COOKIE = "todo_session";

/** Nome do cookie que guarda o provider ativo ("local" | "supabase"). */
export const PROVIDER_COOKIE = "todo_provider";

/**
 * URL interna do backend Python, usada pelo SERVIDOR do Next para falar com o
 * FastAPI. Em dev aponta para o mesmo host/IP. Pode ser sobrescrita por
 * BACKEND_INTERNAL_URL (ex.: nome de serviço no docker-compose).
 */
export function backendBaseUrl(): string {
  const url =
    process.env.BACKEND_INTERNAL_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";
  return url.replace(/\/$/, "");
}

/** Opções padrão do cookie de sessão (httpOnly, sameSite lax). */
export function sessionCookieOptions(maxAgeSeconds: number) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: maxAgeSeconds,
  };
}
