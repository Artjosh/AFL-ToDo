/**
 * Cliente Supabase para o navegador (apenas auth).
 *
 * Reaproveita o conceito do projeto gaming-cloud: um único browser client criado
 * sob demanda. Usado só no modo "Python Backend + Supabase Auth".
 *
 * Chave pública: usamos a NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY (formato novo
 * sb_publishable_...). A NEXT_PUBLIC_SUPABASE_ANON_KEY fica apenas como fallback
 * legado. A Supabase é usada SOMENTE para autenticação — sem tabelas/ORM.
 */
"use client";

import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";

let browserClient: SupabaseClient | null = null;

export function getSupabasePublicKey(): string | null {
  return (
    process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ||
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
    null
  );
}

export function isSupabaseConfigured(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_SUPABASE_URL && getSupabasePublicKey());
}

/** Retorna o browser client da Supabase (singleton) ou null se não configurado. */
export function getSupabaseClient(): SupabaseClient | null {
  if (!isSupabaseConfigured()) {
    return null;
  }
  if (browserClient) {
    return browserClient;
  }
  browserClient = createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    getSupabasePublicKey()!,
  );
  return browserClient;
}
