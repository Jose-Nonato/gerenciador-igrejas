import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

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
    def _novo(**campos):
        r = client.post("/membros", headers=h, json={"nome": "Maria Silva", "rol": "C", **campos})
        assert r.status_code == 201, r.text
        return r.json()

    return _novo


@pytest.fixture
def sociedades(client, h):
    """UMP e UCP da igreja A."""
    return {
        sigla: client.post("/sociedades", headers=h, json={"sigla": sigla}).json()
        for sigla in ("UMP", "UCP")
    }


@pytest.fixture
def lider(client, auth, h, igreja, criar_usuario, novo_membro, sociedades):
    """Usuário ligado a um membro que está na diretoria da UMP."""

    def _lider(perfil=PerfilUsuario.USUARIO, cargo="presidente", sigla="UMP", email="lider@a.org"):
        membro = novo_membro(nome=f"Líder {email}")
        usuario = criar_usuario(igreja, email, perfil=perfil)
        r = client.patch(f"/usuarios/{usuario.id}", headers=h, json={"membro_id": membro["id"]})
        assert r.status_code == 200, r.text
        r = client.post(
            f"/sociedades/{sociedades[sigla]['id']}/lideranca",
            headers=h,
            json={"membro_id": membro["id"], "cargo": cargo},
        )
        assert r.status_code == 201, r.text
        return SimpleNamespace(usuario=usuario, membro=membro, lideranca=r.json(), h=auth(usuario))

    return _lider


# ---------- o líder vê só a sua sociedade ----------

def test_lider_lista_so_a_propria_sociedade(client, lider, sociedades):
    L = lider()
    lista = client.get("/sociedades", headers=L.h).json()
    assert [s["sigla"] for s in lista] == ["UMP"]
    assert client.get(f"/sociedades/{sociedades['UMP']['id']}", headers=L.h).status_code == 200


def test_lider_nao_acessa_outra_sociedade(client, lider, sociedades):
    L = lider()
    ucp = sociedades["UCP"]["id"]
    chamadas = [
        ("get", f"/sociedades/{ucp}", None),
        ("get", f"/sociedades/{ucp}/socios", None),
        ("get", f"/sociedades/{ucp}/lideranca", None),
        ("get", f"/sociedades/{ucp}/reunioes", None),
        ("get", f"/sociedades/{ucp}/frequencia", None),
        ("get", f"/sociedades/{ucp}/membros?q=ma", None),
        ("post", f"/sociedades/{ucp}/socios", {"tipo": "nao_membro", "nome_externo": "X"}),
        ("post", f"/sociedades/{ucp}/reunioes", {"data": dias_atras(1)}),
    ]
    for metodo, caminho, corpo in chamadas:
        r = client.request(metodo, caminho, headers=L.h, json=corpo)
        assert r.status_code == 403, (metodo, caminho, r.status_code)


def test_usuario_sem_lideranca_ve_lista_vazia_e_nao_acessa(client, auth, criar_usuario, igreja, sociedades):
    hx = auth(criar_usuario(igreja, "comum@a.org", perfil=PerfilUsuario.USUARIO))
    assert client.get("/sociedades", headers=hx).json() == []
    assert client.get(f"/sociedades/{sociedades['UMP']['id']}", headers=hx).status_code == 403


def test_usuario_com_membro_mas_sem_cargo_nao_acessa(client, auth, h, criar_usuario, igreja, novo_membro, sociedades):
    membro = novo_membro()
    u = criar_usuario(igreja, "so-membro@a.org", perfil=PerfilUsuario.USUARIO)
    client.patch(f"/usuarios/{u.id}", headers=h, json={"membro_id": membro["id"]})
    assert client.get(f"/sociedades/{sociedades['UMP']['id']}", headers=auth(u)).status_code == 403


def test_sociedade_inexistente_continua_404_para_o_lider(client, lider):
    L = lider()
    assert client.get(f"/sociedades/{uuid.uuid4()}", headers=L.h).status_code == 404


# ---------- o líder edita a sua sociedade ----------

