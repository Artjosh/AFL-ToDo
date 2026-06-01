/**
 * Helper de autenticação para os specs E2E.
 *
 * No modo dev (sem SMTP), a tela de "aguardando" mostra o magic link e o código
 * OTP na própria página. Lemos esses valores do DOM para dirigir o fluxo sem
 * invalidar o pedido pendente (chamar /auth/magic-link de novo trocaria o selector).
 */
import { APIRequestContext, expect, Page, request as pwRequest } from "@playwright/test";

const API = "http://localhost:8100";

export async function requestMagicLinkApi(
  request: APIRequestContext,
  email: string,
) {
  const res = await request.post(`${API}/auth/magic-link`, { data: { email } });
  expect(res.ok()).toBeTruthy();
  const body = await res.json();
  return {
    selector: body.selector as string,
    devMagicUrl: body.dev_magic_url as string,
    devOtpCode: body.dev_otp_code as string,
  };
}

/** Fecha o tour guiado se estiver aberto (espera ele aparecer, com tolerância). */
export async function dismissTour(page: Page) {
  const skip = page.getByRole("button", { name: "Pular" });
  try {
    await skip.waitFor({ state: "visible", timeout: 2000 });
    await skip.click();
    await skip.waitFor({ state: "hidden", timeout: 2000 });
  } catch {
    // Tour não apareceu (já visto) — nada a fazer.
  }
}

/**
 * Marca o tour como já visto antes da página carregar, evitando que o overlay
 * (que intercepta cliques) interfira nos testes que não são sobre o tour.
 */
export async function suppressTour(page: Page) {
  await page.addInitScript(() => {
    try {
      window.localStorage.setItem("todo-toast:shown:guided-tour", "1");
    } catch {
      // ignore
    }
  });
}

/** Inicia o login pela UI e retorna o código OTP lido da tela (modo dev). */
export async function startLoginUI(page: Page, email: string): Promise<string> {
  await suppressTour(page);
  await page.goto("/login");

  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Enviar link de acesso" }).click();

  await expect(page.getByText("Verifique seu acesso")).toBeVisible();

  // Lê o código OTP exibido no painel dev (label "Código (dev)").
  const otp = page.locator("p.tracking-\\[0\\.3em\\]").first();
  await expect(otp).toBeVisible();
  const code = (await otp.textContent())?.trim() ?? "";
  expect(code).toMatch(/^\d{6}$/);
  return code;
}

/** Login completo pela UI. Usa o link dev exibido na tela (modo dev) e o polling. */
export async function loginViaOtpUI(page: Page, email: string): Promise<void> {
  await suppressTour(page);
  await page.goto("/login");

  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Enviar link de acesso" }).click();
  await expect(page.getByText("Verifique seu acesso")).toBeVisible();

  // Abre o link dev em um contexto HTTP separado (simula clicar o link).
  const linkLocator = page.getByRole("link", { name: /\/auth\/confirm\?token=/ });
  await expect(linkLocator).toBeVisible();
  const magicUrl = await linkLocator.getAttribute("href");
  const ctx = await pwRequest.newContext();
  await ctx.get(magicUrl!);
  await ctx.dispose();

  // A aba detecta a confirmação por polling e vai para o dashboard.
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 });
}

/** Login pela UI digitando o código OTP (caminho alternativo, mesmo device). */
export async function loginViaOtpCodeUI(page: Page, email: string): Promise<void> {
  const code = await startLoginUI(page, email);
  await page.getByPlaceholder("••••••").fill(code);
  await page.getByRole("button", { name: "Entrar com o código" }).click();
  await expect(page).toHaveURL(/\/dashboard/);
}
