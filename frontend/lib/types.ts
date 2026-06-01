// Tipos compartilhados do frontend.

export type TaskStatus = "pendente" | "em_andamento" | "concluida";

export interface UserBrief {
  id: number;
  email: string;
}

export interface Task {
  id: number;
  titulo: string;
  descricao: string | null;
  status: TaskStatus;
  position: number;
  project_id: number | null;
  data_criacao: string;
  updated_at: string;
  creator: UserBrief;
  assignees: UserBrief[];
}

export interface Member {
  id: number;
  email: string;
  role: "owner" | "member";
  can_move_project: boolean;
  can_move_tasks: boolean;
  can_manage_tasks: boolean;
  receives_alerts: boolean;
}

export type RemovedMemberPolicy = "revoke" | "keep";

export interface Project {
  id: number;
  nome: string;
  descricao: string | null;
  owner_id: number;
  status: TaskStatus;
  position: number;
  removed_member_policy: RemovedMemberPolicy;
  owner_receives_alerts: boolean;
  data_criacao: string;
  updated_at: string;
  role: "owner" | "member";
  can_move_project: boolean;
  can_move_tasks: boolean;
  can_manage_tasks: boolean;
  task_count: number;
  members: Member[];
}

export interface ProjectDetail extends Project {
  tasks: Task[];
}

export interface User {
  id: number;
  email: string;
  supabase_user_id: string | null;
  created_at: string;
}

// Modo de autenticação selecionado no topo do site.
export type AuthMode = "local" | "supabase";

export interface TaskInput {
  titulo: string;
  descricao?: string | null;
  status?: TaskStatus;
  position?: number;
  project_id?: number | null;
  clear_project?: boolean;
}

export interface ProjectInput {
  nome: string;
  descricao?: string | null;
}

// ---- Auth passwordless (magic link + OTP) ----

export interface MagicLinkResponse {
  selector: string;
  email: string;
  email_sent: boolean;
  dev_magic_url: string | null;
  dev_otp_code: string | null;
  message: string;
}

export interface LoginStatusResponse {
  status: "pending" | "approved";
  authenticated: boolean;
  provider: "local" | "supabase";
  access_token: string | null;
  refresh_token: string | null;
  user: User | null;
}

export const STATUS_LABELS: Record<TaskStatus, string> = {
  pendente: "Pendente",
  em_andamento: "Em andamento",
  concluida: "Concluída",
};

export const STATUS_ORDER: TaskStatus[] = ["pendente", "em_andamento", "concluida"];
