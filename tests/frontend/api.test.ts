/**
 * Testes do cliente da API no padrão BFF (mockando fetch).
 *
 * O browser fala apenas com rotas same-origin do Next:
 * - dados via /api/py/*  (o proxy injeta o token no servidor)
 * - login local via /api/auth/login (o servidor grava o cookie httpOnly)
 * Por isso, nenhuma chamada do browser envia Authorization nem token.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  checkLoginStatus,
  createTask,
  deleteTask,
  listTasks,
  requestMagicLink,
  verifyOtp,
} from "@/lib/api";

function mockFetchOnce(body: unknown, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    text: async () => (body === undefined ? "" : JSON.stringify(body)),
  });
}

describe("lib/api (BFF)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("requestMagicLink chama o proxy same-origin e retorna selector", async () => {
    const fetchMock = mockFetchOnce({
      selector: "sel-1",
      email: "a@b.com",
      email_sent: false,
      dev_magic_url: "http://x/auth/confirm?token=tk",
      dev_otp_code: "123456",
      message: "ok",
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await requestMagicLink("a@b.com");
    expect(res.selector).toBe("sel-1");
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/py/auth/magic-link");
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ email: "a@b.com" });
  });

  it("verifyOtp chama /api/auth/login?step=otp e devolve o usuário (sem token)", async () => {
    const fetchMock = mockFetchOnce({
      user: { id: 1, email: "a@b.com", supabase_user_id: null, created_at: "x" },
      provider: "local",
    });
    vi.stubGlobal("fetch", fetchMock);

    const res = await verifyOtp("sel-1", "123456");
    expect(res.user.id).toBe(1);
    // o token nunca volta ao browser
    expect((res as Record<string, unknown>).access_token).toBeUndefined();
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/login?step=otp");
    expect(JSON.parse(options.body)).toEqual({ selector: "sel-1", code: "123456" });
  });

  it("checkLoginStatus chama /api/auth/login?step=poll com o selector no corpo", async () => {
    const fetchMock = mockFetchOnce({ status: "pending", provider: "local" });
    vi.stubGlobal("fetch", fetchMock);

    await checkLoginStatus("sel abc");
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/login?step=poll");
    expect(JSON.parse(options.body)).toEqual({ selector: "sel abc" });
  });

  it("listTasks chama o proxy SEM Authorization (cookie cuida disso no servidor)", async () => {
    const fetchMock = mockFetchOnce([
      { id: 1, titulo: "T", descricao: null, status: "pendente", data_criacao: "x", updated_at: "x" },
    ]);
    vi.stubGlobal("fetch", fetchMock);

    const tasks = await listTasks({ standalone: true });
    expect(tasks).toHaveLength(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/py/tasks?standalone=true");
    expect(options.headers.Authorization).toBeUndefined();
    expect(options.credentials).toBe("same-origin");
  });

  it("createTask faz POST no proxy com corpo", async () => {
    const fetchMock = mockFetchOnce({ id: 9, titulo: "Nova", descricao: null, status: "pendente", data_criacao: "x", updated_at: "x" });
    vi.stubGlobal("fetch", fetchMock);

    const t = await createTask({ titulo: "Nova" });
    expect(t.id).toBe(9);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/py/tasks");
    expect(options.method).toBe("POST");
  });

  it("deleteTask trata 204 sem corpo", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204, text: async () => "" });
    vi.stubGlobal("fetch", fetchMock);
    await expect(deleteTask(5)).resolves.toBeUndefined();
  });

  it("lança ApiError com detail em erro HTTP", async () => {
    const fetchMock = mockFetchOnce({ detail: "Tarefa não encontrada." }, 404);
    vi.stubGlobal("fetch", fetchMock);

    await expect(listTasks()).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "Tarefa não encontrada.",
    });
  });

  it("ApiError de rede quando fetch falha", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("network down"));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listTasks()).rejects.toBeInstanceOf(ApiError);
  });
});
