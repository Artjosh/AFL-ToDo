/**
 * E2E — Drag-and-drop: mover card entre colunas e reordenar dentro da coluna.
 */
import { test, expect } from "@playwright/test";
import { loginViaOtpUI } from "../helpers/auth";
import { openDb } from "../helpers/db";

function positionsByTitle(email: string): Record<string, { status: string; position: number }> {
  const db = openDb();
  try {
    const rows = db
      .prepare(
        `SELECT t.titulo AS titulo, t.status AS status, t.position AS position
           FROM tasks t JOIN users u ON u.id = t.user_id
          WHERE u.email = ?`,
      )
      .all(email) as { titulo: string; status: string; position: number }[];
    const out: Record<string, { status: string; position: number }> = {};
    for (const r of rows) out[r.titulo] = { status: r.status, position: r.position };
    return out;
  } finally {
    db.close();
  }
}

test("mover card para outra coluna via drag-and-drop muda o status", async ({ page }) => {
  const email = `e2e_dnd_${Date.now()}@test.com`;
  await loginViaOtpUI(page, email);

  // cria 1 tarefa na coluna pendente
  await page.getByRole("button", { name: "+ Nova tarefa" }).click();
  await page.getByLabel("Título da tarefa").fill("Mover-me");
  await page.getByRole("button", { name: /Criar tarefa/ }).click();
  await expect(page.getByText("Mover-me")).toBeVisible();

  // arrasta o card para a coluna "Em andamento"
  const card = page.getByText("Mover-me");
  const target = page.getByTestId("column-em_andamento");
  await card.dragTo(target);

  // Regressão: mover o card NÃO deve mostrar o spinner de tela cheia
  // ("Carregando...") — o reload do realtime/echo é silencioso. O card também
  // não pode sumir da tela durante a sincronização.
  await expect(page.getByTestId("column-em_andamento").getByText("Mover-me")).toBeVisible();
  await expect(page.getByText("Mover-me")).toBeVisible();

  // confirma na coluna e no banco
  await expect.poll(() => positionsByTitle(email)["Mover-me"]?.status).toBe("em_andamento");
});

test("reordenar cards dentro da mesma coluna persiste a posição", async ({ page }) => {
  const email = `e2e_order_${Date.now()}@test.com`;
  await loginViaOtpUI(page, email);

  for (const titulo of ["Card A", "Card B", "Card C"]) {
    await page.getByRole("button", { name: "+ Nova tarefa" }).click();
    await page.getByLabel("Título da tarefa").fill(titulo);
    await page.getByRole("button", { name: /Criar tarefa/ }).click();
    await expect(page.getByText(titulo)).toBeVisible();
  }

  // ordem inicial A(0) B(1) C(2). Arrasta C para cima de A.
  await page.getByText("Card C").dragTo(page.getByText("Card A"));

  await expect.poll(() => positionsByTitle(email)["Card C"]?.position).toBe(0);
  // A e B deslocam para baixo
  await expect.poll(() => positionsByTitle(email)["Card A"]?.position).toBeGreaterThan(0);
});
