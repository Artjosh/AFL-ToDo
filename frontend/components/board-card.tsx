/**
 * Card de tarefa no board Kanban (estilo Trello/Jira).
 *
 * Mostra sempre o **criador** (com anel de destaque) e os **atribuídos**, de forma
 * consistente em qualquer tarefa — solta ou dentro de projeto. Assim você sempre
 * vê sua miniatura nas suas tarefas, e as pessoas atribuídas aparecem ao lado.
 */
"use client";

import Avatar from "@/components/avatar";
import type { Task, UserBrief } from "@/lib/types";

interface BoardCardProps {
  task: Task;
  draggable?: boolean;
  onDragStart?: (task: Task) => void;
  onDragEnd?: () => void;
  onClick?: (task: Task) => void;
}

const MAX_AVATARS = 4;

export default function BoardCard({
  task,
  draggable = true,
  onDragStart,
  onDragEnd,
  onClick,
}: BoardCardProps) {
  // Criador primeiro; depois atribuídos (sem repetir o criador).
  const people: { user: UserBrief; isCreator: boolean }[] = [
    { user: task.creator, isCreator: true },
    ...task.assignees
      .filter((a) => a.id !== task.creator.id)
      .map((a) => ({ user: a, isCreator: false })),
  ];
  const visible = people.slice(0, MAX_AVATARS);
  const overflow = people.length - visible.length;

  return (
    <div
      draggable={draggable}
      onDragStart={(e) => {
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", String(task.id));
        onDragStart?.(task);
      }}
      onDragEnd={() => onDragEnd?.()}
      onClick={() => onClick?.(task)}
      data-testid={`card-${task.id}`}
      className="group cursor-pointer rounded-lg border border-border bg-surface-2 p-3 shadow-sm transition-all hover:border-accent/50 hover:shadow-md"
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium leading-snug text-foreground">
          {task.titulo}
        </p>
      </div>

      {task.descricao && (
        <p className="mt-1 line-clamp-2 text-xs text-muted">{task.descricao}</p>
      )}

      <div className="mt-3 flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-muted">
          #{task.id}
        </span>
        <div className="flex -space-x-1.5">
          {visible.map(({ user, isCreator }) => (
            <span
              key={user.id}
              className={isCreator ? "rounded-full ring-2 ring-accent" : ""}
              title={isCreator ? `${user.email} (criador)` : user.email}
            >
              <Avatar email={user.email} size={22} />
            </span>
          ))}
          {overflow > 0 && (
            <span className="inline-flex h-[22px] w-[22px] items-center justify-center rounded-full bg-border text-[9px] font-bold text-muted ring-2 ring-surface">
              +{overflow}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
