"""Testes de atribuídos (assignees) e acesso por atribuição."""


def test_adicionar_e_remover_assignee(client, login_local):
    ha, _ = login_local("ana@test.com")
    login_local("bruno@test.com")  # garante que bruno existe
    tid = client.post("/tasks", headers=ha, json={"titulo": "T"}).json()["id"]

    r = client.post(f"/tasks/{tid}/assignees", headers=ha, json={"email": "bruno@test.com"})
    assert r.status_code == 200
    assert any(a["email"] == "bruno@test.com" for a in r.json()["assignees"])
    buid = next(a["id"] for a in r.json()["assignees"] if a["email"] == "bruno@test.com")

    r = client.delete(f"/tasks/{tid}/assignees/{buid}", headers=ha)
    assert r.status_code == 200
    assert all(a["email"] != "bruno@test.com" for a in r.json()["assignees"])


def test_assignee_ganha_acesso_a_task_solta(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    tid = client.post("/tasks", headers=ha, json={"titulo": "Compartilhada"}).json()["id"]

    # antes de atribuir, bruno não vê
    assert client.get(f"/tasks/{tid}", headers=hb).status_code == 404
    # atribui
    client.post(f"/tasks/{tid}/assignees", headers=ha, json={"email": "bruno@test.com"})
    # agora vê e aparece na listagem geral dele
    assert client.get(f"/tasks/{tid}", headers=hb).status_code == 200
    assert any(t["id"] == tid for t in client.get("/tasks", headers=hb).json())


def test_assignee_inexistente_404(client, login_local):
    ha, _ = login_local("ana@test.com")
    tid = client.post("/tasks", headers=ha, json={"titulo": "T"}).json()["id"]
    r = client.post(f"/tasks/{tid}/assignees", headers=ha, json={"email": "ninguem@test.com"})
    assert r.status_code == 404


def test_task_out_inclui_creator_e_position(client, login_local):
    ha, _ = login_local("ana@test.com")
    r = client.post("/tasks", headers=ha, json={"titulo": "T"})
    data = r.json()
    assert data["creator"]["email"] == "ana@test.com"
    assert "position" in data
    assert data["project_id"] is None
    assert data["assignees"] == []


def test_filtro_standalone_e_por_projeto(client, login_local):
    ha, _ = login_local("ana@test.com")
    pid = client.post("/projects", headers=ha, json={"nome": "P"}).json()["id"]
    client.post("/tasks", headers=ha, json={"titulo": "Solta"})
    client.post("/tasks", headers=ha, json={"titulo": "No projeto", "project_id": pid})

    standalone = client.get("/tasks", headers=ha, params={"standalone": "true"}).json()
    assert len(standalone) == 1 and standalone[0]["titulo"] == "Solta"

    doproj = client.get("/tasks", headers=ha, params={"project_id": pid}).json()
    assert len(doproj) == 1 and doproj[0]["titulo"] == "No projeto"

    todas = client.get("/tasks", headers=ha).json()
    assert len(todas) == 2
