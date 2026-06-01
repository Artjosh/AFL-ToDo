/**
 * Página raiz: redireciona para o dashboard (se logado) ou para o login.
 */
"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/auth-provider";

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? "/dashboard" : "/login");
  }, [user, loading, router]);

  return (
    <div className="flex min-h-[40vh] items-center justify-center text-muted">
      Carregando...
    </div>
  );
}
