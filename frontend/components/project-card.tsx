/**
 * Card de projeto exibido no board principal (na coluna do seu status).
 * Clicar expande o board do projeto (tarefas aninhadas). Pode ser arrastado
 * entre colunas para mudar o status do PRÓPRIO projeto, quando permitido.
 */
"use client";

import Avatar from "@/components/avatar";
import { STATUS_LABELS, type Project } from "@/lib/types";

export default function ProjectCard({
  project,
  onOpen,
  draggable = false,
  onDragStart,
  onDragEnd,
}: {
  project: Project;
  onOpen: (project: Project) => void;
  /** Habilita arrastar para mudar o status do projeto (permissão can_move_project). */
  draggable?: boolean;
  onDragStart?: (project: Project) => void;
  onDragEnd?: () => void;
}) {
  return (
    <div
      draggable={draggable}
      onDragStart={(e) => {
        // Marca o tipo "projeto" para o board distinguir de um drag de tarefa.
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("application/x-project", String(project.id));
        onDragStart?.(project);
      }}
      onDragEnd={() => onDragEnd?.()}
      onClick={() => onOpen(project)}
      data-testid={`project-${project.id}`}
      className={`w-full rounded-lg border border-accent/40 bg-accent/10 p-3 text-left transition-all hover:border-accent hover:bg-accent/15 ${
        draggable ? "cursor-grab active:cursor-grabbing" : "cursor-pointer"
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-md bg-accent/25 text-sm">
          📁
        </span>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-bold text-foreground">{project.nome}</p>
          <p className="text-[11px] text-accent-soft">
            Projeto · {project.task_count} tarefa{project.task_count === 1 ? "" : "s"}
          </p>
        </div>
      </div>

      {project.descricao && (
        <p className="mt-1.5 line-clamp-1 text-xs text-muted">{project.descricao}</p>
      )}

      <div className="mt-2 flex items-center justify-between">
        <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-muted">
          {project.role === "owner" ? "Dono" : "Membro"} · {STATUS_LABELS[project.status]}
        </span>
        <div className="flex -space-x-1.5">
          {project.members.slice(0, 4).map((m) => (
            <Avatar key={m.id} email={m.email} size={22} />
          ))}
          {project.members.length > 4 && (
            <span className="inline-flex h-[22px] w-[22px] items-center justify-center rounded-full bg-border text-[9px] font-bold text-muted ring-2 ring-surface">
              +{project.members.length - 4}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
