"""Testes de projetos, compartilhamento (membros) e acesso colaborativo."""


def test_criar_projeto_define_owner(client, login_local):
    headers, _ = login_local("ana@test.com")
    r = client.post("/projects", headers=headers, json={"nome": "Lançamento"})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["nome"] == "Lançamento"
    assert data["role"] == "owner"
    assert data["task_count"] == 0
    # o dono aparece nos membros
    assert any(m["email"] == "ana@test.com" and m["role"] == "owner" for m in data["members"])


def test_listar_projetos_so_os_acessiveis(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    client.post("/projects", headers=ha, json={"nome": "Da Ana"})
    assert len(client.get("/projects", headers=ha).json()) == 1
    assert client.get("/projects", headers=hb).json() == []


def test_nao_membro_nao_ve_projeto(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "Secreto"}).json()["id"]
    assert client.get(f"/projects/{pid}", headers=hb).status_code == 404


def test_compartilhar_da_acesso_ao_membro(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "Time"}).json()["id"]
    client.post("/tasks", headers=ha, json={"titulo": "T1", "project_id": pid})

    # compartilha
    r = client.post(f"/projects/{pid}/members", headers=ha, json={"email": "bruno@test.com"})
    assert r.status_code == 200, r.text

    # bruno agora vê projeto + tarefa
    detail = client.get(f"/projects/{pid}", headers=hb)
    assert detail.status_code == 200
    assert len(detail.json()["tasks"]) == 1


def test_adicionar_membro_inexistente_404(client, login_local):
    ha, _ = login_local("ana@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "X"}).json()["id"]
    r = client.post(f"/projects/{pid}/members", headers=ha, json={"email": "naoexiste@test.com"})
    assert r.status_code == 404


def test_membro_nao_pode_deletar_projeto(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "Time"}).json()["id"]
    client.post(f"/projects/{pid}/members", headers=ha, json={"email": "bruno@test.com"})
    assert client.delete(f"/projects/{pid}", headers=hb).status_code == 403
    # dono pode
    assert client.delete(f"/projects/{pid}", headers=ha).status_code == 204


def test_remover_membro_revoga_acesso_ao_projeto(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "Time"}).json()["id"]
    r = client.post(f"/projects/{pid}/members", headers=ha, json={"email": "bruno@test.com"})
    buid = next(m["id"] for m in r.json()["members"] if m["email"] == "bruno@test.com")

    assert client.get(f"/projects/{pid}", headers=hb).status_code == 200
    client.delete(f"/projects/{pid}/members/{buid}", headers=ha)
    assert client.get(f"/projects/{pid}", headers=hb).status_code == 404


def test_membro_cria_e_move_task_no_projeto(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "Time"}).json()["id"]
    client.post(f"/projects/{pid}/members", headers=ha, json={"email": "bruno@test.com"})

    # bruno cria tarefa no projeto compartilhado
    t = client.post("/tasks", headers=hb, json={"titulo": "Do Bruno", "project_id": pid})
    assert t.status_code == 201
    tid = t.json()["id"]
    # e move/atualiza status
    r = client.patch(f"/tasks/{tid}", headers=hb, json={"status": "em_andamento", "position": 3})
    assert r.status_code == 200
    assert r.json()["status"] == "em_andamento"
    assert r.json()["position"] == 3


def test_criar_task_em_projeto_sem_acesso_404(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "Privado"}).json()["id"]
    r = client.post("/tasks", headers=hb, json={"titulo": "Invasao", "project_id": pid})
    assert r.status_code == 404
