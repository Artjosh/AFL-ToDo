/**
 * Controle de estado dos toasts.
 *
 * Inspirado na lógica do projeto ats-example, que usa localStorage para lembrar
 * o que já foi mostrado/dispensado e evitar repetir notificações. Aqui aplicamos
 * o mesmo conceito aos toasts:
 *
 * - "mostrado": registra que um toast com determinada chave já apareceu, para não
 *   exibir de novo (ex.: aviso único por sessão).
 * - "clicado": registra que o usuário já interagiu com aquele toast.
 * - anti-spam: bloqueia toasts idênticos disparados em sequência muito próxima.
 *
 * Mantemos um registro em memória (para anti-spam dentro da mesma sessão) e,
 * opcionalmente, persistimos em localStorage para toasts do tipo "once".
 */

const STORAGE_PREFIX = "todo-toast:";

// Janela anti-spam: o mesmo conteúdo não reaparece dentro deste intervalo (ms).
const ANTI_SPAM_WINDOW_MS = 4000;

// Registro em memória do último disparo por assinatura de conteúdo.
const recentSignatures = new Map<string, number>();

// Registro em memória de toasts "once" já mostrados nesta sessão.
const shownOnceMemory = new Set<string>();

// Registro em memória de toasts já clicados nesta sessão.
const clickedMemory = new Set<string>();

function hasWindow(): boolean {
  return typeof window !== "undefined";
}

/**
 * Verifica se um conteúdo idêntico foi disparado recentemente (anti-spam).
 * Retorna true se deve ser BLOQUEADO.
 */
export function isSpam(signature: string): boolean {
  const now = Date.now();
  const last = recentSignatures.get(signature);
  recentSignatures.set(signature, now);

  // Limpa entradas antigas para não crescer indefinidamente.
  for (const [key, ts] of recentSignatures) {
    if (now - ts > ANTI_SPAM_WINDOW_MS) {
      recentSignatures.delete(key);
    }
  }

  if (last !== undefined && now - last < ANTI_SPAM_WINDOW_MS) {
    return true;
  }
  return false;
}

/** Marca um toast "once" como já mostrado (memória + localStorage). */
export function markShown(key: string): void {
  shownOnceMemory.add(key);
  if (hasWindow()) {
    try {
      window.localStorage.setItem(`${STORAGE_PREFIX}shown:${key}`, "1");
    } catch {
      // localStorage indisponível (modo privado etc.) — ignora.
    }
  }
}

/** Indica se um toast "once" já foi mostrado antes. */
export function wasShown(key: string): boolean {
  if (shownOnceMemory.has(key)) return true;
  if (hasWindow()) {
    try {
      return window.localStorage.getItem(`${STORAGE_PREFIX}shown:${key}`) === "1";
    } catch {
      return false;
    }
  }
  return false;
}

/** Marca que o usuário clicou/interagiu com um toast. */
export function markClicked(key: string): void {
  clickedMemory.add(key);
  if (hasWindow()) {
    try {
      window.localStorage.setItem(`${STORAGE_PREFIX}clicked:${key}`, "1");
    } catch {
      // ignora
    }
  }
}

/** Indica se o usuário já clicou naquele toast antes. */
export function wasClicked(key: string): boolean {
  if (clickedMemory.has(key)) return true;
  if (hasWindow()) {
    try {
      return window.localStorage.getItem(`${STORAGE_PREFIX}clicked:${key}`) === "1";
    } catch {
      return false;
    }
  }
  return false;
}

/** Limpa todo o estado persistido de toasts (útil em logout). */
export function resetToastState(): void {
  shownOnceMemory.clear();
  clickedMemory.clear();
  recentSignatures.clear();
  if (hasWindow()) {
    try {
      const keys: string[] = [];
      for (let i = 0; i < window.localStorage.length; i++) {
        const k = window.localStorage.key(i);
        if (k && k.startsWith(STORAGE_PREFIX)) keys.push(k);
      }
      keys.forEach((k) => window.localStorage.removeItem(k));
    } catch {
      // ignora
    }
  }
}
