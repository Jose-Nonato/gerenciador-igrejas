import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from core.database import SessionLocal
from models import LogAuditoria, Usuario
from models.enums import PerfilUsuario

ADMIN = PerfilUsuario.ADMIN


@pytest.fixture
def igreja(criar_igreja):
    return criar_igreja("Igreja A")


@pytest.fixture
def admin(criar_usuario, igreja):
    return criar_usuario(igreja, "admin@a.org", perfil=ADMIN)


@pytest.fixture
def h(auth, admin):
    return auth(admin)


@pytest.fixture
def novo_membro(client, h):
    def _novo(**campos):
        r = client.post("/membros", headers=h, json={"nome": "Maria Silva", "rol": "C", **campos})
        assert r.status_code == 201, r.text
        return r.json()

    return _novo


def auditoria(acao):
    with SessionLocal() as db:
        return list(db.scalars(select(LogAuditoria).where(LogAuditoria.acao == acao)))


def contas():
    with SessionLocal() as db:
        return {u.email: u for u in db.scalars(select(Usuario))}


# ---------- indicador de acesso no membro ----------

def test_membro_sem_conta_vem_com_acesso_nulo(client, h, novo_membro):
    m = novo_membro()
    assert m["acesso"] is None
    assert client.get(f"/membros/{m['id']}", headers=h).json()["acesso"] is None
    assert client.get("/membros", headers=h).json()["items"][0]["acesso"] is None


def test_acesso_acompanha_a_conta_ligada(client, h, criar_usuario, igreja, novo_membro):
    m = novo_membro()
    u = criar_usuario(igreja, "maria@a.org", perfil=PerfilUsuario.PRESBITERO)
    assert client.patch(f"/usuarios/{u.id}", headers=h, json={"membro_id": m["id"]}).status_code == 200

    esperado = {"id": str(u.id), "email": "maria@a.org", "perfil": "presbitero", "status": "ativo"}
    assert client.get(f"/membros/{m['id']}", headers=h).json()["acesso"] == esperado
    assert client.get("/membros", headers=h).json()["items"][0]["acesso"] == esperado

    client.patch(f"/usuarios/{u.id}", headers=h, json={"membro_id": None})
    assert client.get(f"/membros/{m['id']}", headers=h).json()["acesso"] is None


# ---------- convidar a partir do membro ----------

def test_convite_vinculado_ao_membro(client, h, mailer, novo_membro):
    m = novo_membro(nome="Ana Souza", email="ana@x.org")
    r = client.post("/usuarios", headers=h, json={"email": "Ana@X.org", "membro_id": m["id"]})
    assert r.status_code == 201, r.text
    assert (r.json()["membro_id"], r.json()["status"], r.json()["perfil"]) == (m["id"], "convite_pendente", "usuario")

    assert [e[0] for e in mailer.enviados] == ["ana@x.org"]
    acesso = client.get(f"/membros/{m['id']}", headers=h).json()["acesso"]
    assert (acesso["email"], acesso["status"]) == ("ana@x.org", "convite_pendente")
    assert auditoria("usuario_criado")[0].detalhes["membro"] == "Ana Souza"


def test_convite_vinculado_valida_o_membro(client, auth, criar_igreja, criar_usuario, h, novo_membro):
    m = novo_membro(email="m@x.org")
    assert client.post("/usuarios", headers=h, json={"email": "a@x.org", "membro_id": m["id"]}).status_code == 201
    # já tem acesso
    assert client.post("/usuarios", headers=h, json={"email": "b@x.org", "membro_id": m["id"]}).status_code == 409
    # e-mail em uso
    outro = novo_membro(nome="Outro")
    assert client.post("/usuarios", headers=h, json={"email": "a@x.org", "membro_id": outro["id"]}).status_code == 409
    # inexistente e de outra igreja
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    de_b = client.post("/membros", headers=hb, json={"nome": "De B", "rol": "C"}).json()
    for membro_id in (str(uuid.uuid4()), de_b["id"]):
        assert client.post("/usuarios", headers=h, json={"email": "c@x.org", "membro_id": membro_id}).status_code == 404


