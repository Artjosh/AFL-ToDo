"""Testes do endpoint de reordenação (drag-and-drop fino)."""


def _create(client, headers, titulo, status="pendente"):
    return client.post(
        "/tasks", headers=headers, json={"titulo": titulo, "status": status}
    ).json()


def test_reordenar_dentro_da_coluna(client, login_local):
    h, _ = login_local()
    a = _create(client, h, "A")
    b = _create(client, h, "B")
    c = _create(client, h, "C")
    # ordem inicial: A(0) B(1) C(2). Reordena para C, A, B
    r = client.post(
        "/tasks/reorder",
        headers=h,
        json={"task_ids": [c["id"], a["id"], b["id"]], "status": "pendente"},
    )
    assert r.status_code == 200
    by_id = {t["id"]: t["position"] for t in r.json()}
    assert by_id[c["id"]] == 0
    assert by_id[a["id"]] == 1
    assert by_id[b["id"]] == 2


def test_reorder_move_de_coluna_muda_status(client, login_local):
    h, _ = login_local()
    a = _create(client, h, "A", status="pendente")
    r = client.post(
        "/tasks/reorder",
        headers=h,
        json={"task_ids": [a["id"]], "status": "concluida"},
    )
    assert r.status_code == 200
    assert r.json()[0]["status"] == "concluida"
    assert r.json()[0]["position"] == 0


def test_reorder_ignora_tarefa_sem_acesso(client, login_local):
    ha, _ = login_local("ana@test.com")
    hb, _ = login_local("bruno@test.com")
    a = _create(client, ha, "da Ana")
    b = _create(client, hb, "do Bruno")
    # Bruno tenta reordenar incluindo a tarefa da Ana -> a dela é ignorada
    r = client.post(
        "/tasks/reorder",
        headers=hb,
        json={"task_ids": [a["id"], b["id"]], "status": "pendente"},
    )
    assert r.status_code == 200
    returned_ids = [t["id"] for t in r.json()]
    assert a["id"] not in returned_ids
    assert b["id"] in returned_ids
    # a tarefa da Ana permanece intacta
    assert client.get(f"/tasks/{a['id']}", headers=ha).json()["position"] == 0


def test_reorder_lista_vazia_422(client, login_local):
    h, _ = login_local()
    r = client.post("/tasks/reorder", headers=h, json={"task_ids": []})
    assert r.status_code == 422


def test_reorder_status_invalido_422(client, login_local):
    h, _ = login_local()
    a = _create(client, h, "A")
    r = client.post(
        "/tasks/reorder", headers=h, json={"task_ids": [a["id"]], "status": "XPTO"}
    )
    assert r.status_code == 422


def test_reorder_exige_auth(client):
    assert client.post("/tasks/reorder", json={"task_ids": [1]}).status_code == 401
