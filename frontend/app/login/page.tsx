/**
 * Página de login passwordless (única porta de entrada — sem cadastro separado).
 *
 * O redirect para o dashboard é REATIVO ao `user`: assim que a sessão é
 * estabelecida (via polling do magic link, OTP, ou restauração no F5), o efeito
 * abaixo navega. Centralizar o redirect aqui evita a corrida que deixava a aba
 * "presa" no login após confirmar o link (era preciso dar F5).
 */
"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import AuthForm from "@/components/auth-form";
import { useAuth } from "@/components/auth-provider";
import GuidedTour from "@/components/guided-tour";

export default function LoginPage() {
  const { user } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.replace("/dashboard");
    }
  }, [user, router]);

  return (
    <>
      <GuidedTour />
      <AuthForm />
    </>
  );
}
