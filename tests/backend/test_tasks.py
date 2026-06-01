"""Testes do CRUD de tarefas, ownership e validação."""


def test_listar_vazio(client, login_local):
    headers, _ = login_local()
    r = client.get("/tasks", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


def test_criar_tarefa(client, login_local):
    headers, _ = login_local()
    r = client.post(
        "/tasks",
        headers=headers,
        json={"titulo": "Estudar FastAPI", "descricao": "deps", "status": "pendente"},
    )
    assert r.status_code == 201
    data = r.json()
    assert data["id"]
    assert data["titulo"] == "Estudar FastAPI"
    assert data["status"] == "pendente"
    assert data["data_criacao"]


def test_criar_sem_titulo_422(client, login_local):
    headers, _ = login_local()
    r = client.post("/tasks", headers=headers, json={"descricao": "sem titulo"})
    assert r.status_code == 422


def test_status_invalido_422(client, login_local):
    headers, _ = login_local()
    r = client.post(
        "/tasks", headers=headers, json={"titulo": "x", "status": "xpto"}
    )
    assert r.status_code == 422


def test_atualizar_status(client, login_local):
    headers, _ = login_local()
    tid = client.post(
        "/tasks", headers=headers, json={"titulo": "T"}
    ).json()["id"]
    r = client.patch(f"/tasks/{tid}", headers=headers, json={"status": "concluida"})
    assert r.status_code == 200
    assert r.json()["status"] == "concluida"


def test_atualizar_parcial_preserva_titulo(client, login_local):
    headers, _ = login_local()
    created = client.post(
        "/tasks", headers=headers, json={"titulo": "Original", "status": "pendente"}
    ).json()
    r = client.patch(f"/tasks/{created['id']}", headers=headers, json={"status": "em_andamento"})
    assert r.status_code == 200
    assert r.json()["titulo"] == "Original"
    assert r.json()["status"] == "em_andamento"


def test_excluir_tarefa(client, login_local):
    headers, _ = login_local()
    tid = client.post("/tasks", headers=headers, json={"titulo": "T"}).json()["id"]
    assert client.delete(f"/tasks/{tid}", headers=headers).status_code == 204
    assert client.get("/tasks", headers=headers).json() == []


def test_ownership_nao_ve_tarefa_de_outro(client, login_local):
    headers_a, _ = login_local("a@test.com")
    headers_b, _ = login_local("b@test.com")
    tid = client.post("/tasks", headers=headers_a, json={"titulo": "da A"}).json()["id"]

    # B não enxerga a tarefa de A
    assert client.get(f"/tasks/{tid}", headers=headers_b).status_code == 404
    assert client.get("/tasks", headers=headers_b).json() == []
    # B não consegue editar nem excluir
    assert client.patch(f"/tasks/{tid}", headers=headers_b, json={"status": "concluida"}).status_code == 404
    assert client.delete(f"/tasks/{tid}", headers=headers_b).status_code == 404


def test_tasks_exige_autenticacao(client):
    assert client.get("/tasks").status_code == 401
    assert client.post("/tasks", json={"titulo": "x"}).status_code == 401


def test_lista_isolada_por_usuario(client, login_local):
    headers_a, _ = login_local("a@test.com")
    headers_b, _ = login_local("b@test.com")
    client.post("/tasks", headers=headers_a, json={"titulo": "A1"})
    client.post("/tasks", headers=headers_a, json={"titulo": "A2"})
    client.post("/tasks", headers=headers_b, json={"titulo": "B1"})

    assert len(client.get("/tasks", headers=headers_a).json()) == 2
    assert len(client.get("/tasks", headers=headers_b).json()) == 1
