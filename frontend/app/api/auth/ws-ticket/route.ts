/**
 * Route handler do ticket de WebSocket (BFF).
 *
 * POST /api/auth/ws-ticket -> usa o cookie httpOnly de sessão para pedir ao
 * backend um ticket efêmero (válido por segundos) e o devolve ao browser. O
 * browser usa esse ticket descartável na URL do WebSocket, sem nunca conhecer o
 * token de sessão real.
 */
import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import { SESSION_COOKIE, backendBaseUrl } from "@/lib/server-env";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function POST() {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;
  if (!token) {
    return NextResponse.json({ detail: "Sem sessão." }, { status: 401 });
  }

  const res = await fetch(`${backendBaseUrl()}/auth/ws-ticket`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!res.ok) {
    return NextResponse.json({ detail: "Falha ao emitir ticket." }, { status: res.status });
  }
  const data = (await res.json()) as { ticket: string };
  return NextResponse.json({ ticket: data.ticket });
}
