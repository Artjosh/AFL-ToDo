/**
 * Route handlers do fim do login (BFF) — modo local e Supabase cross-device.
 *
 * Estes endpoints rodam no servidor do Next. Eles falam com o backend Python,
 * e quando o login é aprovado, gravam o token de sessão direto no cookie
 * httpOnly — devolvendo ao browser APENAS o usuário, nunca o token. Assim, no
 * modo local (foco do projeto) o token de sessão jamais toca o JavaScript.
 *
 * - POST /api/auth/login?step=otp   body { selector, code }
 * - POST /api/auth/login?step=poll  body { selector }
 */
import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";

import {
  PROVIDER_COOKIE,
  SESSION_COOKIE,
  backendBaseUrl,
  sessionCookieOptions,
} from "@/lib/server-env";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const SESSION_MAX_AGE = 60 * 60 * 24;

interface BackendLoginResult {
  status: string;
  authenticated: boolean;
  provider: string;
  access_token: string | null;
  refresh_token: string | null;
  user: unknown;
}

async function persistSession(result: BackendLoginResult) {
  const store = await cookies();
  store.set(
    SESSION_COOKIE,
    result.access_token as string,
    sessionCookieOptions(SESSION_MAX_AGE),
  );
  store.set(PROVIDER_COOKIE, result.provider || "local", {
    ...sessionCookieOptions(SESSION_MAX_AGE),
    httpOnly: false,
  });
}

export async function POST(request: NextRequest) {
  const step = request.nextUrl.searchParams.get("step");
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ detail: "JSON inválido." }, { status: 400 });
  }

  if (step === "otp") {
    const res = await fetch(`${backendBaseUrl()}/auth/verify-otp`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ selector: body.selector, code: body.code }),
      cache: "no-store",
    });
    const data = (await res.json()) as BackendLoginResult & { detail?: string };
    if (!res.ok) {
      return NextResponse.json({ detail: data.detail ?? "Erro." }, { status: res.status });
    }
    if (data.access_token) await persistSession(data);
    return NextResponse.json({ user: data.user, provider: data.provider });
  }

  if (step === "poll") {
    const selector = encodeURIComponent(String(body.selector ?? ""));
    const res = await fetch(
      `${backendBaseUrl()}/auth/login-status?selector=${selector}`,
      { method: "POST", cache: "no-store" },
    );
    const data = (await res.json()) as BackendLoginResult & { detail?: string };
    if (!res.ok) {
      return NextResponse.json({ detail: data.detail ?? "Erro." }, { status: res.status });
    }
    if (data.status === "approved" && data.access_token) {
      await persistSession(data);
      return NextResponse.json({ status: "approved", user: data.user, provider: data.provider });
    }
    return NextResponse.json({ status: data.status, provider: data.provider });
  }

  return NextResponse.json({ detail: "Step inválido." }, { status: 400 });
}
