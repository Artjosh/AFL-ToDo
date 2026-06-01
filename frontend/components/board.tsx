/**
 * Board Kanban reutilizável (estilo Trello/Jira).
 *
 * Renderiza 3 colunas (Pendente / Em andamento / Concluída) com drag-and-drop
 * nativo. Suporta:
 * - mover card entre colunas (muda o status);
 * - reordenar cards dentro/entre colunas (soltar sobre outro card define a posição).
 *
 * A persistência é delegada via onReorder(status, orderedIds) para o pai, que
 * chama a API (/tasks/reorder). É usado na lista principal e dentro de projetos.
 */
"use client";

import { useState } from "react";

import BoardCard from "@/components/board-card";
import { STATUS_LABELS, STATUS_ORDER, type Task, type TaskStatus } from "@/lib/types";

interface BoardProps {
  tasks: Task[];
  /** Persiste a nova ordem de uma coluna. Ausente = drag-and-drop desabilitado. */
  onReorder?: (status: TaskStatus, orderedIds: number[]) => void;
  onOpenTask: (task: Task) => void;
  /** Adiciona tarefa numa coluna. Ausente = botão "+" oculto (sem permissão). */
  onAddTask?: (status: TaskStatus) => void;
  /** Move um PROJETO (card) para outra coluna de status. */
  onMoveProject?: (projectId: number, status: TaskStatus) => void;
  /** Cards extras (ex.: projetos) renderizados no topo de cada coluna por status. */
  renderExtra?: (status: TaskStatus) => React.ReactNode;
}

const COLUMN_ACCENT: Record<TaskStatus, string> = {
  pendente: "border-t-warning",
  em_andamento: "border-t-accent",
  concluida: "border-t-success",
};

export default function Board({
  tasks,
  onReorder,
  onOpenTask,
  onAddTask,
  onMoveProject,
  renderExtra,
}: BoardProps) {
  const canDrag = typeof onReorder === "function";
  const [draggingId, setDraggingId] = useState<number | null>(null);
  const [overColumn, setOverColumn] = useState<TaskStatus | null>(null);

  // Permite reagir a drops (tarefa ou projeto) na coluna.
  const anyDrop = canDrag || typeof onMoveProject === "function";

  /** Extrai o id do projeto sendo arrastado, se o drag for de um projeto. */
  const projectIdFromDrag = (e: React.DragEvent): number | null => {
    const raw = e.dataTransfer.getData("application/x-project");
    if (!raw) return null;
    const id = Number(raw);
    return Number.isNaN(id) ? null : id;
  };

  const columnTasksOf = (status: TaskStatus) =>
    tasks.filter((t) => t.status === status).sort((a, b) => a.position - b.position);

  /**
   * Calcula a nova ordem de ids ao soltar o card arrastado na coluna `status`,
   * opcionalmente antes do card `beforeId` (null = no fim da coluna).
   */
  const computeOrder = (
    status: TaskStatus,
    beforeId: number | null,
  ): { status: TaskStatus; ids: number[] } | null => {
    if (draggingId == null) return null;
    const dragged = tasks.find((t) => t.id === draggingId);
    if (!dragged) return null;

    const target = columnTasksOf(status)
      .filter((t) => t.id !== draggingId)
      .map((t) => t.id);

    let insertAt = target.length;
    if (beforeId != null) {
      const idx = target.indexOf(beforeId);
      if (idx >= 0) insertAt = idx;
    }
    target.splice(insertAt, 0, draggingId);

    // Sem mudança real? evita request desnecessário.
    const current = columnTasksOf(status).map((t) => t.id);
    if (
      dragged.status === status &&
      current.length === target.length &&
      current.every((id, i) => id === target[i])
    ) {
      return null;
    }
    return { status, ids: target };
  };

  const dropOnColumn = (status: TaskStatus) => {
    const result = computeOrder(status, null);
    setOverColumn(null);
    setDraggingId(null);
    if (result && onReorder) onReorder(result.status, result.ids);
  };

  const dropOnCard = (status: TaskStatus, beforeId: number) => {
    const result = computeOrder(status, beforeId);
    setOverColumn(null);
    setDraggingId(null);
    if (result && onReorder) onReorder(result.status, result.ids);
  };

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
      {STATUS_ORDER.map((status) => {
        const columnTasks = columnTasksOf(status);

        return (
          <div
            key={status}
            onDragOver={(e) => {
              if (!anyDrop) return;
              e.preventDefault();
              setOverColumn(status);
            }}
            onDragLeave={() => setOverColumn((c) => (c === status ? null : c))}
            onDrop={(e) => {
              if (!anyDrop) return;
              e.preventDefault();
              // Drop de PROJETO: muda o status do projeto.
              const projectId = projectIdFromDrag(e);
              if (projectId != null) {
                setOverColumn(null);
                setDraggingId(null);
                onMoveProject?.(projectId, status);
                return;
              }
              if (canDrag) dropOnColumn(status);
            }}
            data-testid={`column-${status}`}
            className={`flex min-h-[200px] flex-col rounded-xl border border-t-4 border-border ${COLUMN_ACCENT[status]} bg-surface/60 p-3 transition-colors ${
              overColumn === status ? "bg-accent/5 ring-1 ring-accent/40" : ""
            }`}
          >
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-bold text-foreground">
                {STATUS_LABELS[status]}
                <span className="ml-2 rounded-full bg-surface-2 px-2 py-0.5 text-[11px] font-semibold text-muted">
                  {columnTasks.length}
                </span>
              </h3>
              {onAddTask && (
                <button
                  type="button"
                  onClick={() => onAddTask(status)}
                  title="Adicionar tarefa"
                  className="flex h-6 w-6 items-center justify-center rounded text-muted transition-colors hover:bg-surface-2 hover:text-foreground"
                >
                  +
                </button>
              )}
            </div>

            <div className="flex flex-1 flex-col gap-2">
              {renderExtra?.(status)}
              {columnTasks.map((task) => (
                <div
                  key={task.id}
                  onDragOver={(e) => {
                    if (canDrag && draggingId != null && draggingId !== task.id) {
                      e.preventDefault();
                      e.stopPropagation();
                    }
                  }}
                  onDrop={(e) => {
                    if (!anyDrop) return;
                    // Se for um projeto sendo solto sobre um card, deixa a coluna tratar.
                    if (projectIdFromDrag(e) != null) return;
                    if (!canDrag) return;
                    e.preventDefault();
                    e.stopPropagation();
                    dropOnCard(status, task.id);
                  }}
                >
                  <BoardCard
                    task={task}
                    draggable={canDrag}
                    onDragStart={canDrag ? (t) => setDraggingId(t.id) : undefined}
                    onDragEnd={canDrag ? () => setDraggingId(null) : undefined}
                    onClick={onOpenTask}
                  />
                </div>
              ))}
              {columnTasks.length === 0 && !renderExtra && (
                <p className="rounded-lg border border-dashed border-border/60 p-4 text-center text-xs text-muted">
                  Arraste tarefas para cá
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
