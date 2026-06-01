/**
 * E2E — Login multi-dispositivo (modo local).
 *
 * Simula: o usuário pede o link no "device de origem" (a aba do navegador) e
 * clica o link em "outro device" (uma chamada HTTP independente ao /auth/confirm).
 * A aba de origem deve detectar a confirmação via polling e entrar sozinha.
 */
import { test, expect, request as pwRequest } from "@playwright/test";
import { suppressTour } from "../helpers/auth";
import { userExists } from "../helpers/db";

test("magic link clicado em outro device confirma a aba de origem (polling)", async ({ page }) => {
  const email = `e2e_multi_${Date.now()}@test.com`;

  // Device de origem: inicia o login pela UI.
  await suppressTour(page);
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Enviar link de acesso" }).click();
  await expect(page.getByText("Verifique seu acesso")).toBeVisible();

  // Lê o link (dev) exibido na tela — é o que iria no email.
  const linkLocator = page.getByRole("link", { name: /\/auth\/confirm\?token=/ });
  await expect(linkLocator).toBeVisible();
  const magicUrl = await linkLocator.getAttribute("href");
  expect(magicUrl).toBeTruthy();

  // "Outro device": abre o link via um contexto HTTP independente (sem cookies da aba).
  const ctx = await pwRequest.newContext();
  const res = await ctx.get(magicUrl!);
  expect(res.ok()).toBeTruthy();
  await ctx.dispose();

  // Regressão: a aba de origem deve ir SOZINHA para o dashboard (sem F5/reload),
  // reagindo ao polling. Antes, o toaster aparecia mas a navegação não ocorria.
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 20_000 });
  await expect(page.getByRole("heading", { name: "Meu quadro" })).toBeVisible();

  expect(userExists(email)).toBe(true);
});

test("login pelo CÓDIGO OTP redireciona sozinho (sem F5)", async ({ page }) => {
  const email = `e2e_otp_redirect_${Date.now()}@test.com`;

  await suppressTour(page);
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByRole("button", { name: "Enviar link de acesso" }).click();
  await expect(page.getByText("Verifique seu acesso")).toBeVisible();

  // Lê o código OTP (dev) e digita.
  const otp = page.locator("p.tracking-\\[0\\.3em\\]").first();
  await expect(otp).toBeVisible();
  const code = (await otp.textContent())?.trim() ?? "";
  await page.getByPlaceholder("••••••").fill(code);
  await page.getByRole("button", { name: "Entrar com o código" }).click();

  // Redirect automático após verificar o código.
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });
  await expect(page.getByRole("heading", { name: "Meu quadro" })).toBeVisible();
});
