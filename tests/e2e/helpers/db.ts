/**
 * Helper para inspecionar o banco SQLite de teste direto nos specs E2E.
 * Permite verificar a camada de dados além da UI e do HTTP.
 */
import path from "node:path";
import Database from "better-sqlite3";

const E2E_DB = path.resolve(__dirname, "..", "e2e.db");

export function openDb() {
  return new Database(E2E_DB, { readonly: true, fileMustExist: false });
}

export function countTasksByEmail(email: string): number {
  const db = openDb();
  try {
    const row = db
      .prepare(
        `SELECT COUNT(*) AS n
           FROM tasks t
           JOIN users u ON u.id = t.user_id
          WHERE u.email = ?`,
      )
      .get(email) as { n: number } | undefined;
    return row?.n ?? 0;
  } finally {
    db.close();
  }
}

export function getTaskTitlesByEmail(email: string): string[] {
  const db = openDb();
  try {
    const rows = db
      .prepare(
        `SELECT t.titulo AS titulo
           FROM tasks t
           JOIN users u ON u.id = t.user_id
          WHERE u.email = ?
          ORDER BY t.id`,
      )
      .all(email) as { titulo: string }[];
    return rows.map((r) => r.titulo);
  } finally {
    db.close();
  }
}

export function userExists(email: string): boolean {
  const db = openDb();
  try {
    const row = db
      .prepare(`SELECT 1 FROM users WHERE email = ? LIMIT 1`)
      .get(email);
    return Boolean(row);
  } finally {
    db.close();
  }
}