def test_nao_convida_membro_fora_do_rol_nem_excluido(client, h, novo_membro):
    saiu = novo_membro(nome="Saiu")
    ev = {"tipo": "saida", "data": "2024-01-01", "ata_conselho": "Ata 1", "situacao_resultante": "transferido"}
    client.post(f"/membros/{saiu['id']}/eventos", headers=h, json=ev)
    assert client.post("/usuarios", headers=h, json={"email": "s@x.org", "membro_id": saiu["id"]}).status_code == 409
    excluido = novo_membro(nome="Errado")
    client.delete(f"/membros/{excluido['id']}", headers=h)
    assert client.post("/usuarios", headers=h, json={"email": "e@x.org", "membro_id": excluido["id"]}).status_code == 404


def test_convite_sem_membro_continua_funcionando(client, h):
    r = client.post("/usuarios", headers=h, json={"email": "solto@x.org", "perfil": "pastor"})
    assert r.status_code == 201 and r.json()["membro_id"] is None


def test_so_admin_convida(client, auth, criar_usuario, igreja, novo_membro):
    m = novo_membro(email="m@x.org")
    for perfil in (PerfilUsuario.PASTOR, PerfilUsuario.PRESBITERO):
        hx = auth(criar_usuario(igreja, f"{perfil.value}@a.org", perfil=perfil))
        assert client.post("/usuarios", headers=hx, json={"email": "z@x.org", "membro_id": m["id"]}).status_code == 403


# ---------- convite em massa ----------

URL = "/usuarios/convites-em-massa"


@pytest.fixture
def rol(client, h, novo_membro, criar_usuario, igreja):
    """3 elegíveis, 1 sem e-mail, 1 com e-mail de outro usuário, 1 com conta, 1 fora do rol."""
    elegiveis = [novo_membro(nome=f"Elegivel {i}", email=f"e{i}@x.org") for i in range(3)]
    sem_email = novo_membro(nome="Sem email")
    usado = novo_membro(nome="Email em uso", email="admin@a.org")  # o e-mail do admin
    com_conta = novo_membro(nome="Ja tem conta", email="ja@x.org")
    u = criar_usuario(igreja, "ja@x.org")
    client.patch(f"/usuarios/{u.id}", headers=h, json={"membro_id": com_conta["id"]})
    fora = novo_membro(nome="Fora do rol", email="fora@x.org")
    ev = {"tipo": "saida", "data": "2024-01-01", "ata_conselho": "Ata 1", "situacao_resultante": "transferido"}
    client.post(f"/membros/{fora['id']}/eventos", headers=h, json=ev)
    return SimpleNamespace(elegiveis=elegiveis, sem_email=sem_email, usado=usado)


def test_simulacao_e_o_padrao_e_nao_cria_nada(client, h, mailer, rol):
    antes = set(contas())
    r = client.post(URL, headers=h, json={})
    assert r.status_code == 200, r.text
    assert r.json() == {"simulacao": True, "elegiveis": 3, "convidados": 0, "restantes": 3,
                        "sem_email": 1, "email_em_uso": 1}
    assert set(contas()) == antes and mailer.enviados == []
    assert not auditoria("convite_em_massa")


def test_convida_os_elegiveis_e_vincula_as_contas(client, h, mailer, rol):
    r = client.post(URL, headers=h, json={"simular": False})
    assert r.status_code == 200, r.text
    assert (r.json()["convidados"], r.json()["restantes"], r.json()["simulacao"]) == (3, 0, False)

    por_email = contas()
    for i, m in enumerate(rol.elegiveis):
        conta = por_email[f"e{i}@x.org"]
        assert (str(conta.membro_id), conta.status.value, conta.perfil) == (m["id"], "convite_pendente", PerfilUsuario.USUARIO)
        assert client.get(f"/membros/{m['id']}", headers=h).json()["acesso"]["status"] == "convite_pendente"
    assert sorted(e[0] for e in mailer.enviados) == ["e0@x.org", "e1@x.org", "e2@x.org"]
    assert auditoria("convite_em_massa")[0].detalhes["convidados"] == 3
    assert len(auditoria("usuario_criado")) == 3

    # os demais não foram tocados
    assert "fora@x.org" not in por_email and rol.sem_email["email"] is None
    # e repetir não convida ninguém de novo
    r = client.post(URL, headers=h, json={"simular": False})
    assert (r.json()["elegiveis"], r.json()["convidados"]) == (0, 0)


