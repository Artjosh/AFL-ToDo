/**
 * E2E — Login passwordless (modo local) e tour guiado.
 * Cobre UI + comportamento do tour + entrada no dashboard via OTP.
 */
import { test, expect } from "@playwright/test";
import { dismissTour, loginViaOtpUI, loginViaOtpCodeUI, suppressTour } from "../helpers/auth";
import { userExists } from "../helpers/db";

test.describe("Login passwordless (modo local)", () => {
  test("tour guiado aparece no primeiro acesso e pode ser fechado", async ({ page, context }) => {
    await context.clearCookies();
    await page.goto("/login");
    // O tour abre automaticamente.
    await expect(page.getByText("Passo 1 de 4")).toBeVisible();
    await expect(page.getByText("Bem-vindo ao ToDo AFL")).toBeVisible();

    // Avança um passo.
    await page.getByRole("button", { name: /Próximo/ }).click();
    await expect(page.getByText("Passo 2 de 4")).toBeVisible();

    // Fecha pelo "Pular".
    await page.getByRole("button", { name: "Pular" }).click();
    await expect(page.getByText("Passo 2 de 4")).not.toBeVisible();
  });

  test("botão ? reabre o tour", async ({ page }) => {
    await page.goto("/login");
    await dismissTour(page);
    await page.getByRole("button", { name: "Ver o tour novamente" }).click();
    await expect(page.getByText(/Passo 1 de 4/)).toBeVisible();
  });

  test("login via OTP entra no dashboard e cria usuário no banco", async ({ page }) => {
    const email = `e2e_login_${Date.now()}@test.com`;
    await loginViaOtpUI(page, email);

    // UI no dashboard
    await expect(page.getByRole("heading", { name: "Meu quadro" })).toBeVisible();
    // Camada de dados: usuário criado no SQLite
    expect(userExists(email)).toBe(true);
  });

  test("login digitando o código OTP de 6 dígitos", async ({ page }) => {
    const email = `e2e_otp_${Date.now()}@test.com`;
    await loginViaOtpCodeUI(page, email);
    await expect(page.getByRole("heading", { name: "Meu quadro" })).toBeVisible();
    expect(userExists(email)).toBe(true);
  });

  test("email inválido não avança para a tela de confirmação", async ({ page }) => {
    await suppressTour(page);
    await page.goto("/login");
    await page.getByLabel("Email").fill("nao-eh-email");
    await page.getByRole("button", { name: "Enviar link de acesso" }).click();
    // Campo type=email inválido + validação no submit: não vai para "aguardando".
    await expect(page.getByText("Verifique seu acesso")).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Enviar link de acesso" })).toBeVisible();
  });
});
