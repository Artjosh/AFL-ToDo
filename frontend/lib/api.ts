/**
 * Cliente da API — padrão BFF (Backend-for-Frontend).
 *
 * O browser NÃO fala diretamente com o FastAPI e NÃO guarda o token de sessão.
 * Em vez disso, chama rotas same-origin do próprio Next:
 *
 * - /api/py/*           -> proxy que injeta o token (do cookie httpOnly) e
 *                          repassa ao backend Python (fonte de verdade).
 * - /api/auth/login     -> finaliza o login (OTP/polling) e grava o cookie de
 *                          sessão no servidor; devolve só o usuário.
 * - /api/auth/session   -> restaura (GET) ou encerra (DELETE) a sessão.
 *
 * Como o token vive apenas num cookie httpOnly, ele nunca é exposto ao
 * JavaScript do browser. O backend continua validando o token a cada chamada.
 */
import type {
  LoginStatusResponse,
  MagicLinkResponse,
  Member,
  Project,
  ProjectDetail,
  ProjectInput,
  Task,
  TaskInput,
  User,
} from "./types";

/** Base do proxy same-origin para o backend Python. */
const PY = "/api/py";

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const { headers, ...rest } = options;
  const finalHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    ...(headers as Record<string, string>),
  };

  let response: Response;
  try {
    response = await fetch(path, {
      ...rest,
      headers: finalHeaders,
      credentials: "same-origin",
    });
  } catch {
    throw new ApiError(
      "Não foi possível conectar à API. Verifique se o backend está rodando.",
      0,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  let data: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!response.ok) {
    const detail =
      (data as { detail?: string })?.detail ||
      (typeof data === "string" ? data : "Erro na requisição.");
    throw new ApiError(detail, response.status);
  }

  return data as T;
}

// ---- Auth passwordless ----

/** Solicita o magic link + OTP para um email (público, via proxy). */
export function requestMagicLink(email: string) {
  return request<MagicLinkResponse>(`${PY}/auth/magic-link`, {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

/** Cria um pedido de login Supabase no backend (para polling cross-device). */
export function supabaseStart(email: string) {
  return request<MagicLinkResponse>(`${PY}/auth/supabase/start`, {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

/**
 * Verifica o OTP local. Em sucesso o servidor grava o cookie de sessão e
 * devolve apenas o usuário (o token nunca volta ao browser).
 */
export function verifyOtp(selector: string, code: string) {
  return request<{ user: User; provider: string }>(`/api/auth/login?step=otp`, {
    method: "POST",
    body: JSON.stringify({ selector, code }),
  });
}

/**
 * Polling: pergunta ao servidor se o login foi aprovado. Quando aprovado, o
 * servidor grava o cookie de sessão e devolve o usuário.
 */
export function checkLoginStatus(selector: string) {
  return request<{ status: string; user?: User; provider?: string }>(
    `/api/auth/login?step=poll`,
    { method: "POST", body: JSON.stringify({ selector }) },
  );
}

/**
 * Estabelece a sessão a partir de um token externo (modo Supabase): o servidor
 * valida o token, espelha o usuário e grava o cookie httpOnly.
 */
export function establishSession(token: string, provider: "local" | "supabase") {
  return request<{ user: User; provider: string }>(`/api/auth/session`, {
    method: "POST",
    body: JSON.stringify({ token, provider }),
  });
}

/** Restaura a sessão atual a partir do cookie httpOnly. */
export function getSession() {
  return request<{ user: User; provider: string }>(`/api/auth/session`, {
    method: "GET",
  });
}

/** Encerra a sessão (limpa o cookie httpOnly). */
export function clearSession() {
  return request<{ ok: boolean }>(`/api/auth/session`, { method: "DELETE" });
}

/** Pede um ticket efêmero para abrir o WebSocket do board. */
export function requestWsTicket() {
  return request<{ ticket: string }>(`/api/auth/ws-ticket`, { method: "POST" });
}

// Mantido por compatibilidade de tipos; o "me" agora vem de getSession().
export function getMe() {
  return getSession().then((s) => s.user);
}

// Mantido por compatibilidade de assinatura do contexto (não usado no BFF).
export type { LoginStatusResponse };

// ---- Tarefas (autenticadas via cookie no proxy) ----

export function listTasks(
  opts: { projectId?: number; standalone?: boolean } = {},
) {
  const params = new URLSearchParams();
  if (opts.projectId != null) params.set("project_id", String(opts.projectId));
  if (opts.standalone) params.set("standalone", "true");
  const qs = params.toString();
  return request<Task[]>(`${PY}/tasks${qs ? `?${qs}` : ""}`);
}

export function createTask(input: TaskInput) {
  return request<Task>(`${PY}/tasks`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateTask(id: number, input: Partial<TaskInput>) {
  return request<Task>(`${PY}/tasks/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteTask(id: number) {
  return request<void>(`${PY}/tasks/${id}`, { method: "DELETE" });
}

/** Reordena (e opcionalmente move de coluna) uma lista de tarefas pelo id. */
export function reorderTasks(taskIds: number[], status?: string) {
  return request<Task[]>(`${PY}/tasks/reorder`, {
    method: "POST",
    body: JSON.stringify({ task_ids: taskIds, status: status ?? null }),
  });
}

export function addAssignee(taskId: number, email: string) {
  return request<Task>(`${PY}/tasks/${taskId}/assignees`, {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function removeAssignee(taskId: number, userId: number) {
  return request<Task>(`${PY}/tasks/${taskId}/assignees/${userId}`, {
    method: "DELETE",
  });
}

// ---- Projetos e membros ----

export function listProjects() {
  return request<Project[]>(`${PY}/projects`);
}

export function getProject(id: number) {
  return request<ProjectDetail>(`${PY}/projects/${id}`);
}

export function createProject(input: ProjectInput) {
  return request<Project>(`${PY}/projects`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateProject(id: number, input: Partial<ProjectInput> & {
  status?: string;
  removed_member_policy?: "revoke" | "keep";
  owner_receives_alerts?: boolean;
}) {
  return request<Project>(`${PY}/projects/${id}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteProject(id: number) {
  return request<void>(`${PY}/projects/${id}`, { method: "DELETE" });
}

export function addMember(projectId: number, email: string) {
  return request<Project>(`${PY}/projects/${projectId}/members`, {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export function updateMemberPermissions(
  projectId: number,
  userId: number,
  perms: Partial<{
    can_move_project: boolean;
    can_move_tasks: boolean;
    can_manage_tasks: boolean;
    receives_alerts: boolean;
  }>,
) {
  return request<Project>(`${PY}/projects/${projectId}/members/${userId}`, {
    method: "PATCH",
    body: JSON.stringify(perms),
  });
}

export function removeMember(projectId: number, userId: number) {
  return request<Project>(`${PY}/projects/${projectId}/members/${userId}`, {
    method: "DELETE",
  });
}

export type { Member };
