/**
 * E2E — Realtime do board (WebSocket).
 *
 * Dois usuários no MESMO projeto compartilhado: quando o dono cria uma tarefa,
 * o board do membro (em outra sessão) atualiza ao vivo, sem recarregar a página.
 *
 * Roda com o broadcaster local (sem Redis) — suficiente porque o E2E sobe um
 * único processo de backend. Com Redis, o mesmo funcionaria entre réplicas.
 */
import { test, expect } from "@playwright/test";
import { loginViaOtpUI } from "../helpers/auth";

test("tarefa criada pelo dono aparece ao vivo no board do membro", async ({ browser, request }) => {
  const owner = `rt_owner_${Date.now()}@test.com`;
  const member = `rt_member_${Date.now()}@test.com`;

  // Cria a conta do membro antecipadamente (precisa existir para ser convidado).
  const ml = await request.post("http://localhost:8100/auth/magic-link", {
    data: { email: member },
  });
  const body = await ml.json();
  await request.get(body.dev_magic_url);
  await request.post(
    `http://localhost:8100/auth/login-status?selector=${encodeURIComponent(body.selector)}`,
  );

  // Sessão do dono
  const ownerCtx = await browser.newContext();
  const ownerPage = await ownerCtx.newPage();
  await loginViaOtpUI(ownerPage, owner);

  // Dono cria projeto e adiciona o membro
  await ownerPage.getByRole("button", { name: "+ Novo projeto" }).click();
  await ownerPage.getByLabel("Nome do projeto").fill("Sprint RT");
  await ownerPage.getByRole("button", { name: /Criar projeto/ }).click();
  await ownerPage.getByText("Sprint RT").click();
  await ownerPage.getByRole("button", { name: /Membros/ }).click();
  await ownerPage.getByLabel("Email do novo membro").fill(member);
  await ownerPage.getByRole("button", { name: "Adicionar" }).click();
  await expect(ownerPage.getByText(member)).toBeVisible();
  await ownerPage.getByRole("button", { name: "Fechar", exact: true }).click();

  // Sessão do membro: abre o MESMO projeto
  const memberCtx = await browser.newContext();
  const memberPage = await memberCtx.newPage();
  await loginViaOtpUI(memberPage, member);
  await memberPage.getByText("Sprint RT").click();
  await expect(memberPage.getByRole("heading", { name: /Sprint RT/ })).toBeVisible();

  // Dá um tempo para a conexão WS do membro estabilizar antes de publicar.
  await memberPage.waitForTimeout(1500);

  // Dono cria uma tarefa no projeto
  await ownerPage.getByRole("button", { name: "+ Nova tarefa" }).click();
  await ownerPage.getByLabel("Título da tarefa").fill("Tarefa ao vivo");
  await ownerPage.getByRole("button", { name: /Criar tarefa/ }).click();
  await expect(ownerPage.getByText("Tarefa ao vivo")).toBeVisible();

  // A tarefa aparece no board do MEMBRO sem recarregar (via realtime).
  await expect(memberPage.getByText("Tarefa ao vivo")).toBeVisible({ timeout: 15_000 });

  await ownerCtx.close();
  await memberCtx.close();
});
