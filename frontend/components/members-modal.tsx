/**
 * Modal de gestão do projeto: membros, permissões por membro e configurações.
 *
 * O dono pode:
 * - adicionar/remover membros (por email);
 * - configurar, por membro: mover o projeto, mover tarefas, gerenciar tarefas
 *   (criar/editar/excluir) e receber emails de alerta;
 * - configurar o projeto: política ao remover membro (manter como dono / revogar)
 *   e se o próprio dono recebe alertas por email.
 */
"use client";

import { useState } from "react";

import Avatar from "@/components/avatar";
import { useToast } from "@/components/toast";
import type { Member, ProjectDetail, RemovedMemberPolicy } from "@/lib/types";

interface MembersModalProps {
  open: boolean;
  project: ProjectDetail | null;
  canManage: boolean; // é o dono?
  onClose: () => void;
  onAdd: (email: string) => Promise<void>;
  onRemove: (userId: number) => Promise<void>;
  onUpdatePermissions: (
    userId: number,
    perms: Partial<{
      can_move_project: boolean;
      can_move_tasks: boolean;
      can_manage_tasks: boolean;
      receives_alerts: boolean;
    }>,
  ) => Promise<void>;
  onUpdateProject: (
    changes: Partial<{
      removed_member_policy: RemovedMemberPolicy;
      owner_receives_alerts: boolean;
    }>,
  ) => Promise<void>;
}

const PERMISSION_LABELS: {
  key: keyof Pick<
    Member,
    "can_move_project" | "can_move_tasks" | "can_manage_tasks" | "receives_alerts"
  >;
  label: string;
  hint: string;
}[] = [
  { key: "can_move_project", label: "Mover o projeto", hint: "trocar o status do próprio projeto" },
  { key: "can_move_tasks", label: "Mover tarefas", hint: "arrastar tarefas entre colunas" },
  { key: "can_manage_tasks", label: "Gerenciar tarefas", hint: "criar, editar e excluir" },
  { key: "receives_alerts", label: "Receber alertas", hint: "emails de criação/mudança de status" },
];

export default function MembersModal({
  open,
  project,
  canManage,
  onClose,
  onAdd,
  onRemove,
  onUpdatePermissions,
  onUpdateProject,
}: MembersModalProps) {
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);

  if (!open || !project) return null;

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    const value = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      toast.error("Informe um email válido.", { key: "member-invalid" });
      return;
    }
    setBusy(true);
    try {
      await onAdd(value);
      setEmail("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-[210] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="max-h-[88vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-border bg-surface p-6 shadow-[0_20px_60px_rgba(0,0,0,0.6)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-bold text-foreground">Membros e permissões</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-muted transition-colors hover:text-foreground"
            aria-label="Fechar"
          >
            ✕
          </button>
        </div>

        {/* Configurações do projeto (só dono) */}
        {canManage && (
          <div className="mb-5 space-y-3 rounded-lg border border-border bg-surface-2/60 p-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted">
              Configurações do projeto
            </p>

            <label className="flex items-center justify-between gap-3 text-sm text-foreground">
              <span>
                Ao remover um membro
                <span className="block text-[11px] text-muted">
                  o que acontece com as tarefas que ele criou
                </span>
              </span>
              <select
                className="input-base w-44"
                value={project.removed_member_policy}
                onChange={(e) =>
                  onUpdateProject({
                    removed_member_policy: e.target.value as RemovedMemberPolicy,
                  })
                }
                aria-label="Política ao remover membro"
              >
                <option value="revoke">Revogar acesso</option>
                <option value="keep">Mantém como dono</option>
              </select>
            </label>

            <label className="flex items-center justify-between gap-3 text-sm text-foreground">
              <span>
                Eu (dono) recebo alertas
                <span className="block text-[11px] text-muted">
                  emails de criação/mudança de status
                </span>
              </span>
              <input
                type="checkbox"
                className="h-4 w-4 accent-accent"
                checked={project.owner_receives_alerts}
                onChange={(e) =>
                  onUpdateProject({ owner_receives_alerts: e.target.checked })
                }
                aria-label="Dono recebe alertas"
              />
            </label>
          </div>
        )}

        {/* Lista de membros */}
        <div className="mb-4 space-y-3">
          {project.members.map((m) => (
            <div
              key={m.id}
              className="rounded-lg border border-border bg-surface-2 p-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Avatar email={m.email} size={28} />
                  <div>
                    <p className="text-sm text-foreground">{m.email}</p>
                    <p className="text-[10px] uppercase tracking-wider text-muted">
                      {m.role === "owner" ? "Dono" : "Membro"}
                    </p>
                  </div>
                </div>
                {canManage && m.role !== "owner" && (
                  <button
                    type="button"
                    onClick={() => onRemove(m.id)}
                    className="rounded-lg border border-danger/40 bg-danger/10 px-2.5 py-1 text-xs font-semibold text-danger transition-colors hover:bg-danger/20"
                  >
                    Remover
                  </button>
                )}
              </div>

              {/* Permissões por membro (só dono, e não para o próprio dono) */}
              {canManage && m.role !== "owner" && (
                <div className="mt-3 grid grid-cols-2 gap-2">
                  {PERMISSION_LABELS.map((p) => (
                    <label
                      key={p.key}
                      className="flex items-start gap-2 rounded-md border border-border bg-surface px-2 py-1.5 text-xs text-foreground"
                      title={p.hint}
                    >
                      <input
                        type="checkbox"
                        className="mt-0.5 h-3.5 w-3.5 accent-accent"
                        checked={Boolean(m[p.key])}
                        onChange={(e) =>
                          onUpdatePermissions(m.id, { [p.key]: e.target.checked })
                        }
                      />
                      <span>
                        {p.label}
                        <span className="block text-[10px] text-muted">{p.hint}</span>
                      </span>
                    </label>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        {canManage ? (
          <form onSubmit={handleAdd} className="flex gap-2">
            <input
              className="input-base flex-1"
              placeholder="email@pessoa.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-label="Email do novo membro"
            />
            <button type="submit" className="btn-primary" disabled={busy}>
              {busy ? "..." : "Adicionar"}
            </button>
          </form>
        ) : (
          <p className="text-xs text-muted">
            Apenas o dono do projeto pode gerenciar membros e permissões.
          </p>
        )}
      </div>
    </div>
  );
}
