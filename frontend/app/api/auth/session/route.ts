/**
 * Route handler da sessão (BFF).
 *
 * - POST   /api/auth/session  -> recebe { token, provider } do fluxo de login e
 *                                grava o token num cookie httpOnly. Valida o
 *                                token contra o backend (/auth/me) antes.
 * - GET    /api/auth/session  -> devolve o usuário atual (a partir do cookie),
 *                                ou 401 se não houver sessão válida.
 * - DELETE /api/auth/session  -> limpa os cookies (logout).
 *
 * O token NUNCA é devolvido ao browser: ele vive apenas neste cookie httpOnly.
 */
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  PROVIDER_COOKIE,
  SESSION_COOKIE,
  backendBaseUrl,
  sessionCookieOptions,
} from "@/lib/server-env";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// Sessão de 1 dia (igual ao ACCESS_TOKEN_EXPIRE_MINUTES padrão do backend).
const SESSION_MAX_AGE = 60 * 60 * 24;

async function fetchMe(token: string) {
  const res = await fetch(`${backendBaseUrl()}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  if (!res.ok) return null;
  return (await res.json()) as unknown;
}

export async function POST(request: Request) {
  let body: { token?: string; provider?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "JSON inválido." }, { status: 400 });
  }

  const token = body.token?.trim();
  const provider = body.provider === "supabase" ? "supabase" : "local";
  if (!token) {
    return NextResponse.json({ detail: "Token ausente." }, { status: 400 });
  }

  // Valida o token contra o backend antes de aceitar a sessão.
  const user = await fetchMe(token);
  if (!user) {
    return NextResponse.json({ detail: "Token inválido." }, { status: 401 });
  }

  const store = await cookies();
  store.set(SESSION_COOKIE, token, sessionCookieOptions(SESSION_MAX_AGE));
  store.set(PROVIDER_COOKIE, provider, {
    ...sessionCookieOptions(SESSION_MAX_AGE),
    httpOnly: false, // o provider não é segredo; a UI pode lê-lo
  });

  return NextResponse.json({ user, provider });
}

export async function GET() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Sem sessão." }, { status: 401 });
  }
  const user = await fetchMe(token);
  if (!user) {
    // cookie inválido/expirado: limpa para evitar loop
    store.delete(SESSION_COOKIE);
    store.delete(PROVIDER_COOKIE);
    return NextResponse.json({ detail: "Sessão expirada." }, { status: 401 });
  }
  const provider = store.get(PROVIDER_COOKIE)?.value === "supabase" ? "supabase" : "local";
  return NextResponse.json({ user, provider });
}

export async function DELETE() {
  const store = await cookies();
  // Expira explicitamente (path "/") para garantir a remoção em todos os browsers.
  const expire = { ...sessionCookieOptions(0), maxAge: 0 };
  store.set(SESSION_COOKIE, "", expire);
  store.set(PROVIDER_COOKIE, "", { ...expire, httpOnly: false });
  return NextResponse.json({ ok: true });
}
