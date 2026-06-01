"""Testes de edge cases e regressão (validações, idempotência, escopo)."""


def test_titulo_so_espacos_rejeitado(client, login_local):
    headers, _ = login_local()
    r = client.post("/tasks", headers=headers, json={"titulo": "   "})
    assert r.status_code == 422


def test_titulo_com_espacos_e_trimado(client, login_local):
    headers, _ = login_local()
    r = client.post("/tasks", headers=headers, json={"titulo": "  Comprar pão  "})
    assert r.status_code == 201
    assert r.json()["titulo"] == "Comprar pão"


def test_patch_titulo_so_espacos_rejeitado(client, login_local):
    headers, _ = login_local()
    tid = client.post("/tasks", headers=headers, json={"titulo": "ok"}).json()["id"]
    r = client.patch(f"/tasks/{tid}", headers=headers, json={"titulo": "    "})
    assert r.status_code == 422


def test_projeto_nome_so_espacos_rejeitado(client, login_local):
    headers, _ = login_local()
    r = client.post("/projects", headers=headers, json={"nome": "   "})
    assert r.status_code == 422


def test_position_negativa_rejeitada(client, login_local):
    headers, _ = login_local()
    tid = client.post("/tasks", headers=headers, json={"titulo": "ok"}).json()["id"]
    r = client.patch(f"/tasks/{tid}", headers=headers, json={"position": -1})
    assert r.status_code == 422


def test_status_invalido_no_patch_rejeitado(client, login_local):
    headers, _ = login_local()
    tid = client.post("/tasks", headers=headers, json={"titulo": "ok"}).json()["id"]
    r = client.patch(f"/tasks/{tid}", headers=headers, json={"status": "XPTO"})
    assert r.status_code == 422


def test_mover_task_para_projeto_sem_acesso_404(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid_ana = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    tid_b = client.post("/tasks", headers=hb, json={"titulo": "T"}).json()["id"]
    r = client.patch(f"/tasks/{tid_b}", headers=hb, json={"project_id": pid_ana})
    assert r.status_code == 404


def test_criar_task_projeto_inexistente_404(client, login_local):
    headers, _ = login_local()
    r = client.post("/tasks", headers=headers, json={"titulo": "x", "project_id": 99999})
    assert r.status_code == 404


def test_get_projeto_inexistente_404(client, login_local):
    headers, _ = login_local()
    assert client.get("/projects/99999", headers=headers).status_code == 404


def test_patch_vazio_ok(client, login_local):
    headers, _ = login_local()
    tid = client.post("/tasks", headers=headers, json={"titulo": "ok"}).json()["id"]
    r = client.patch(f"/tasks/{tid}", headers=headers, json={})
    assert r.status_code == 200
    assert r.json()["titulo"] == "ok"


def test_add_membro_repetido_idempotente(client, login_local):
    ha, _ = login_local("ana@test.com")
    login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    r1 = client.post(f"/projects/{pid}/members", headers=ha, json={"email": "bruno@test.com"})
    r2 = client.post(f"/projects/{pid}/members", headers=ha, json={"email": "bruno@test.com"})
    assert r1.status_code == 200 and r2.status_code == 200
    bruno_count = sum(1 for m in r2.json()["members"] if m["email"] == "bruno@test.com")
    assert bruno_count == 1  # não duplica


def test_remover_membro_inexistente_idempotente(client, login_local):
    ha, _ = login_local("ana@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    r = client.delete(f"/projects/{pid}/members/99999", headers=ha)
    assert r.status_code == 200


def test_auto_atribuicao_ok(client, login_local):
    headers, email = login_local("ana@test.com")
    tid = client.post("/tasks", headers=headers, json={"titulo": "Self"}).json()["id"]
    r = client.post(f"/tasks/{tid}/assignees", headers=headers, json={"email": email})
    assert r.status_code == 200
    assert any(a["email"] == email for a in r.json()["assignees"])


def test_remover_do_projeto_via_clear_project(client, login_local):
    ha, _ = login_local("ana@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    tid = client.post("/tasks", headers=ha, json={"titulo": "T", "project_id": pid}).json()["id"]
    r = client.patch(f"/tasks/{tid}", headers=ha, json={"clear_project": True})
    assert r.status_code == 200
    assert r.json()["project_id"] is None
