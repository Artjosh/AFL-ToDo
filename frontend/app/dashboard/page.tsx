/**
 * Dashboard estilo Trello/Jira (rota protegida).
 *
 * - Visão principal: board Kanban com as tarefas soltas; projetos aparecem como
 *   cards especiais na coluna "Pendente".
 * - Ao abrir um projeto, mostra o board daquele projeto (tarefas aninhadas) com
 *   gestão de membros.
 * - Drag-and-drop move a tarefa entre colunas (persistido via API).
 *
 * Os dados são sempre buscados/validados pelo backend Python.
 */
"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useAuth } from "@/components/auth-provider";
import Board from "@/components/board";
import MembersModal from "@/components/members-modal";
import ProjectCard from "@/components/project-card";
import QuickCreateModal from "@/components/quick-create-modal";
import TaskDetailModal from "@/components/task-detail-modal";
import { useToast } from "@/components/toast";
import * as api from "@/lib/api";
import { ApiError } from "@/lib/api";
import { connectBoard } from "@/lib/realtime";
import type {
  Project,
  ProjectDetail,
  Task,
  TaskStatus,
} from "@/lib/types";
import { STATUS_LABELS, STATUS_ORDER } from "@/lib/types";

export default function DashboardPage() {
  const { user, loading, logout } = useAuth();
  const toast = useToast();
  const router = useRouter();

  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [fetching, setFetching] = useState(true);

  // Projeto aberto (drill-down). null = visão principal.
  const [openProject, setOpenProject] = useState<ProjectDetail | null>(null);

  // Modais
  const [createKind, setCreateKind] = useState<"task" | "project" | null>(null);
  const [createStatus, setCreateStatus] = useState<TaskStatus>("pendente");
  const [detailTask, setDetailTask] = useState<Task | null>(null);
  const [savingTask, setSavingTask] = useState(false);
  const [membersOpen, setMembersOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  // Indicador discreto de sincronização (ex.: durante reorder otimista).
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  const handleApiError = useCallback(
    (err: unknown, fallback: string) => {
      if (err instanceof ApiError && err.status === 401) {
        toast.error("Sessão expirada. Faça login novamente.", { key: "session-expired" });
        void logout();
        return;
      }
      toast.error(err instanceof Error ? err.message : fallback, { key: "api-error" });
    },
    [toast, logout],
  );

  const loadMain = useCallback(
    async (opts?: { silent?: boolean }) => {
      // O spinner de tela cheia só aparece na carga inicial. Refreshes em
      // background (realtime/echo, pós-mutação) são silenciosos para não piscar
      // a tela toda — o indicador discreto "Sincronizando..." já dá o feedback.
      if (!opts?.silent) setFetching(true);
      try {
        const [t, p] = await Promise.all([
          api.listTasks({ standalone: true }),
          api.listProjects(),
        ]);
        setTasks(t);
        setProjects(p);
      } catch (err) {
        handleApiError(err, "Erro ao carregar.");
      } finally {
        if (!opts?.silent) setFetching(false);
      }
    },
    [handleApiError],
  );

  useEffect(() => {
    void loadMain();
  }, [loadMain]);

  // ---- Realtime: assina o board e recarrega ao vivo quando outro membro muda algo ----
  // Mantém sempre a função de reload "atual" numa ref, para o efeito do WS poder
  // depender só de [token, projectId] (conexão estável, sem reconectar a cada render).
  const reloadCurrentViewRef = useRef<() => void>(() => {});

  useEffect(() => {
    const projectId = openProject?.id ?? null;
    let debounce: ReturnType<typeof setTimeout> | null = null;
    const disconnect = connectBoard(projectId, () => {
      if (debounce) clearTimeout(debounce);
      debounce = setTimeout(() => reloadCurrentViewRef.current(), 250);
    });
    return () => {
      if (debounce) clearTimeout(debounce);
      disconnect();
    };
  }, [openProject?.id]);

  // ---- Projeto (drill-down) ----
  const openProjectView = useCallback(
    async (project: Project) => {
      try {
        const detail = await api.getProject(project.id);
        setOpenProject(detail);
      } catch (err) {
        handleApiError(err, "Erro ao abrir projeto.");
      }
    },
    [handleApiError],
  );

  const reloadProject = useCallback(async () => {
    if (!openProject) return;
    try {
      const detail = await api.getProject(openProject.id);
      setOpenProject(detail);
    } catch (err) {
      handleApiError(err, "Erro ao recarregar projeto.");
    }
  }, [openProject, handleApiError]);

  // mantém a ref usada pelo realtime apontando para o reload da view atual
  useEffect(() => {
    reloadCurrentViewRef.current = () => {
      // Reload de realtime é sempre silencioso (sem spinner de tela cheia).
      if (openProject) void reloadProject();
      else void loadMain({ silent: true });
    };
  }, [openProject, reloadProject, loadMain]);

  // ---- Reordenar / mover tarefa (drag-and-drop) ----
  const reorder = useCallback(
    async (status: TaskStatus, orderedIds: number[]) => {
      const inProject = openProject != null;
      // atualização otimista: aplica novo status + posições na coluna
      const apply = (list: Task[]) =>
        list.map((t) => {
          const idx = orderedIds.indexOf(t.id);
          if (idx >= 0) return { ...t, status, position: idx };
          return t;
        });
      if (inProject) {
        setOpenProject((p) => (p ? { ...p, tasks: apply(p.tasks) } : p));
      } else {
        setTasks(apply);
      }
      try {
        setSyncing(true);
        await api.reorderTasks(orderedIds, status);
      } catch (err) {
        handleApiError(err, "Erro ao reordenar tarefas.");
        if (inProject) void reloadProject();
        else void loadMain();
      } finally {
        setSyncing(false);
      }
    },
    [openProject, handleApiError, reloadProject, loadMain],
  );

  // ---- Criar ----
  const handleCreate = async (data: { titulo: string; descricao: string | null }) => {
    setSubmitting(true);
    try {
      if (createKind === "project") {
        await api.createProject({ nome: data.titulo, descricao: data.descricao });
        toast.success("Projeto criado.", { key: "project-created" });
        await loadMain({ silent: true });
      } else {
        await api.createTask({
          titulo: data.titulo,
          descricao: data.descricao,
          status: createStatus,
          project_id: openProject?.id ?? null,
        });
        toast.success("Tarefa criada.", { key: "task-created" });
        if (openProject) await reloadProject();
        else await loadMain({ silent: true });
      }
      setCreateKind(null);
    } catch (err) {
      handleApiError(err, "Erro ao criar.");
    } finally {
      setSubmitting(false);
    }
  };

  // ---- Editar tarefa ----
  const saveTask = async (changes: {
    titulo?: string;
    descricao?: string | null;
    status?: TaskStatus;
  }) => {
    if (!detailTask) return;
    setSavingTask(true);
    try {
      await api.updateTask(detailTask.id, changes);
      toast.success("Tarefa atualizada.", { key: "task-updated" });
      setDetailTask(null);
      if (openProject) await reloadProject();
      else await loadMain({ silent: true });
    } catch (err) {
      handleApiError(err, "Erro ao salvar tarefa.");
    } finally {
      setSavingTask(false);
    }
  };

  const deleteTask = async (task: Task) => {
    if (!window.confirm(`Excluir a tarefa "${task.titulo}"?`)) return;
    try {
      await api.deleteTask(task.id);
      toast.success("Tarefa excluída.", { key: "task-deleted" });
      setDetailTask(null);
      if (openProject) await reloadProject();
      else await loadMain({ silent: true });
    } catch (err) {
      handleApiError(err, "Erro ao excluir tarefa.");
    }
  };

  // ---- Assignees ----
  const addAssignee = async (email: string) => {
    if (!detailTask) return;
    try {
      const updated = await api.addAssignee(detailTask.id, email);
      setDetailTask(updated);
      toast.success("Pessoa atribuída.", { key: "assignee-added" });
      if (openProject) await reloadProject();
      else await loadMain({ silent: true });
    } catch (err) {
      handleApiError(err, "Erro ao atribuir pessoa.");
    }
  };

  const removeAssignee = async (userId: number) => {
    if (!detailTask) return;
    try {
      const updated = await api.removeAssignee(detailTask.id, userId);
      setDetailTask(updated);
      if (openProject) await reloadProject();
      else await loadMain({ silent: true });
    } catch (err) {
      handleApiError(err, "Erro ao remover atribuição.");
    }
  };

  // ---- Membros do projeto ----
  const addMember = async (email: string) => {
    if (!openProject) return;
    try {
      await api.addMember(openProject.id, email);
      toast.success("Membro adicionado.", { key: "member-added" });
      await reloadProject();
    } catch (err) {
      handleApiError(err, "Erro ao adicionar membro.");
    }
  };

  const removeMember = async (userId: number) => {
    if (!openProject) return;
    try {
      await api.removeMember(openProject.id, userId);
      toast.success("Membro removido.", { key: "member-removed" });
      await reloadProject();
    } catch (err) {
      handleApiError(err, "Erro ao remover membro.");
    }
  };

  const updateMemberPermissions = async (
    userId: number,
    perms: Partial<{
      can_move_project: boolean;
      can_move_tasks: boolean;
      can_manage_tasks: boolean;
      receives_alerts: boolean;
    }>,
  ) => {
    if (!openProject) return;
    try {
      await api.updateMemberPermissions(openProject.id, userId, perms);
      await reloadProject();
    } catch (err) {
      handleApiError(err, "Erro ao atualizar permissões.");
    }
  };

  const updateProjectSettings = async (
    changes: Partial<{
      removed_member_policy: "revoke" | "keep";
      owner_receives_alerts: boolean;
    }>,
  ) => {
    if (!openProject) return;
    try {
      await api.updateProject(openProject.id, changes);
      toast.success("Configuração salva.", { key: "project-settings" });
      await reloadProject();
    } catch (err) {
      handleApiError(err, "Erro ao salvar configuração.");
    }
  };

  const moveProjectStatus = async (status: TaskStatus) => {
    if (!openProject) return;
    try {
      await api.updateProject(openProject.id, { status });
      toast.success("Status do projeto atualizado.", { key: "project-status" });
      await reloadProject();
      await loadMain({ silent: true });
    } catch (err) {
      handleApiError(err, "Erro ao mover o projeto.");
    }
  };

  // Move um projeto (card no board principal) para outra coluna de status.
  const moveProjectStatusById = async (projectId: number, status: TaskStatus) => {
    const target = projects.find((p) => p.id === projectId);
    if (!target || target.status === status) return;
    // atualização otimista: reposiciona o card na coluna nova
    setProjects((prev) =>
      prev.map((p) => (p.id === projectId ? { ...p, status } : p)),
    );
    try {
      setSyncing(true);
      await api.updateProject(projectId, { status });
    } catch (err) {
      handleApiError(err, "Erro ao mover o projeto.");
      await loadMain({ silent: true });
    } finally {
      setSyncing(false);
    }
  };

  const deleteProject = async () => {
    if (!openProject) return;
    if (!window.confirm(`Excluir o projeto "${openProject.nome}" e suas tarefas?`)) return;
    try {
      await api.deleteProject(openProject.id);
      toast.success("Projeto excluído.", { key: "project-deleted" });
      setOpenProject(null);
      await loadMain({ silent: true });
    } catch (err) {
      handleApiError(err, "Erro ao excluir projeto.");
    }
  };

  if (loading || !user) {
    return (
      <div className="flex min-h-[40vh] items-center justify-center text-muted">
        Carregando...
      </div>
    );
  }

  // ----------------- VISÃO DE PROJETO (drill-down) -----------------
  if (openProject) {
    const isOwner = openProject.role === "owner";
    const canManageTasks = openProject.can_manage_tasks;
    const canMoveProject = openProject.can_move_project;
    return (
      <div>
        <div className="mb-5">
          <button
            type="button"
            onClick={() => setOpenProject(null)}
            className="mb-3 text-sm text-accent-soft hover:underline"
          >
            ← Voltar
          </button>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h1 className="flex items-center gap-2 text-2xl font-bold text-foreground">
                📁 {openProject.nome}
              </h1>
              {openProject.descricao && (
                <p className="text-sm text-muted">{openProject.descricao}</p>
              )}
              <div className="mt-2 flex items-center gap-2">
                <span className="text-xs text-muted">Status do projeto:</span>
                {canMoveProject ? (
                  <select
                    className="rounded-md border border-border bg-surface-2 px-2 py-1 text-xs font-semibold text-foreground"
                    value={openProject.status}
                    onChange={(e) => moveProjectStatus(e.target.value as TaskStatus)}
                    aria-label="Status do projeto"
                    data-testid="project-status-select"
                  >
                    {STATUS_ORDER.map((s) => (
                      <option key={s} value={s}>
                        {STATUS_LABELS[s]}
                      </option>
                    ))}
                  </select>
                ) : (
                  <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-semibold text-accent-soft">
                    {STATUS_LABELS[openProject.status]}
                  </span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {canManageTasks && (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => {
                    setCreateStatus("pendente");
                    setCreateKind("task");
                  }}
                >
                  + Nova tarefa
                </button>
              )}
              <button type="button" className="btn-ghost" onClick={() => setMembersOpen(true)}>
                Membros ({openProject.members.length})
              </button>
              {isOwner && (
                <button
                  type="button"
                  onClick={deleteProject}
                  className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm font-semibold text-danger transition-colors hover:bg-danger/20"
                >
                  Excluir projeto
                </button>
              )}
            </div>
          </div>
        </div>

        <Board
          tasks={openProject.tasks}
          onReorder={openProject.can_move_tasks ? reorder : undefined}
          onOpenTask={setDetailTask}
          onAddTask={
            canManageTasks
              ? (status) => {
                  setCreateStatus(status);
                  setCreateKind("task");
                }
              : undefined
          }
        />

        {renderModals()}

        <MembersModal
          open={membersOpen}
          project={openProject}
          canManage={isOwner}
          onClose={() => setMembersOpen(false)}
          onAdd={addMember}
          onRemove={removeMember}
          onUpdatePermissions={updateMemberPermissions}
          onUpdateProject={updateProjectSettings}
        />
      </div>
    );
  }

  // ----------------- VISÃO PRINCIPAL -----------------
  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Meu quadro</h1>
          <p className="text-sm text-muted">
            Arraste tarefas entre as colunas. Projetos agrupam tarefas e podem ser
            compartilhados.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {syncing && (
            <span className="flex items-center gap-1.5 text-xs text-muted" data-testid="syncing">
              <span className="h-2 w-2 animate-ping rounded-full bg-accent-soft" />
              Sincronizando...
            </span>
          )}
          <button
            type="button"
            className="btn-ghost"
            onClick={() => setCreateKind("project")}
          >
            + Novo projeto
          </button>
          <button
            type="button"
            className="btn-primary"
            onClick={() => {
              setCreateStatus("pendente");
              setCreateKind("task");
            }}
          >
            + Nova tarefa
          </button>
        </div>
      </div>

      {fetching ? (
        <div className="flex min-h-[30vh] items-center justify-center text-muted">
          Carregando...
        </div>
      ) : (
        <Board
          tasks={tasks}
          onReorder={reorder}
          onOpenTask={setDetailTask}
          onMoveProject={moveProjectStatusById}
          onAddTask={(status) => {
            setCreateStatus(status);
            setCreateKind("task");
          }}
          renderExtra={(status) => {
            const projectsHere = projects.filter((p) => p.status === status);
            if (projectsHere.length === 0) return null;
            return (
              <div className="mb-1 flex flex-col gap-2">
                {projectsHere.map((p) => (
                  <ProjectCard
                    key={p.id}
                    project={p}
                    onOpen={openProjectView}
                    draggable={p.can_move_project}
                  />
                ))}
              </div>
            );
          }}
        />
      )}

      {renderModals()}
    </div>
  );

  function renderModals() {
    return (
      <>
        <QuickCreateModal
          open={createKind !== null}
          kind={createKind ?? "task"}
          submitting={submitting}
          onClose={() => setCreateKind(null)}
          onSubmit={handleCreate}
        />
        <TaskDetailModal
          open={detailTask !== null}
          task={detailTask}
          saving={savingTask}
          onClose={() => setDetailTask(null)}
          onSave={saveTask}
          onDelete={deleteTask}
          onAddAssignee={addAssignee}
          onRemoveAssignee={removeAssignee}
        />
      </>
    );
  }
}

