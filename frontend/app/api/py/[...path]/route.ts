/**
 * Proxy BFF para o backend Python (FastAPI).
 *
 * Todas as chamadas de dados do browser passam por aqui (same-origin), por
 * exemplo: GET /api/py/tasks -> GET <backend>/tasks.
 *
 * O handler lê o token de sessão do cookie httpOnly e o injeta como
 * Authorization: Bearer ao falar com o FastAPI. Assim, o token NUNCA é exposto
 * ao JavaScript do browser, mas o backend continua sendo a fonte de verdade e
 * revalida o token em toda requisição.
 */
import { cookies } from "next/headers";
import { NextResponse, type NextRequest } from "next/server";

import { SESSION_COOKIE, backendBaseUrl } from "@/lib/server-env";

// Nunca cachear o proxy: cada chamada deve refletir o estado atual do backend.
export const dynamic = "force-dynamic";
export const runtime = "nodejs";

// Hop-by-hop e headers que não devem ser repassados.
const SKIP_REQUEST_HEADERS = new Set([
  "host",
  "connection",
  "content-length",
  "cookie",
  "authorization",
]);

async function handle(request: NextRequest, segments: string[]): Promise<NextResponse> {
  const store = await cookies();
  const token = store.get(SESSION_COOKIE)?.value;

  const path = segments.map(encodeURIComponent).join("/");
  const search = request.nextUrl.search;
  const targetUrl = `${backendBaseUrl()}/${path}${search}`;

  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!SKIP_REQUEST_HEADERS.has(key.toLowerCase())) {
      headers.set(key, value);
    }
  });
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const method = request.method.toUpperCase();
  const hasBody = method !== "GET" && method !== "HEAD";

  let backendRes: Response;
  try {
    backendRes = await fetch(targetUrl, {
      method,
      headers,
      body: hasBody ? await request.text() : undefined,
      cache: "no-store",
      redirect: "manual",
    });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar à API." },
      { status: 502 },
    );
  }

  const resBody = await backendRes.text();
  const res = new NextResponse(resBody || null, { status: backendRes.status });
  const contentType = backendRes.headers.get("content-type");
  if (contentType) res.headers.set("content-type", contentType);
  return res;
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, ctx: Ctx) {
  return handle(request, (await ctx.params).path);
}
export async function POST(request: NextRequest, ctx: Ctx) {
  return handle(request, (await ctx.params).path);
}
export async function PATCH(request: NextRequest, ctx: Ctx) {
  return handle(request, (await ctx.params).path);
}
export async function PUT(request: NextRequest, ctx: Ctx) {
  return handle(request, (await ctx.params).path);
}
export async function DELETE(request: NextRequest, ctx: Ctx) {
  return handle(request, (await ctx.params).path);
}