def test_limite_por_chamada_e_continuacao(client, h, mailer, rol):
    r = client.post(URL, headers=h, json={"simular": False, "limite": 2})
    assert (r.json()["convidados"], r.json()["restantes"]) == (2, 1)
    r = client.post(URL, headers=h, json={"simular": False, "limite": 2})
    assert (r.json()["convidados"], r.json()["restantes"]) == (1, 0)
    assert len(mailer.enviados) == 3


def test_limite_invalido(client, h):
    assert client.post(URL, headers=h, json={"limite": 0}).status_code == 422
    assert client.post(URL, headers=h, json={"limite": 51}).status_code == 422


def test_membros_com_o_mesmo_email_so_o_primeiro_e_convidado(client, h, mailer, novo_membro):
    novo_membro(nome="Pai", email="familia@x.org")
    novo_membro(nome="Mae", email="familia@x.org")
    r = client.post(URL, headers=h, json={"simular": False})
    assert (r.json()["convidados"], r.json()["email_em_uso"]) == (1, 1)
    assert len(mailer.enviados) == 1


def test_convite_em_massa_so_do_admin_e_da_propria_igreja(client, auth, criar_igreja, criar_usuario, igreja, h, rol, mailer):
    for perfil in (PerfilUsuario.PASTOR, PerfilUsuario.PRESBITERO, PerfilUsuario.USUARIO):
        hx = auth(criar_usuario(igreja, f"{perfil.value}@a.org", perfil=perfil))
        assert client.post(URL, headers=hx, json={"simular": False}).status_code == 403
    assert client.post(URL, json={}).status_code == 401

    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    r = client.post(URL, headers=hb, json={"simular": False})
    assert (r.json()["elegiveis"], r.json()["convidados"]) == (0, 0)  # não enxerga o rol de A
    assert mailer.enviados == []


# ---------- link de convite para copiar ----------

def test_admin_gera_link_de_convite_sem_enviar_email(client, h, mailer):
    u = client.post("/usuarios", headers=h, json={"email": "novo@a.org"}).json()
    enviados = len(mailer.enviados)

    r = client.post(f"/usuarios/{u['id']}/link-convite", headers=h)
    assert r.status_code == 200, r.text
    link = r.json()["link"]
    assert "/redefinir-senha?token=" in link and r.json()["expira_em"]
    assert len(mailer.enviados) == enviados  # nada foi enviado
    assert auditoria("link_convite_gerado")

    # o link funciona e ativa a conta
    token = link.split("token=")[1]
    assert client.post("/auth/redefinir-senha", json={"token": token, "nova_senha": "Senha-Forte-123"}).status_code in (200, 204)


def test_novo_link_invalida_o_anterior(client, h):
    u = client.post("/usuarios", headers=h, json={"email": "novo@a.org"}).json()
    antigo = client.post(f"/usuarios/{u['id']}/link-convite", headers=h).json()["link"].split("token=")[1]
    client.post(f"/usuarios/{u['id']}/link-convite", headers=h)
    r = client.post("/auth/redefinir-senha", json={"token": antigo, "nova_senha": "Senha-Forte-123"})
    assert r.status_code == 400


def test_link_so_para_convite_pendente_e_admin(client, h, admin, auth, criar_usuario, igreja):
    assert client.post(f"/usuarios/{admin.id}/link-convite", headers=h).status_code == 409
    u = client.post("/usuarios", headers=h, json={"email": "novo@a.org"}).json()
    outro = criar_usuario(igreja, "p@a.org", perfil=PerfilUsuario.PRESBITERO)
    assert client.post(f"/usuarios/{u['id']}/link-convite", headers=auth(outro)).status_code == 403
