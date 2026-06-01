/**
 * Modal compacto para criar tarefa OU projeto rapidamente.
 */
"use client";

import { useEffect, useState } from "react";

import { useToast } from "@/components/toast";

interface QuickCreateModalProps {
  open: boolean;
  kind: "task" | "project";
  submitting?: boolean;
  onClose: () => void;
  onSubmit: (data: { titulo: string; descricao: string | null }) => void;
}

export default function QuickCreateModal({
  open,
  kind,
  submitting,
  onClose,
  onSubmit,
}: QuickCreateModalProps) {
  const toast = useToast();
  const [titulo, setTitulo] = useState("");
  const [descricao, setDescricao] = useState("");

  useEffect(() => {
    if (open) {
      setTitulo("");
      setDescricao("");
    }
  }, [open]);

  if (!open) return null;

  const isProject = kind === "project";
  const label = isProject ? "projeto" : "tarefa";

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!titulo.trim()) {
      toast.error(`Informe o nome ${isProject ? "do projeto" : "da tarefa"}.`, {
        key: "quick-create-required",
      });
      return;
    }
    onSubmit({ titulo: titulo.trim(), descricao: descricao.trim() || null });
  };

  return (
    <div
      className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-2xl border border-border bg-surface p-6 shadow-[0_20px_60px_rgba(0,0,0,0.6)]"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="mb-4 text-lg font-bold text-foreground">
          {isProject ? "Novo projeto" : "Nova tarefa"}
        </h2>

        <div className="space-y-3">
          <input
            className="input-base"
            placeholder={isProject ? "Nome do projeto" : "Título da tarefa"}
            value={titulo}
            maxLength={255}
            onChange={(e) => setTitulo(e.target.value)}
            autoFocus
            aria-label={isProject ? "Nome do projeto" : "Título da tarefa"}
          />
          <textarea
            className="input-base min-h-[80px] resize-y"
            placeholder="Descrição (opcional)"
            value={descricao}
            maxLength={5000}
            onChange={(e) => setDescricao(e.target.value)}
            aria-label="Descrição"
          />
        </div>

        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="btn-ghost">
            Cancelar
          </button>
          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? "Criando..." : `Criar ${label}`}
          </button>
        </div>
      </form>
    </div>
  );
}
