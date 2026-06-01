"""Rotas de projetos (board aninhado) e gestão de membros (compartilhamento)."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.access import (
    can_manage_tasks as access_can_manage_tasks,
)
from app.api.access import (
    can_move_project,
    ensure_can,
    ensure_project_owner,
    get_accessible_project,
    user_project_ids,
)
from app.api.access import (
    can_move_tasks as access_can_move_tasks,
)
from app.api.deps import get_current_user
from app.api.serializers import task_to_out
from app.db.session import get_db
from app.models.project import Project, ProjectMember, ProjectRole, RemovedMemberPolicy
from app.models.task import Task, TaskAssignee
from app.models.user import User
from app.schemas.project import (
    MemberAdd,
    MemberOut,
    MemberPermissionsUpdate,
    ProjectCreate,
    ProjectDetail,
    ProjectOut,
    ProjectUpdate,
)
from app.services.realtime import notify_board, topic_for_standalone

router = APIRouter(prefix="/projects", tags=["projects"])


def _members_out(db: Session, project: Project) -> list[MemberOut]:
    out: list[MemberOut] = [
        MemberOut(
            id=project.owner.id,
            email=project.owner.email,
            role=ProjectRole.OWNER,
            can_move_project=True,
            can_move_tasks=True,
            can_manage_tasks=True,
            receives_alerts=project.owner_receives_alerts,
        )
    ]
    for m in project.members:
        out.append(
            MemberOut(
                id=m.user.id,
                email=m.user.email,
                role=m.role,
                can_move_project=m.can_move_project,
                can_move_tasks=m.can_move_tasks,
                can_manage_tasks=m.can_manage_tasks,
                receives_alerts=m.receives_alerts,
            )
        )
    return out


def _project_out(db: Session, project: Project, user: User) -> ProjectOut:
    is_owner = project.owner_id == user.id
    role = ProjectRole.OWNER if is_owner else ProjectRole.MEMBER
    task_count = db.query(Task).filter(Task.project_id == project.id).count()
    return ProjectOut(
        id=project.id,
        nome=project.nome,
        descricao=project.descricao,
        owner_id=project.owner_id,
        status=project.status,
        position=project.position,
        removed_member_policy=project.removed_member_policy,
        owner_receives_alerts=project.owner_receives_alerts,
        data_criacao=project.data_criacao,
        updated_at=project.updated_at,
        role=role,
        can_move_project=can_move_project(db, project, user),
        can_move_tasks=access_can_move_tasks(db, project, user),
        can_manage_tasks=access_can_manage_tasks(db, project, user),
        task_count=task_count,
        members=_members_out(db, project),
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ProjectOut]:
    ids = user_project_ids(db, current_user)
    if not ids:
        return []
    projects = (
        db.query(Project)
        .filter(Project.id.in_(ids))
        .order_by(Project.data_criacao.desc())
        .all()
    )
    return [_project_out(db, p, current_user) for p in projects]


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = Project(
        nome=payload.nome,
        descricao=payload.descricao,
        owner_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_out(db, project, current_user)


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectDetail:
    project = get_accessible_project(db, project_id, current_user)
    base = _project_out(db, project, current_user)
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project.id)
        .order_by(Task.position.asc(), Task.data_criacao.desc())
        .all()
    )
    return ProjectDetail(**base.model_dump(), tasks=[task_to_out(t) for t in tasks])


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = get_accessible_project(db, project_id, current_user)
    data = payload.model_dump(exclude_unset=True)

    # Mudar o STATUS do projeto: dono ou membro com can_move_project.
    if "status" in data:
        ensure_can(can_move_project(db, project, current_user))
        new_status = data.pop("status")
        if new_status != project.status:
            project.status = new_status
            notify_board(topic_for_standalone(project.owner_id), "project_moved", {})

    # Demais campos (nome, descrição, política, alertas do dono): só o dono.
    if data:
        ensure_project_owner(db, project, current_user)
        for field, value in data.items():
            setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return _project_out(db, project, current_user)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    project = get_accessible_project(db, project_id, current_user)
    ensure_project_owner(db, project, current_user)
    db.delete(project)
    db.commit()


# ------------------------------------------------------------ membros

@router.post("/{project_id}/members", response_model=ProjectOut)
def add_member(
    project_id: int,
    payload: MemberAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = get_accessible_project(db, project_id, current_user)
    ensure_project_owner(db, project, current_user)

    user = db.query(User).filter(User.email == payload.email.lower().strip()).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Não existe usuário com este email (ele precisa ter acessado ao menos uma vez).",
        )
    if user.id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O dono já participa do projeto.",
        )
    exists = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user.id)
        .first()
    )
    if exists is None:
        db.add(ProjectMember(project_id=project.id, user_id=user.id, role=ProjectRole.MEMBER))
        db.commit()
        db.refresh(project)
    return _project_out(db, project, current_user)


@router.patch("/{project_id}/members/{user_id}", response_model=ProjectOut)
def update_member_permissions(
    project_id: int,
    user_id: int,
    payload: MemberPermissionsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    """Atualiza as permissões de um membro (só o dono pode)."""
    project = get_accessible_project(db, project_id, current_user)
    ensure_project_owner(db, project, current_user)

    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user_id)
        .first()
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Membro não encontrado."
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    db.commit()
    db.refresh(project)
    return _project_out(db, project, current_user)


@router.delete("/{project_id}/members/{user_id}", response_model=ProjectOut)
def remove_member(
    project_id: int,
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectOut:
    project = get_accessible_project(db, project_id, current_user)
    ensure_project_owner(db, project, current_user)
    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == user_id)
        .first()
    )
    if member is not None:
        _apply_removal_policy(db, project, user_id)
        db.delete(member)
        db.commit()
        db.refresh(project)
    return _project_out(db, project, current_user)


def _apply_removal_policy(db: Session, project: Project, user_id: int) -> None:
    """Aplica a política do projeto às tarefas do membro removido.

    - KEEP: nada muda — o usuário continua criador (e mantém atribuições), então
      segue vendo/possuindo as tarefas que criou, mesmo sem ser membro.
    - REVOKE: o usuário perde o vínculo. As tarefas que ele CRIOU no projeto são
      transferidas para o dono (para não ficarem órfãs/invisíveis) e as
      atribuições dele nas tarefas do projeto são removidas.
    """
    if project.removed_member_policy != RemovedMemberPolicy.REVOKE:
        return

    # Transfere a autoria das tarefas do membro (neste projeto) para o dono.
    tasks = (
        db.query(Task)
        .filter(Task.project_id == project.id, Task.user_id == user_id)
        .all()
    )
    for t in tasks:
        t.user_id = project.owner_id

    # Remove atribuições do membro nas tarefas deste projeto.
    project_task_ids = [
        row[0]
        for row in db.query(Task.id).filter(Task.project_id == project.id).all()
    ]
    if project_task_ids:
        db.query(TaskAssignee).filter(
            TaskAssignee.user_id == user_id,
            TaskAssignee.task_id.in_(project_task_ids),
        ).delete(synchronize_session=False)
