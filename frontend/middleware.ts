/**
 * Middleware do Next.js (padrão BFF).
 *
 * Faz duas coisas:
 * 1. Gating SSR de rotas protegidas: sem o cookie de sessão httpOnly, o acesso a
 *    /dashboard é redirecionado para /login no próprio servidor (sem flash de
 *    conteúdo). Estando logado, /login redireciona para /dashboard.
 * 2. Quando o Supabase está configurado, faz o refresh dos cookies de sessão a
 *    cada navegação (como no projeto gaming-cloud).
 *
 * A proteção dos dados continua garantida pelo backend Python, que valida o
 * token em toda requisição (o middleware é só uma camada de UX/roteamento).
 */
import { NextResponse, type NextRequest } from "next/server";
import { createServerClient, type CookieOptions } from "@supabase/ssr";

import { SESSION_COOKIE } from "@/lib/server-env";

interface CookieToSet {
  name: string;
  value: string;
  options?: CookieOptions;
}

const PROTECTED_PREFIXES = ["/dashboard"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasSession = Boolean(request.cookies.get(SESSION_COOKIE)?.value);

  // Gating de rotas: protege /dashboard e tira logado de /login.
  const isProtected = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  if (isProtected && !hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  if (pathname === "/login" && hasSession) {
    const url = request.nextUrl.clone();
    url.pathname = "/dashboard";
    return NextResponse.redirect(url);
  }

  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey =
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  if (!supabaseUrl || !supabaseKey) {
    return NextResponse.next();
  }

  let response = NextResponse.next({ request });

  const supabase = createServerClient(supabaseUrl, supabaseKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet: CookieToSet[]) {
        cookiesToSet.forEach(({ name, value }) =>
          request.cookies.set(name, value),
        );
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
      },
    },
  });

  await supabase.auth.getUser();

  return response;
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