def test_lider_gerencia_socios(client, lider, novo_membro, sociedades):
    L = lider()
    base = f"/sociedades/{sociedades['UMP']['id']}"
    m = novo_membro(nome="Novo Sócio")

    r = client.post(f"{base}/socios", headers=L.h, json={"tipo": "ativo", "membro_id": m["id"]})
    assert r.status_code == 201, r.text
    socio = r.json()
    assert client.get(f"{base}/socios", headers=L.h).json()[0]["nome"] == "Novo Sócio"
    assert client.patch(f"{base}/socios/{socio['id']}", headers=L.h, json={"tipo": "cooperador"}).status_code == 200
    assert client.delete(f"{base}/socios/{socio['id']}", headers=L.h).status_code == 204


def test_lider_registra_reuniao_presenca_e_ve_a_frequencia(client, lider, novo_membro, sociedades):
    L = lider()
    base = f"/sociedades/{sociedades['UMP']['id']}"
    socio = client.post(
        f"{base}/socios", headers=L.h, json={"tipo": "ativo", "membro_id": novo_membro()["id"]}
    ).json()

    r = client.post(
        f"{base}/reunioes",
        headers=L.h,
        json={"data": dias_atras(2), "presencas": [{"socio_id": socio["id"], "status": "P"}]},
    )
    assert r.status_code == 201, r.text
    reuniao = r.json()
    r = client.put(
        f"{base}/reunioes/{reuniao['id']}/presencas",
        headers=L.h,
        json={"presencas": [{"socio_id": socio["id"], "status": "A"}]},
    )
    assert r.status_code == 200 and r.json()["ausentes"] == 1
    assert client.patch(f"{base}/reunioes/{reuniao['id']}", headers=L.h, json={"tema": "Novo tema"}).status_code == 200
    assert client.get(f"{base}/frequencia", headers=L.h).json()["total_reunioes"] == 1


@pytest.mark.parametrize("cargo", ["presidente", "vice_presidente", "secretario", "tesoureiro", "conselheiro"])
def test_qualquer_cargo_em_exercicio_da_acesso(client, lider, sociedades, cargo):
    L = lider(cargo=cargo)
    assert client.get(f"/sociedades/{sociedades['UMP']['id']}/socios", headers=L.h).status_code == 200


def test_presbitero_lider_tambem_acessa_so_a_sua(client, lider, sociedades):
    L = lider(perfil=PerfilUsuario.PRESBITERO)
    assert client.get(f"/sociedades/{sociedades['UMP']['id']}", headers=L.h).status_code == 200
    assert client.get(f"/sociedades/{sociedades['UCP']['id']}", headers=L.h).status_code == 403


# ---------- o que o líder NÃO faz ----------

def test_lider_nao_cria_sociedade_nem_muda_o_nome(client, lider, sociedades):
    L = lider()
    assert client.post("/sociedades", headers=L.h, json={"sigla": "SAF"}).status_code == 403
    assert client.patch(f"/sociedades/{sociedades['UMP']['id']}", headers=L.h, json={"nome": "X"}).status_code == 403


def test_lider_ve_mas_nao_altera_a_diretoria(client, lider, novo_membro, sociedades):
    L = lider()
    base = f"/sociedades/{sociedades['UMP']['id']}/lideranca"
    lista = client.get(base, headers=L.h)
    assert lista.status_code == 200 and [x["cargo"] for x in lista.json()] == ["presidente"]

    outro = novo_membro(nome="Outro")
    assert client.post(base, headers=L.h, json={"membro_id": outro["id"], "cargo": "tesoureiro"}).status_code == 403
    assert client.patch(f"{base}/{L.lideranca['id']}", headers=L.h, json={"fim": dias_atras(0)}).status_code == 403
    assert client.get(base, headers=L.h).json()[0]["fim"] is None  # continua no cargo


def test_lider_nao_acessa_o_resto_do_sistema(client, lider, novo_membro):
    L = lider()
    m = novo_membro()
    assert client.get("/membros", headers=L.h).status_code == 403
    assert client.get(f"/membros/{m['id']}", headers=L.h).status_code == 403
    assert client.get("/usuarios", headers=L.h).status_code == 403
    assert client.get("/familias", headers=L.h).status_code == 403


# ---------- o acesso acompanha o mandato ----------

def test_acesso_termina_quando_o_mandato_e_encerrado(client, lider, h, sociedades):
    L = lider()
    sid = sociedades["UMP"]["id"]
    assert client.get(f"/sociedades/{sid}/socios", headers=L.h).status_code == 200

    r = client.patch(f"/sociedades/{sid}/lideranca/{L.lideranca['id']}", headers=h, json={"fim": dias_atras(0)})
    assert r.status_code == 200
    assert client.get(f"/sociedades/{sid}/socios", headers=L.h).status_code == 403
    assert client.get("/sociedades", headers=L.h).json() == []


