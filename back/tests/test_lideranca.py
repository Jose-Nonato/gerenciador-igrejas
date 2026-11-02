import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from core.database import SessionLocal
from models import LogAuditoria
from models.enums import PerfilUsuario

ADMIN = PerfilUsuario.ADMIN


def dias_atras(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


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
    def _novo(headers=None, **campos):
        corpo = {"nome": "Maria Silva", "rol": "C", **campos}
        r = client.post("/membros", headers=headers or h, json=corpo)
        assert r.status_code == 201, r.text
        return r.json()

    return _novo


@pytest.fixture
def ump(client, h):
    r = client.post("/sociedades", headers=h, json={"sigla": "UMP"})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def url(ump):
    return f"/sociedades/{ump['id']}/lideranca"


@pytest.fixture
def eleger(client, h, url):
    def _eleger(membro_id, cargo="presidente", headers=None, **extra):
        r = client.post(url, headers=headers or h, json={"membro_id": membro_id, "cargo": cargo, **extra})
        assert r.status_code == 201, r.text
        return r.json()

    return _eleger


def auditoria(acao):
    with SessionLocal() as db:
        return list(db.scalars(select(LogAuditoria).where(LogAuditoria.acao == acao)))


# ---------- permissões ----------

@pytest.mark.parametrize("perfil", [PerfilUsuario.PRESBITERO, PerfilUsuario.USUARIO])
def test_so_admin_e_pastor_acessam_a_lideranca(client, auth, criar_usuario, igreja, url, novo_membro, perfil):
    hx = auth(criar_usuario(igreja, "x@a.org", perfil=perfil))
    m = novo_membro()
    assert client.get(url, headers=hx).status_code == 403
    assert client.post(url, headers=hx, json={"membro_id": m["id"], "cargo": "presidente"}).status_code == 403
    assert client.patch(f"{url}/{uuid.uuid4()}", headers=hx, json={"fim": dias_atras(0)}).status_code == 403


def test_pastor_gerencia_a_lideranca(client, auth, criar_usuario, igreja, url, novo_membro):
    hp = auth(criar_usuario(igreja, "pastor@a.org", perfil=PerfilUsuario.PASTOR))
    m = novo_membro()
    assert client.post(url, headers=hp, json={"membro_id": m["id"], "cargo": "tesoureiro"}).status_code == 201


def test_lideranca_exige_autenticacao(client, url):
    assert client.get(url).status_code == 401


# ---------- eleger ----------

def test_eleger_lider_em_exercicio(client, h, url, novo_membro, eleger):
    m = novo_membro(nome="Ana Presidente")
    r = eleger(m["id"], "presidente")
    assert (r["nome"], r["cargo"], r["fim"], r["cargo_descricao"]) == ("Ana Presidente", "presidente", None, None)
    assert r["inicio"] == date.today().isoformat()

    lista = client.get(url, headers=h).json()
    assert [(x["nome"], x["cargo"]) for x in lista] == [("Ana Presidente", "presidente")]
    assert len(auditoria("lideranca_adicionada")) == 1


def test_inicio_pode_ser_informado_mas_nao_no_futuro(client, h, url, novo_membro, eleger):
    m = novo_membro()
    assert eleger(m["id"], inicio=dias_atras(40))["inicio"] == dias_atras(40)
    futuro = (date.today() + timedelta(days=1)).isoformat()
    r = client.post(url, headers=h, json={"membro_id": m["id"], "cargo": "tesoureiro", "inicio": futuro})
    assert r.status_code == 422


@pytest.mark.parametrize("cargo", ["presidente", "vice_presidente", "secretario", "tesoureiro"])
def test_cargos_unicos_tem_um_ocupante_em_exercicio(client, h, url, novo_membro, eleger, cargo):
    a, b = novo_membro(nome="A"), novo_membro(nome="B")
    eleger(a["id"], cargo)
    r = client.post(url, headers=h, json={"membro_id": b["id"], "cargo": cargo})
    assert r.status_code == 409
    assert "encerre o mandato" in r.json()["detail"]


def test_substituir_o_ocupante_exige_encerrar_o_mandato_antes(client, h, url, novo_membro, eleger):
    a, b = novo_membro(nome="A"), novo_membro(nome="B")
    atual = eleger(a["id"], "presidente", inicio=dias_atras(30))
    assert client.patch(f"{url}/{atual['id']}", headers=h, json={"fim": dias_atras(0)}).status_code == 200
    eleger(b["id"], "presidente")

    em_exercicio = client.get(url, headers=h).json()
    assert [x["nome"] for x in em_exercicio] == ["B"]
    todos = client.get(f"{url}?incluir_encerrados=true", headers=h).json()
    assert [x["nome"] for x in todos] == ["B", "A"]  # em exercício primeiro
    assert todos[1]["fim"] == dias_atras(0)


def test_o_mesmo_membro_pode_ter_cargos_diferentes_e_voltar_ao_cargo(client, h, url, novo_membro, eleger):
    m = novo_membro()
    eleger(m["id"], "presidente")
    eleger(m["id"], "tesoureiro")
    antigo = client.get(url, headers=h).json()[0]
    client.patch(f"{url}/{antigo['id']}", headers=h, json={"fim": dias_atras(0)})
    eleger(m["id"], antigo["cargo"])  # novo mandato, o histórico antigo permanece


def test_conselheiro_admite_varios_mas_nao_o_mesmo_membro_duas_vezes(client, h, url, novo_membro, eleger):
    a, b = novo_membro(nome="A"), novo_membro(nome="B")
    eleger(a["id"], "conselheiro")
    eleger(b["id"], "conselheiro")
    assert client.post(url, headers=h, json={"membro_id": a["id"], "cargo": "conselheiro"}).status_code == 409
    assert len(client.get(url, headers=h).json()) == 2


def test_cargo_outro_exige_descricao_e_so_ele_a_aceita(client, h, url, novo_membro, eleger):
    m = novo_membro()
    base = {"membro_id": m["id"]}
    assert client.post(url, headers=h, json={**base, "cargo": "outro"}).status_code == 422
    assert client.post(url, headers=h, json={**base, "cargo": "outro", "cargo_descricao": "   "}).status_code == 422
    assert client.post(url, headers=h, json={**base, "cargo": "presidente", "cargo_descricao": "X"}).status_code == 422

    r = eleger(m["id"], "outro", cargo_descricao="  Diretor de música ")
    assert r["cargo_descricao"] == "Diretor de música"
    # a mesma pessoa pode ter outro cargo "outro" com descrição diferente, mas não a mesma
    eleger(m["id"], "outro", cargo_descricao="Diretor de esportes")
    repetido = client.post(url, headers=h, json={**base, "cargo": "outro", "cargo_descricao": "DIRETOR DE MÚSICA"})
    assert repetido.status_code == 409


def test_cargo_invalido_e_dados_ausentes(client, h, url, novo_membro):
    m = novo_membro()
    assert client.post(url, headers=h, json={"membro_id": m["id"], "cargo": "rei"}).status_code == 422
    assert client.post(url, headers=h, json={"cargo": "presidente"}).status_code == 422
    assert client.post(url, headers=h, json={"membro_id": m["id"]}).status_code == 422


def test_lider_nao_precisa_ser_socio(client, h, url, novo_membro, eleger):
    eleger(novo_membro()["id"], "conselheiro")  # o membro nunca foi cadastrado como sócio


# ---------- membro ----------

def test_membro_de_outra_igreja_ou_inexistente_da_404(client, auth, criar_igreja, criar_usuario, h, url):
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    de_b = client.post("/membros", headers=hb, json={"nome": "De B", "rol": "C"}).json()
    for membro_id in (de_b["id"], str(uuid.uuid4())):
        assert client.post(url, headers=h, json={"membro_id": membro_id, "cargo": "presidente"}).status_code == 404


def test_membro_que_saiu_do_rol_nao_pode_ser_lider(client, h, url, novo_membro):
    m = novo_membro()
    ev = {"tipo": "saida", "data": dias_atras(1), "ata_conselho": "Ata 1", "situacao_resultante": "falecido"}
    assert client.post(f"/membros/{m['id']}/eventos", headers=h, json=ev).status_code == 201
    assert client.post(url, headers=h, json={"membro_id": m["id"], "cargo": "presidente"}).status_code == 409


def test_membro_excluido_logicamente_some_da_lideranca(client, h, url, novo_membro, eleger):
    m = novo_membro(nome="Cadastro Errado")
    eleger(m["id"], "presidente")
    assert client.delete(f"/membros/{m['id']}", headers=h).status_code == 204
    assert client.get(f"{url}?incluir_encerrados=true", headers=h).json() == []
    assert client.post(url, headers=h, json={"membro_id": m["id"], "cargo": "tesoureiro"}).status_code == 404


# ---------- encerrar e corrigir ----------

def test_encerrar_mandato_audita_e_mantem_o_registro(client, h, url, novo_membro, eleger):
    r = eleger(novo_membro()["id"], "secretario", inicio=dias_atras(10))
    out = client.patch(f"{url}/{r['id']}", headers=h, json={"fim": dias_atras(2)})
    assert out.status_code == 200 and out.json()["fim"] == dias_atras(2)
    assert client.get(url, headers=h).json() == []
    assert len(auditoria("lideranca_encerrada")) == 1


def test_corrigir_a_data_de_inicio_audita_como_alteracao(client, h, url, novo_membro, eleger):
    r = eleger(novo_membro()["id"], "presidente", inicio=dias_atras(5))
    out = client.patch(f"{url}/{r['id']}", headers=h, json={"inicio": dias_atras(20)})
    assert out.json()["inicio"] == dias_atras(20)
    assert len(auditoria("lideranca_alterada")) == 1 and not auditoria("lideranca_encerrada")


def test_datas_invalidas_na_atualizacao(client, h, url, novo_membro, eleger):
    r = eleger(novo_membro()["id"], "presidente", inicio=dias_atras(5))
    alvo = f"{url}/{r['id']}"
    assert client.patch(alvo, headers=h, json={"fim": dias_atras(9)}).status_code == 400  # fim antes do início
    assert client.patch(alvo, headers=h, json={"inicio": dias_atras(0), "fim": dias_atras(1)}).status_code == 400
    assert client.patch(alvo, headers=h, json={"fim": (date.today() + timedelta(days=1)).isoformat()}).status_code == 422
    assert client.patch(alvo, headers=h, json={}).status_code == 422
    assert client.patch(f"{url}/{uuid.uuid4()}", headers=h, json={"fim": dias_atras(0)}).status_code == 404


# ---------- isolamento ----------

def test_lideranca_de_outra_igreja_ou_sociedade_nao_e_acessivel(client, auth, criar_igreja, criar_usuario, h, url, ump, novo_membro, eleger):
    r = eleger(novo_membro()["id"], "presidente")
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    assert client.get(url, headers=hb).status_code == 404
    assert client.patch(f"{url}/{r['id']}", headers=hb, json={"fim": dias_atras(0)}).status_code == 404

    outra = client.post("/sociedades", headers=h, json={"sigla": "UPA"}).json()
    assert client.patch(f"/sociedades/{outra['id']}/lideranca/{r['id']}", headers=h, json={"fim": dias_atras(0)}).status_code == 404
    # o mesmo cargo único pode ser ocupado em outra sociedade
    assert client.post(f"/sociedades/{outra['id']}/lideranca", headers=h,
                       json={"membro_id": novo_membro(nome="Outro")["id"], "cargo": "presidente"}).status_code == 201


def test_sociedade_inexistente_da_404(client, h):
    assert client.get(f"/sociedades/{uuid.uuid4()}/lideranca", headers=h).status_code == 404
