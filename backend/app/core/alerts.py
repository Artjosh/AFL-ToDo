"""Alertas por email sobre mudanças em tarefas de um projeto.

Quando uma tarefa de um projeto é criada ou tem o status alterado, notificamos
por email os destinatários configurados:

- o dono do projeto, se ``owner_receives_alerts`` estiver ligado;
- cada membro com ``receives_alerts`` ligado.

O envio reusa o transporte SMTP de ``app.core.email`` (Brevo). Sem SMTP
configurado (modo dev), não envia nada — apenas é um no-op silencioso. O envio é
"fire-and-forget" e nunca derruba a request que originou a mudança.
"""
from __future__ import annotations

import threading

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email import send_simple_email
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.user import User

_STATUS_LABEL = {
    "pendente": "Pendente",
    "em_andamento": "Em andamento",
    "concluida": "Concluída",
}


def _status_label(status: str) -> str:
    return _STATUS_LABEL.get(status, status)


def alert_recipients(db: Session, project: Project, exclude_user_id: int | None) -> list[str]:
    """Emails que devem receber alerta no projeto (dono + membros marcados).

    ``exclude_user_id`` evita notificar quem originou a ação (não recebe alerta da
    própria mudança).
    """
    emails: list[str] = []
    if project.owner_receives_alerts and project.owner_id != exclude_user_id:
        if project.owner and project.owner.email:
            emails.append(project.owner.email)

    members = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.receives_alerts.is_(True))
        .all()
    )
    for m in members:
        if m.user_id == exclude_user_id:
            continue
        if m.user and m.user.email:
            emails.append(m.user.email)

    # de-duplica preservando ordem
    seen: set[str] = set()
    unique = []
    for e in emails:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return unique


def _send_async(subject: str, recipients: list[str], html: str, text: str) -> None:
    if not settings.smtp_enabled or not recipients:
        return

    def _worker() -> None:
        for to in recipients:
            try:
                send_simple_email(to, subject, html, text)
            except Exception:
                # Alertas nunca devem quebrar o fluxo principal.
                pass

    threading.Thread(target=_worker, daemon=True).start()


def notify_task_event(
    db: Session,
    project: Project,
    task: Task,
    actor: User,
    event: str,
) -> None:
    """Dispara o alerta de um evento de tarefa (created / status_changed).

    Roda em thread separada (fire-and-forget). Resolve os destinatários ANTES de
    sair da request (usa a sessão atual), e só o envio SMTP fica assíncrono.
    """
    recipients = alert_recipients(db, project, exclude_user_id=actor.id)
    if not recipients:
        return

    if event == "task_created":
        assunto = f"[{project.nome}] Nova tarefa: {task.titulo}"
        acao = "criou a tarefa"
        detalhe = f"Status inicial: <strong>{_status_label(task.status)}</strong>."
        detalhe_txt = f"Status inicial: {_status_label(task.status)}."
    else:  # task_status_changed
        assunto = f"[{project.nome}] Tarefa movida: {task.titulo}"
        acao = "alterou o status da tarefa"
        detalhe = f"Novo status: <strong>{_status_label(task.status)}</strong>."
        detalhe_txt = f"Novo status: {_status_label(task.status)}."

    html = f"""\
<div style="max-width:480px;margin:0 auto;font-family:Arial,Helvetica,sans-serif;">
  <h2 style="margin:0 0 16px;color:#0f172a;">{settings.APP_NAME}</h2>
  <p style="margin:0 0 12px;color:#334155;font-size:15px;line-height:1.6;">
    <strong>{actor.email}</strong> {acao} <strong>{task.titulo}</strong>
    no projeto <strong>{project.nome}</strong>.
  </p>
  <p style="margin:0 0 16px;color:#334155;font-size:15px;line-height:1.6;">{detalhe}</p>
  <p style="margin:0;color:#94a3b8;font-size:13px;line-height:1.6;">
    Você recebe este alerta porque está configurado como destinatário de
    notificações deste projeto.
  </p>
</div>"""

    text = (
        f"{settings.APP_NAME}\n\n"
        f"{actor.email} {acao} \"{task.titulo}\" no projeto \"{project.nome}\".\n"
        f"{detalhe_txt}\n\n"
        "Você recebe este alerta porque está configurado como destinatário de "
        "notificações deste projeto."
    )

    _send_async(assunto, recipients, html, text)
