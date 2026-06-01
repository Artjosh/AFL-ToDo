/**
 * E2E — Projetos (board aninhado) + compartilhamento + atribuídos.
 * Cobre UI + dados: criar projeto, abrir board, criar task no projeto,
 * adicionar membro e atribuir pessoa.
 */
import { test, expect } from "@playwright/test";
import { loginViaOtpUI } from "../helpers/auth";
import { countTasksByEmail } from "../helpers/db";

test("cria projeto, abre board, adiciona tarefa, membro e atribuído", async ({ page, request }) => {
  const owner = `e2e_proj_${Date.now()}@test.com`;
  const colega = `e2e_colega_${Date.now()}@test.com`;

  // O colega precisa existir (acessar ao menos uma vez) para ser convidável.
  // Cria a conta dele via API (modo dev devolve link).
  const ml = await request.post("http://localhost:8100/auth/magic-link", {
    data: { email: colega },
  });
  const body = await ml.json();
  await request.get(body.dev_magic_url);
  await request.post(`http://localhost:8100/auth/login-status?selector=${encodeURIComponent(body.selector)}`);

  // Owner entra
  await loginViaOtpUI(page, owner);

  // --- cria projeto ---
  await page.getByRole("button", { name: "+ Novo projeto" }).click();
  await page.getByLabel("Nome do projeto").fill("Lançamento Q3");
  await page.getByRole("button", { name: /Criar projeto/ }).click();

  // o projeto aparece como card na coluna pendente
  const projectCard = page.getByText("Lançamento Q3");
  await expect(projectCard).toBeVisible();

  // --- abre o board do projeto ---
  await projectCard.click();
  await expect(page.getByRole("heading", { name: /Lançamento Q3/ })).toBeVisible();

  // --- cria tarefa dentro do projeto ---
  await page.getByRole("button", { name: "+ Nova tarefa" }).click();
  await page.getByLabel("Título da tarefa").fill("Definir escopo");
  await page.getByRole("button", { name: /Criar tarefa/ }).click();
  await expect(page.getByText("Definir escopo")).toBeVisible();
  expect(countTasksByEmail(owner)).toBe(1);

  // --- adiciona membro ao projeto (compartilhamento) ---
  await page.getByRole("button", { name: /Membros/ }).click();
  await page.getByLabel("Email do novo membro").fill(colega);
  await page.getByRole("button", { name: "Adicionar" }).click();
  await expect(page.getByText(colega)).toBeVisible();
  // fecha o modal de membros (X do modal, exato — evita casar com toasts)
  await page.getByRole("button", { name: "Fechar", exact: true }).click();

  // --- atribui o colega à tarefa ---
  await page.getByText("Definir escopo").click();
  await expect(page.getByText(/^Tarefa #\d+$/)).toBeVisible();
  await page.getByPlaceholder("email@pessoa.com").fill(colega);
  await page.getByRole("button", { name: "Atribuir" }).click();
  // o email do atribuído aparece na lista de pessoas atribuídas do modal
  await expect(page.getByText(colega).first()).toBeVisible();
});

test("membro convidado vê o projeto compartilhado", async ({ page, request, browser }) => {
  const owner = `e2e_owner_${Date.now()}@test.com`;
  const membro = `e2e_membro_${Date.now()}@test.com`;

  // cria conta do membro
  const ml = await request.post("http://localhost:8100/auth/magic-link", {
    data: { email: membro },
  });
  const body = await ml.json();
  await request.get(body.dev_magic_url);
  await request.post(`http://localhost:8100/auth/login-status?selector=${encodeURIComponent(body.selector)}`);

  // owner cria projeto e compartilha
  await loginViaOtpUI(page, owner);
  await page.getByRole("button", { name: "+ Novo projeto" }).click();
  await page.getByLabel("Nome do projeto").fill("Projeto Compartilhado");
  await page.getByRole("button", { name: /Criar projeto/ }).click();
  await page.getByText("Projeto Compartilhado").click();
  await page.getByRole("button", { name: /Membros/ }).click();
  await page.getByLabel("Email do novo membro").fill(membro);
  await page.getByRole("button", { name: "Adicionar" }).click();
  await expect(page.getByText(membro)).toBeVisible();

  // membro entra em outra sessão e vê o projeto
  const ctx = await browser.newContext();
  const page2 = await ctx.newPage();
  await loginViaOtpUI(page2, membro);
  await expect(page2.getByText("Projeto Compartilhado")).toBeVisible();
  await ctx.close();
});


test("permissões: membro sem can_move_tasks não arrasta; dono configura e libera", async ({
  page,
  request,
  browser,
}) => {
  const owner = `e2e_perm_owner_${Date.now()}@test.com`;
  const membro = `e2e_perm_membro_${Date.now()}@test.com`;

  // cria conta do membro
  const ml = await request.post("http://localhost:8100/auth/magic-link", {
    data: { email: membro },
  });
  const body = await ml.json();
  await request.get(body.dev_magic_url);
  await request.post(
    `http://localhost:8100/auth/login-status?selector=${encodeURIComponent(body.selector)}`,
  );

  // dono cria projeto, tarefa e compartilha
  await loginViaOtpUI(page, owner);
  await page.getByRole("button", { name: "+ Novo projeto" }).click();
  await page.getByLabel("Nome do projeto").fill("Proj Permissões");
  await page.getByRole("button", { name: /Criar projeto/ }).click();
  await page.getByText("Proj Permissões").click();
  await page.getByRole("button", { name: "+ Nova tarefa" }).click();
  await page.getByLabel("Título da tarefa").fill("Tarefa controlada");
  await page.getByRole("button", { name: /Criar tarefa/ }).click();
  await expect(page.getByText("Tarefa controlada")).toBeVisible();

  // adiciona membro e REMOVE a permissão de mover tarefas
  await page.getByRole("button", { name: /Membros/ }).click();
  await page.getByLabel("Email do novo membro").fill(membro);
  await page.getByRole("button", { name: "Adicionar" }).click();
  await expect(page.getByText(membro)).toBeVisible();
  // desmarca "Mover tarefas" para o membro (localiza pelo título do checkbox).
  // O onChange dispara PATCH + reload; usamos click e aguardamos a resposta.
  const moverTarefasCheckbox = page
    .locator('label[title="arrastar tarefas entre colunas"] input[type="checkbox"]')
    .first();
  await expect(moverTarefasCheckbox).toBeChecked();
  await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes("/members/") && r.request().method() === "PATCH",
    ),
    moverTarefasCheckbox.click(),
  ]);
  await page.getByRole("button", { name: "Fechar", exact: true }).click();

  // membro entra: vê a tarefa mas o card NÃO é arrastável (sem permissão)
  const ctx = await browser.newContext();
  const page2 = await ctx.newPage();
  await loginViaOtpUI(page2, membro);
  await page2.getByText("Proj Permissões").click();
  await expect(page2.getByText("Tarefa controlada")).toBeVisible();
  // o botão "+ Nova tarefa" continua disponível (can_manage_tasks default true),
  // mas o card não deve ter draggable=true
  const card = page2.getByTestId(/^card-\d+$/).first();
  await expect(card).toHaveAttribute("draggable", "false");

  await ctx.close();
});


test("dono move o PROJETO entre colunas (status do projeto)", async ({ page }) => {
  const owner = `e2e_projmove_${Date.now()}@test.com`;
  await loginViaOtpUI(page, owner);

  // cria projeto (nasce em Pendente)
  await page.getByRole("button", { name: "+ Novo projeto" }).click();
  await page.getByLabel("Nome do projeto").fill("Projeto Móvel");
  await page.getByRole("button", { name: /Criar projeto/ }).click();

  // o card do projeto aparece na coluna PENDENTE
  const pendente = page.getByTestId("column-pendente");
  await expect(pendente.getByText("Projeto Móvel")).toBeVisible();

  // arrasta o card do projeto para "Em andamento"
  const projectCard = page.getByText("Projeto Móvel");
  const emAndamento = page.getByTestId("column-em_andamento");
  await projectCard.dragTo(emAndamento);

  // o projeto agora aparece na coluna "Em andamento" (status mudou)
  await expect(
    page.getByTestId("column-em_andamento").getByText("Projeto Móvel"),
  ).toBeVisible();
  // e some da coluna pendente
  await expect(
    page.getByTestId("column-pendente").getByText("Projeto Móvel"),
  ).toHaveCount(0);
});
