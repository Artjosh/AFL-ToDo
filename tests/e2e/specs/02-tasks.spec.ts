/**
 * E2E — Board Kanban: criar tarefa, abrir detalhe, mover entre colunas e excluir.
 * Cobre UI + camada de dados (SQLite).
 */
import { test, expect } from "@playwright/test";
import { loginViaOtpUI } from "../helpers/auth";
import { countTasksByEmail } from "../helpers/db";

test.describe("Board de tarefas", () => {
  test("cria tarefa, edita no detalhe e exclui — refletindo no banco", async ({ page }) => {
    const email = `e2e_tasks_${Date.now()}@test.com`;
    await loginViaOtpUI(page, email);

    await expect(page.getByRole("heading", { name: "Meu quadro" })).toBeVisible();

    // --- criar tarefa ---
    await page.getByRole("button", { name: "+ Nova tarefa" }).click();
    await page.getByLabel("Título da tarefa").fill("Comprar café");
    await page.getByLabel("Descrição").fill("pacote 1kg");
    await page.getByRole("button", { name: /Criar tarefa/ }).click();

    // card aparece no board
    const card = page.getByText("Comprar café");
    await expect(card).toBeVisible();
    expect(countTasksByEmail(email)).toBe(1);

    // --- abrir detalhe e mudar status para concluída ---
    await card.click();
    await expect(page.getByText(/^Tarefa #\d+$/)).toBeVisible();
    await page.getByLabel("Status").selectOption("concluida");
    await page.getByRole("button", { name: "Salvar" }).click();

    // o card agora aparece na coluna "Concluída"
    const concluida = page.getByTestId("column-concluida");
    await expect(concluida.getByText("Comprar café")).toBeVisible();

    // --- excluir ---
    await page.getByText("Comprar café").click();
    page.once("dialog", (d) => d.accept());
    await page.getByRole("button", { name: "Excluir tarefa" }).click();
    await expect(page.getByText("Comprar café")).toHaveCount(0);
    expect(countTasksByEmail(email)).toBe(0);
  });

  test("isolamento: tarefas não vazam entre usuários", async ({ page }) => {
    const emailA = `e2e_iso_a_${Date.now()}@test.com`;
    const emailB = `e2e_iso_b_${Date.now()}@test.com`;

    await loginViaOtpUI(page, emailA);
    await page.getByRole("button", { name: "+ Nova tarefa" }).click();
    await page.getByLabel("Título da tarefa").fill("Segredo do A");
    await page.getByRole("button", { name: /Criar tarefa/ }).click();
    await expect(page.getByText("Segredo do A")).toBeVisible();

    await page.getByRole("button", { name: "Sair" }).click();
    await expect(page).toHaveURL(/\/login/);

    await loginViaOtpUI(page, emailB);
    await expect(page.getByText("Segredo do A")).toHaveCount(0);

    expect(countTasksByEmail(emailA)).toBe(1);
    expect(countTasksByEmail(emailB)).toBe(0);
  });
});
