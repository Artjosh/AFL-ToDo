/**
 * Modal de detalhe/edição de tarefa (estilo Jira): título, descrição, status,
 * atribuídos (adicionar/remover pessoas por email) e exclusão.
 */
"use client";

import { useEffect, useState } from "react";

import Avatar from "@/components/avatar";
import { useToast } from "@/components/toast";
import {
  STATUS_LABELS,
  type Task,
  type TaskStatus,
} from "@/lib/types";

interface TaskDetailModalProps {
  task: Task | null;
  open: boolean;
  saving?: boolean;
  onClose: () => void;
  onSave: (changes: { titulo?: string; descricao?: string | null; status?: TaskStatus }) => void;
  onDelete: (task: Task) => void;
  onAddAssignee: (email: string) => Promise<void>;
  onRemoveAssignee: (userId: number) => Promise<void>;
}

export default function TaskDetailModal({
  task,
  open,
  saving,
  onClose,
  onSave,
  onDelete,
  onAddAssignee,
  onRemoveAssignee,
}: TaskDetailModalProps) {
  const toast = useToast();
  const [titulo, setTitulo] = useState("");
  const [descricao, setDescricao] = useState("");
  const [status, setStatus] = useState<TaskStatus>("pendente");
  const [assigneeEmail, setAssigneeEmail] = useState("");
  const [addingAssignee, setAddingAssignee] = useState(false);

  useEffect(() => {
    if (open && task) {
      setTitulo(task.titulo);
      setDescricao(task.descricao ?? "");
      setStatus(task.status);
      setAssigneeEmail("");
    }
  }, [open, task]);

  if (!open || !task) return null;

  const handleSave = () => {
    if (!titulo.trim()) {
      toast.error("O título é obrigatório.", { key: "task-title-required" });
      return;
    }
    onSave({
      titulo: titulo.trim(),
      descricao: descricao.trim() || null,
      status,
    });
  };

  const handleAddAssignee = async (e: React.FormEvent) => {
    e.preventDefault();
    const email = assigneeEmail.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      toast.error("Informe um email válido.", { key: "assignee-invalid" });
      return;
    }
    setAddingAssignee(true);
    try {
      await onAddAssignee(email);
      setAssigneeEmail("");
    } finally {
      setAddingAssignee(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-border bg-surface p-6 shadow-[0_20px_60px_rgba(0,0,0,0.6)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted">
            Tarefa #{task.id}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="text-muted transition-colors hover:text-foreground"
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>

        <div className="space-y-4">
          <div>
            <label htmlFor="detail-titulo" className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-muted">
              Título
            </label>
            <input
              id="detail-titulo"
              className="input-base"
              value={titulo}
              maxLength={255}
              onChange={(e) => setTitulo(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor="detail-descricao" className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-muted">
              Descrição
            </label>
            <textarea
              id="detail-descricao"
              className="input-base min-h-[100px] resize-y"
              value={descricao}
              maxLength={5000}
              onChange={(e) => setDescricao(e.target.value)}
            />
          </div>

          <div>
            <label htmlFor="detail-status" className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-muted">
              Status
            </label>
            <select
              id="detail-status"
              className="input-base"
              value={status}
              onChange={(e) => setStatus(e.target.value as TaskStatus)}
            >
              {(Object.keys(STATUS_LABELS) as TaskStatus[]).map((s) => (
                <option key={s} value={s}>
                  {STATUS_LABELS[s]}
                </option>
              ))}
            </select>
          </div>

          {/* Criador + atribuídos */}
          <div>
            <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-muted">
              Pessoas
            </label>
            <div className="mb-2 flex flex-wrap gap-2">
              {/* Criador (sempre presente) */}
              <span
                className="inline-flex items-center gap-1.5 rounded-full border border-accent/50 bg-accent/10 py-0.5 pl-0.5 pr-2 text-xs"
                title={`${task.creator.email} (criador)`}
              >
                <span className="rounded-full ring-2 ring-accent">
                  <Avatar email={task.creator.email} size={20} />
                </span>
                <span className="text-foreground">{task.creator.email}</span>
                <span className="text-[10px] uppercase tracking-wider text-accent-soft">
                  criador
                </span>
              </span>
              {/* Atribuídos (sem repetir o criador) */}
              {task.assignees
                .filter((a) => a.id !== task.creator.id)
                .map((a) => (
                  <span
                    key={a.id}
                    className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface-2 py-0.5 pl-0.5 pr-2 text-xs"
                  >
                    <Avatar email={a.email} size={20} />
                    <span className="text-foreground">{a.email}</span>
                    <button
                      type="button"
                      onClick={() => onRemoveAssignee(a.id)}
                      className="text-muted hover:text-danger"
                      aria-label={`Remover ${a.email}`}
                    >
                      ✕
                    </button>
                  </span>
                ))}
            </div>
            <form onSubmit={handleAddAssignee} className="flex gap-2">
              <input
                className="input-base flex-1"
                placeholder="email@pessoa.com"
                value={assigneeEmail}
                onChange={(e) => setAssigneeEmail(e.target.value)}
              />
              <button type="submit" className="btn-ghost" disabled={addingAssignee}>
                {addingAssignee ? "..." : "Atribuir"}
              </button>
            </form>
            <p className="mt-1.5 text-[11px] text-muted">
              Atribuir dá acesso à tarefa para a pessoa — funciona inclusive em
              tarefas fora de um projeto.
            </p>
          </div>

          <div className="flex items-center justify-between border-t border-border pt-4">
            <button
              type="button"
              onClick={() => onDelete(task)}
              className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-xs font-semibold text-danger transition-colors hover:bg-danger/20"
            >
              Excluir tarefa
            </button>
            <div className="flex gap-2">
              <button type="button" onClick={onClose} className="btn-ghost">
                Cancelar
              </button>
              <button type="button" onClick={handleSave} className="btn-primary" disabled={saving}>
                {saving ? "Salvando..." : "Salvar"}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
