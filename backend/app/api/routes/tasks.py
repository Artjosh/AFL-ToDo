"""Rotas de tarefas (CRUD) com acesso compartilhado, projetos e atribuídos.

Acesso por membership (ver app/api/access.py): criador, atribuídos e membros do
projeto. O criador é sempre o usuário do token, nunca um id do frontend.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.access import (
    accessible_tasks_query,
    can_manage_tasks,
    can_move_tasks,
    ensure_can,
    get_accessible_project,
    get_accessible_task,
    task_is_accessible,
)
from app.api.deps import get_current_user
from app.api.serializers import task_to_out
from app.core.alerts import notify_task_event
from app.db.session import get_db
from app.models.project import Project
from app.models.task import Task, TaskAssignee
from app.models.user import User
from app.schemas.task import (
    AssigneeUpdate,
    ReorderRequest,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from app.services.realtime import (
    notify_board,
    topic_for_project,
    topic_for_standalone,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _project_of(db: Session, task: Task) -> Project | None:
    if task.project_id is None:
        return None
    return db.query(Project).filter(Project.id == task.project_id).first()


def _notify_task_change(task: Task, event: str) -> None:
    """Publica um evento de realtime no tópico apropriado da tarefa."""
    if task.project_id is not None:
        topic = topic_for_project(task.project_id)
    else:
        topic = topic_for_standalone(task.user_id)
    notify_board(topic, event, {"task_id": task.id})


@router.get("", response_model=list[TaskOut])
def list_tasks(
    project_id: int | None = None,
    standalone: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    """Lista tarefas acessíveis.

    - sem filtro: todas as tarefas acessíveis;
    - ?standalone=true: apenas tarefas soltas (sem projeto);
    - ?project_id=N: tarefas do projeto N (se o usuário tiver acesso).
    """
    query = accessible_tasks_query(db, current_user)

    if project_id is not None:
        get_accessible_project(db, project_id, current_user)  # valida acesso
        query = query.filter(Task.project_id == project_id)
    elif standalone:
        query = query.filter(Task.project_id.is_(None))

    tasks = query.order_by(Task.position.asc(), Task.data_criacao.desc()).all()
    return [task_to_out(t) for t in tasks]


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    if payload.project_id is not None:
        # Só cria dentro de projeto ao qual o usuário tem acesso E permissão.
        project = get_accessible_project(db, payload.project_id, current_user)
        ensure_can(can_manage_tasks(db, project, current_user))
    else:
        project = None

    # posição = final da coluna (status) no escopo (projeto ou soltas).
    scope = (
        Task.project_id == payload.project_id
        if payload.project_id is not None
        else Task.project_id.is_(None)
    )
    max_pos = (
        db.query(Task.position)
        .filter(scope, Task.status == payload.status)
        .order_by(Task.position.desc())
        .first()
    )
    next_pos = (max_pos[0] + 1) if max_pos else 0

    task = Task(
        user_id=current_user.id,
        project_id=payload.project_id,
        titulo=payload.titulo,
        descricao=payload.descricao,
        status=payload.status,
        position=next_pos,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    _notify_task_change(task, "task_created")
    if project is not None:
        notify_task_event(db, project, task, current_user, "task_created")
    return task_to_out(task)


@router.post("/reorder", response_model=list[TaskOut])
def reorder_tasks(
    payload: ReorderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TaskOut]:
    """Reordena (e opcionalmente move de coluna) uma lista de tarefas.

    Recebe a ordem final dos ids de uma coluna (status) num escopo (projeto ou
    soltas). Aplica position sequencial e, se informado, o novo status — útil
    para drag-and-drop fino dentro da mesma coluna ou entre colunas.

    Só altera tarefas às quais o usuário tem acesso; ids inacessíveis são ignorados.
    """
    updated: list[Task] = []
    status_changed: list[Task] = []
    for index, task_id in enumerate(payload.task_ids):
        task = db.query(Task).filter(Task.id == task_id).first()
        if task is None or not task_is_accessible(db, task, current_user):
            continue
        # Mover de status exige permissão no projeto (tarefa solta: só o criador).
        project = _project_of(db, task)
        if payload.status is not None and payload.status != task.status:
            if project is not None:
                if not can_move_tasks(db, project, current_user):
                    continue
            elif task.user_id != current_user.id:
                continue
            task.status = payload.status
            status_changed.append(task)
        else:
            # Reordenar dentro da coluna: exige ao menos poder mover tarefas.
            if project is not None and not can_move_tasks(db, project, current_user):
                continue
        task.position = index
        updated.append(task)

    db.commit()
    for t in updated:
        db.refresh(t)
    # Notifica os tópicos afetados (de-duplicados).
    notified: set[str] = set()
    for t in updated:
        topic = (
            topic_for_project(t.project_id)
            if t.project_id is not None
            else topic_for_standalone(t.user_id)
        )
        if topic not in notified:
            notify_board(topic, "tasks_reordered", {})
            notified.add(topic)
    # Alertas por email para mudanças de status em tarefas de projeto.
    for t in status_changed:
        project = _project_of(db, t)
        if project is not None:
            notify_task_event(db, project, t, current_user, "task_status_changed")
    return [task_to_out(t) for t in updated]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    return task_to_out(get_accessible_task(db, task_id, current_user))


@router.patch("/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = get_accessible_task(db, task_id, current_user)
    project = _project_of(db, task)
    ensure_can(can_manage_tasks(db, project, current_user))

    data = payload.model_dump(exclude_unset=True)
    clear_project = data.pop("clear_project", False)
    old_status = task.status

    # Mover para outro projeto exige acesso ao destino.
    if "project_id" in data and data["project_id"] is not None:
        get_accessible_project(db, data["project_id"], current_user)
    if clear_project:
        data["project_id"] = None

    for field, value in data.items():
        setattr(task, field, value)

    db.commit()
    db.refresh(task)
    _notify_task_change(task, "task_updated")
    # Alerta de mudança de status (tarefa em projeto).
    new_project = _project_of(db, task)
    if new_project is not None and "status" in data and data["status"] != old_status:
        notify_task_event(db, new_project, task, current_user, "task_status_changed")
    return task_to_out(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    task = get_accessible_task(db, task_id, current_user)
    project = _project_of(db, task)
    ensure_can(can_manage_tasks(db, project, current_user))
    db.delete(task)
    db.commit()
    _notify_task_change(task, "task_deleted")


# ------------------------------------------------------------ atribuídos

@router.post("/{task_id}/assignees", response_model=TaskOut)
def add_assignee(
    task_id: int,
    payload: AssigneeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = get_accessible_task(db, task_id, current_user)
    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não existe usuário com este email (ele precisa ter acessado ao menos uma vez).",
        )
    exists = (
        db.query(TaskAssignee)
        .filter(TaskAssignee.task_id == task.id, TaskAssignee.user_id == user.id)
        .first()
    )
    if exists is None:
        db.add(TaskAssignee(task_id=task.id, user_id=user.id))
        db.commit()
        db.refresh(task)
    return task_to_out(task)


@router.delete("/{task_id}/assignees/{user_id}", response_model=TaskOut)
def remove_assignee(
    task_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TaskOut:
    task = get_accessible_task(db, task_id, current_user)
    assignee = (
        db.query(TaskAssignee)
        .filter(TaskAssignee.task_id == task.id, TaskAssignee.user_id == user_id)
        .first()
    )
    if assignee is not None:
        db.delete(assignee)
        db.commit()
        db.refresh(task)
    return task_to_out(task)