def test_acesso_acaba_se_o_usuario_for_desvinculado_do_membro(client, lider, h, sociedades):
    L = lider()
    sid = sociedades["UMP"]["id"]
    r = client.patch(f"/usuarios/{L.usuario.id}", headers=h, json={"membro_id": None})
    assert r.status_code == 200
    assert client.get(f"/sociedades/{sid}", headers=L.h).status_code == 403


def test_admin_de_outra_igreja_nao_ve_a_sociedade_desta(client, auth, criar_igreja, criar_usuario, sociedades):
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    assert client.get(f"/sociedades/{sociedades['UMP']['id']}", headers=hb).status_code == 404


# ---------- busca restrita de membros ----------

def test_lider_busca_membros_com_dados_minimos(client, lider, novo_membro, sociedades):
    L = lider()
    novo_membro(nome="Beatriz Santos", telefone="11999990000", email="b@x.org", endereco="Rua A")
    r = client.get(f"/sociedades/{sociedades['UMP']['id']}/membros", params={"q": "beatriz"}, headers=L.h)
    assert r.status_code == 200
    achado = r.json()
    assert [m["nome"] for m in achado] == ["Beatriz Santos"]
    assert set(achado[0]) == {"id", "nome", "numero_rol"}  # sem telefone, e-mail, endereço…


def test_busca_exclui_quem_saiu_do_rol_e_excluidos(client, h, lider, novo_membro, sociedades):
    L = lider()
    saiu = novo_membro(nome="Zé Transferido")
    ev = {"tipo": "saida", "data": dias_atras(1), "ata_conselho": "Ata 1", "situacao_resultante": "transferido"}
    client.post(f"/membros/{saiu['id']}/eventos", headers=h, json=ev)
    excluido = novo_membro(nome="Zé Excluído Logicamente")
    client.delete(f"/membros/{excluido['id']}", headers=h)
    novo_membro(nome="Zé Ativo")

    r = client.get(f"/sociedades/{sociedades['UMP']['id']}/membros", params={"q": "zé"}, headers=L.h)
    assert [m["nome"] for m in r.json()] == ["Zé Ativo"]


def test_busca_exige_dois_caracteres_e_acesso_a_sociedade(client, lider, auth, criar_usuario, igreja, sociedades):
    L = lider()
    url = f"/sociedades/{sociedades['UMP']['id']}/membros"
    assert client.get(url, params={"q": "a"}, headers=L.h).status_code == 422
    assert client.get(url, headers=L.h).status_code == 422
    quem = auth(criar_usuario(igreja, "sem-acesso@a.org", perfil=PerfilUsuario.USUARIO))
    assert client.get(url, params={"q": "ab"}, headers=quem).status_code == 403


def test_admin_e_pastor_tambem_usam_a_busca(client, auth, h, criar_usuario, igreja, novo_membro, sociedades):
    novo_membro(nome="Carla Dias")
    url = f"/sociedades/{sociedades['UMP']['id']}/membros"
    assert client.get(url, params={"q": "carla"}, headers=h).json()[0]["nome"] == "Carla Dias"
    pastor = auth(criar_usuario(igreja, "pastor@a.org", perfil=PerfilUsuario.PASTOR))
    assert client.get(url, params={"q": "carla"}, headers=pastor).status_code == 200


# ---------- troca de senha obrigatória ----------

def test_lider_com_troca_de_senha_pendente_fica_bloqueado(client, login, h, criar_usuario, igreja, novo_membro, sociedades):
    membro = novo_membro()
    u = criar_usuario(igreja, "novo@a.org", perfil=PerfilUsuario.USUARIO, troca_obrigatoria=True)
    client.patch(f"/usuarios/{u.id}", headers=h, json={"membro_id": membro["id"]})
    client.post(
        f"/sociedades/{sociedades['UMP']['id']}/lideranca",
        headers=h,
        json={"membro_id": membro["id"], "cargo": "presidente"},
    )
    tokens = login(u).json()
    hx = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert client.get("/sociedades", headers=hx).status_code == 403
