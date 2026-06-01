"""Testes das permissões por membro, status do projeto, política de remoção e alertas."""
import app.core.alerts as alerts_module


def _share(client, ha, pid, email):
    """Compartilha o projeto e devolve o user_id do membro adicionado."""
    r = client.post(f"/projects/{pid}/members", headers=ha, json={"email": email})
    assert r.status_code == 200, r.text
    return next(m["id"] for m in r.json()["members"] if m["email"] == email)


# ---------------------------------------------------------------- status do projeto

def test_projeto_nasce_pendente_e_dono_move(client, login_local):
    ha, _ = login_local("ana@test.com")
    p = client.post("/projects", headers=ha, json={"nome": "P"}).json()
    assert p["status"] == "pendente"
    assert p["can_move_project"] is True

    r = client.patch(f"/projects/{p['id']}", headers=ha, json={"status": "em_andamento"})
    assert r.status_code == 200
    assert r.json()["status"] == "em_andamento"


def test_membro_sem_permissao_nao_move_projeto(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    buid = _share(client, ha, pid, "bruno@test.com")

    # por padrão, membro NÃO pode mover o projeto
    assert client.patch(f"/projects/{pid}", headers=hb, json={"status": "concluida"}).status_code == 403

    # dono concede a permissão
    client.patch(f"/projects/{pid}/members/{buid}", headers=ha, json={"can_move_project": True})
    r = client.patch(f"/projects/{pid}", headers=hb, json={"status": "concluida"})
    assert r.status_code == 200
    assert r.json()["status"] == "concluida"


def test_membro_nao_altera_nome_mesmo_podendo_mover(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    buid = _share(client, ha, pid, "bruno@test.com")
    client.patch(f"/projects/{pid}/members/{buid}", headers=ha, json={"can_move_project": True})

    # mover status: ok; alterar nome: 403 (só dono)
    assert client.patch(f"/projects/{pid}", headers=hb, json={"nome": "Novo"}).status_code == 403


# ---------------------------------------------------------------- mover/gerenciar tarefas

def test_membro_sem_can_move_tasks_nao_move(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    buid = _share(client, ha, pid, "bruno@test.com")
    tid = client.post("/tasks", headers=ha, json={"titulo": "T", "project_id": pid}).json()["id"]

    client.patch(f"/projects/{pid}/members/{buid}", headers=ha, json={"can_move_tasks": False})
    # reorder com mudança de status deve ser ignorado (sem permissão) -> tarefa não muda
    r = client.post("/tasks/reorder", headers=hb, json={"task_ids": [tid], "status": "concluida"})
    assert r.status_code == 200
    # como não tinha permissão, a tarefa não entra em 'updated'
    assert r.json() == []
    # confirma que o status não mudou
    assert client.get(f"/tasks/{tid}", headers=ha).json()["status"] == "pendente"


def test_membro_sem_can_manage_tasks_nao_cria_nem_exclui(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    buid = _share(client, ha, pid, "bruno@test.com")
    client.patch(f"/projects/{pid}/members/{buid}", headers=ha, json={"can_manage_tasks": False})

    # criar tarefa no projeto -> 403
    assert client.post("/tasks", headers=hb, json={"titulo": "X", "project_id": pid}).status_code == 403

    # dono cria; bruno tenta excluir -> 403
    tid = client.post("/tasks", headers=ha, json={"titulo": "T", "project_id": pid}).json()["id"]
    assert client.delete(f"/tasks/{tid}", headers=hb).status_code == 403


def test_dono_sempre_pode_tudo(client, login_local):
    ha, _ = login_local("ana@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    tid = client.post("/tasks", headers=ha, json={"titulo": "T", "project_id": pid}).json()["id"]
    assert client.patch(f"/tasks/{tid}", headers=ha, json={"status": "concluida"}).status_code == 200
    assert client.delete(f"/tasks/{tid}", headers=ha).status_code == 204


# ---------------------------------------------------------------- política de remoção

def test_politica_keep_membro_mantem_task_apos_remocao(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    client.patch(f"/projects/{pid}", headers=ha, json={"removed_member_policy": "keep"})
    buid = _share(client, ha, pid, "bruno@test.com")

    tid = client.post("/tasks", headers=hb, json={"titulo": "Do Bruno", "project_id": pid}).json()["id"]
    # remove o membro
    client.delete(f"/projects/{pid}/members/{buid}", headers=ha)

    # com KEEP, bruno continua dono/criador e ainda enxerga a tarefa
    t = client.get(f"/tasks/{tid}", headers=hb)
    assert t.status_code == 200
    assert t.json()["creator"]["email"] == "bruno@test.com"


def test_politica_revoke_transfere_task_ao_dono(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    proj = client.post("/projects", headers=ha, json={"nome": "P"}).json()
    pid = proj["id"]
    # padrão já é revoke, mas deixamos explícito
    client.patch(f"/projects/{pid}", headers=ha, json={"removed_member_policy": "revoke"})
    buid = _share(client, ha, pid, "bruno@test.com")

    tid = client.post("/tasks", headers=hb, json={"titulo": "Do Bruno", "project_id": pid}).json()["id"]
    client.delete(f"/projects/{pid}/members/{buid}", headers=ha)

    # com REVOKE, bruno perde acesso...
    assert client.get(f"/tasks/{tid}", headers=hb).status_code == 404
    # ...e a tarefa foi transferida para a dona (ana continua vendo)
    t = client.get(f"/tasks/{tid}", headers=ha)
    assert t.status_code == 200
    assert t.json()["creator"]["email"] == "ana@test.com"


# ---------------------------------------------------------------- alertas por email

def test_alert_recipients_inclui_dono_e_membros_marcados(client, login_local, db_session):
    from app.api.access import get_accessible_project
    from app.core.alerts import alert_recipients
    from app.models.user import User

    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    buid = _share(client, ha, pid, "bruno@test.com")
    client.patch(f"/projects/{pid}/members/{buid}", headers=ha, json={"receives_alerts": True})

    # resolve via sessão de teste
    ana = db_session.query(User).filter(User.email == "ana@test.com").first()
    project = get_accessible_project(db_session, pid, ana)

    # ana é a atora (excluída); bruno marcado deve receber
    recipients = alert_recipients(db_session, project, exclude_user_id=ana.id)
    assert "bruno@test.com" in recipients
    assert "ana@test.com" not in recipients


def test_criar_task_dispara_alerta(client, login_local, monkeypatch):
    """Ao criar tarefa num projeto, notify_task_event é chamado com 'task_created'."""
    calls = []
    monkeypatch.setattr(
        alerts_module,
        "_send_async",
        lambda subject, recipients, html, text: calls.append((subject, recipients)),
    )

    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    buid = _share(client, ha, pid, "bruno@test.com")
    client.patch(f"/projects/{pid}/members/{buid}", headers=ha, json={"receives_alerts": True})

    # bruno cria -> ana (dono) deve ser destinatária
    client.post("/tasks", headers=hb, json={"titulo": "Nova", "project_id": pid})
    assert calls, "deveria ter disparado um alerta"
    _, recipients = calls[-1]
    assert "ana@test.com" in recipients
