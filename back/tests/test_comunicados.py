import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from core.database import SessionLocal
from models import Comunicado, LogAuditoria
from models.enums import PerfilUsuario

ADMIN = PerfilUsuario.ADMIN


def agora() -> datetime:
    return datetime.now(timezone.utc)


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
def conta(client, auth, h, igreja, criar_usuario, novo_membro):
    """Cria um usuário; com `membro`, também um membro ligado a ele."""
    contador = iter(range(1000))

    def _conta(perfil=PerfilUsuario.USUARIO, membro=None):
        n = next(contador)
        u = criar_usuario(igreja, f"u{n}@a.org", perfil=perfil)
        m = None
        if membro is not None:
            m = novo_membro(**{"nome": f"Membro {n}", **membro})
            r = client.patch(f"/usuarios/{u.id}", headers=h, json={"membro_id": m["id"]})
            assert r.status_code == 200, r.text
        return SimpleNamespace(usuario=u, membro=m, h=auth(u))

    return _conta


@pytest.fixture
def sociedades(client, h):
    return {s: client.post("/sociedades", headers=h, json={"sigla": s}).json() for s in ("UMP", "UCP")}


@pytest.fixture
def criar(client, h):
    def _criar(headers=None, esperado=201, **campos):
        corpo = {"titulo": "Culto especial", "corpo": "Domingo às 19h.", "categoria": "aviso",
                 "publico": "igreja", **campos}
        r = client.post("/comunicados", headers=headers or h, json=corpo)
        assert r.status_code == esperado, r.text
        return r.json()

    return _criar


@pytest.fixture
def publicado(client, h, criar):
    def _pub(headers=None, **campos):
        c = criar(**campos)
        r = client.post(f"/comunicados/{c['id']}/publicar", headers=headers or h, json={})
        assert r.status_code == 200, r.text
        return r.json()

    return _pub


def ids(resposta):
    return [c["id"] for c in resposta.json()["items"]]


def auditoria(acao):
    with SessionLocal() as db:
        return list(db.scalars(select(LogAuditoria).where(LogAuditoria.acao == acao)))


# ---------- quem escreve ----------

def test_admin_e_pastor_escrevem_para_qualquer_publico(client, conta, criar, sociedades):
    pastor = conta(PerfilUsuario.PASTOR)
    for publico in ("igreja", "comungantes", "oficiais", "professores_ebd"):
        criar(headers=pastor.h, publico=publico)
    criar(headers=pastor.h, publico="sociedade", sociedade_id=sociedades["UMP"]["id"])


@pytest.mark.parametrize("perfil", [PerfilUsuario.PRESBITERO, PerfilUsuario.USUARIO])
def test_quem_nao_e_gestor_nem_lider_nao_escreve(client, conta, criar, perfil):
    x = conta(perfil, membro={})
    criar(headers=x.h, esperado=403)
    assert client.get("/comunicados/gerenciar", headers=x.h).status_code == 403


def test_comunicados_exigem_autenticacao(client):
    assert client.get("/comunicados").status_code == 401
    assert client.post("/comunicados", json={}).status_code == 401


# ---------- ciclo de vida ----------

def test_ciclo_rascunho_publicar_despublicar(client, h, conta, criar):
    leitor = conta(PerfilUsuario.USUARIO)
    c = criar(titulo="  Aviso importante  ")
    assert (c["status"], c["titulo"], c["data_publicacao"]) == ("rascunho", "Aviso importante", None)
    # rascunho: só quem gerencia vê
    assert ids(client.get("/comunicados", headers=leitor.h)) == []
    assert client.get(f"/comunicados/{c['id']}", headers=leitor.h).status_code == 404
    assert client.get(f"/comunicados/{c['id']}", headers=h).status_code == 200

    r = client.post(f"/comunicados/{c['id']}/publicar", headers=h, json={})
    assert r.status_code == 200 and r.json()["status"] == "publicado" and r.json()["data_publicacao"]
    assert ids(client.get("/comunicados", headers=leitor.h)) == [c["id"]]
    assert client.get(f"/comunicados/{c['id']}", headers=leitor.h).status_code == 200

    assert client.post(f"/comunicados/{c['id']}/publicar", headers=h, json={}).status_code == 409
    r = client.post(f"/comunicados/{c['id']}/despublicar", headers=h)
    assert r.status_code == 200 and r.json()["status"] == "rascunho" and r.json()["data_publicacao"] is None
    assert ids(client.get("/comunicados", headers=leitor.h)) == []
    assert client.post(f"/comunicados/{c['id']}/despublicar", headers=h).status_code == 409


def test_agendar_e_a_hora_chegar(client, h, conta, criar):
    leitor = conta(PerfilUsuario.USUARIO)
    c = criar()
    futuro = (agora() + timedelta(days=2)).isoformat()
    r = client.post(f"/comunicados/{c['id']}/publicar", headers=h, json={"quando": futuro})
    assert r.status_code == 200 and r.json()["status"] == "agendado"
    assert ids(client.get("/comunicados", headers=leitor.h)) == []
    assert ids(client.get("/comunicados/gerenciar?status=agendado", headers=h)) == [c["id"]]

    # a hora chega: sem tarefa em segundo plano, passa a valer como publicado nas consultas
    with SessionLocal() as db:
        db.get(Comunicado, uuid.UUID(c["id"])).publicar_em = agora() - timedelta(minutes=1)
        db.commit()
    assert ids(client.get("/comunicados", headers=leitor.h)) == [c["id"]]
    assert client.get(f"/comunicados/{c['id']}", headers=h).json()["status"] == "publicado"
    assert ids(client.get("/comunicados/gerenciar?status=publicado", headers=h)) == [c["id"]]
    assert ids(client.get("/comunicados/gerenciar?status=agendado", headers=h)) == []
    assert client.post(f"/comunicados/{c['id']}/publicar", headers=h, json={}).status_code == 409


def test_cancelar_agendamento_volta_para_rascunho(client, h, criar):
    c = criar()
    futuro = (agora() + timedelta(days=1)).isoformat()
    client.post(f"/comunicados/{c['id']}/publicar", headers=h, json={"quando": futuro})
    r = client.post(f"/comunicados/{c['id']}/despublicar", headers=h)
    assert r.json()["status"] == "rascunho" and r.json()["publicar_em"] is None


def test_reagendar_um_comunicado_agendado(client, h, criar):
    c = criar()
    for dias in (1, 3):
        r = client.post(f"/comunicados/{c['id']}/publicar", headers=h,
                        json={"quando": (agora() + timedelta(days=dias)).isoformat()})
        assert r.status_code == 200 and r.json()["status"] == "agendado"


def test_data_no_passado_publica_na_hora_e_sem_fuso_vale_utc(client, h, criar):
    a, b = criar(), criar(titulo="Outro")
    passado = (agora() - timedelta(days=3)).isoformat()
    assert client.post(f"/comunicados/{a['id']}/publicar", headers=h, json={"quando": passado}).json()["status"] == "publicado"
    sem_fuso = (agora() + timedelta(days=1)).replace(tzinfo=None, microsecond=0).isoformat()
    assert client.post(f"/comunicados/{b['id']}/publicar", headers=h, json={"quando": sem_fuso}).json()["status"] == "agendado"


def test_excluir_e_logico_e_audita(client, h, conta, criar, publicado):
    leitor = conta(PerfilUsuario.USUARIO)
    c = publicado(titulo="Errado")
    assert client.delete(f"/comunicados/{c['id']}", headers=h).status_code == 204
    assert client.get(f"/comunicados/{c['id']}", headers=h).status_code == 404
    assert client.delete(f"/comunicados/{c['id']}", headers=h).status_code == 404
    assert ids(client.get("/comunicados", headers=leitor.h)) == []
    assert ids(client.get("/comunicados/gerenciar", headers=h)) == []
    with SessionLocal() as db:
        assert db.get(Comunicado, uuid.UUID(c["id"])).excluido_em is not None
    assert auditoria("comunicado_excluido")[0].detalhes["titulo"] == "Errado"


def test_auditoria_do_ciclo(client, h, criar):
    c = criar()
    client.patch(f"/comunicados/{c['id']}", headers=h, json={"titulo": "Novo"})
    client.post(f"/comunicados/{c['id']}/publicar", headers=h, json={})
    client.post(f"/comunicados/{c['id']}/despublicar", headers=h)
    client.post(f"/comunicados/{c['id']}/publicar", headers=h,
                json={"quando": (agora() + timedelta(days=1)).isoformat()})
    for acao in ("comunicado_criado", "comunicado_alterado", "comunicado_publicado",
                 "comunicado_despublicado", "comunicado_agendado"):
        assert len(auditoria(acao)) == 1, acao


def test_editar_comunicado_publicado(client, h, publicado):
    c = publicado()
    r = client.patch(f"/comunicados/{c['id']}", headers=h, json={"corpo": "Horário mudou.", "categoria": "evento"})
    assert r.status_code == 200
    assert (r.json()["corpo"], r.json()["categoria"], r.json()["status"]) == ("Horário mudou.", "evento", "publicado")


# ---------- validação ----------

@pytest.mark.parametrize(
    "campos",
    [
        {"titulo": "   "},
        {"corpo": ""},
        {"titulo": "x" * 201},
        {"categoria": "outra"},
        {"publico": "todos"},
        {"publico": "sociedade"},  # falta a sociedade
        {"publico": "igreja", "sociedade_id": str(uuid.uuid4())},  # sociedade onde não cabe
    ],
)
def test_dados_invalidos(client, h, campos):
    corpo = {"titulo": "T", "corpo": "C", "categoria": "aviso", "publico": "igreja", **campos}
    assert client.post("/comunicados", headers=h, json=corpo).status_code == 422


def test_sociedade_de_outra_igreja_ou_inexistente_da_404(client, auth, criar_igreja, criar_usuario, h):
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    de_b = client.post("/sociedades", headers=hb, json={"sigla": "UMP"}).json()
    for sid in (de_b["id"], str(uuid.uuid4())):
        r = client.post("/comunicados", headers=h, json={
            "titulo": "T", "corpo": "C", "categoria": "aviso", "publico": "sociedade", "sociedade_id": sid})
        assert r.status_code == 404


def test_atualizacao_parcial_e_regras_de_publico(client, h, criar, sociedades):
    ump = sociedades["UMP"]["id"]
    c = criar(publico="sociedade", sociedade_id=ump)
    assert client.patch(f"/comunicados/{c['id']}", headers=h, json={}).status_code == 422
    assert client.patch(f"/comunicados/{c['id']}", headers=h, json={"titulo": None}).status_code == 422
    # sair de "sociedade" limpa a sociedade
    r = client.patch(f"/comunicados/{c['id']}", headers=h, json={"publico": "igreja"})
    assert (r.json()["publico"], r.json()["sociedade_id"]) == ("igreja", None)
    # voltar para "sociedade" exige informar qual
    assert client.patch(f"/comunicados/{c['id']}", headers=h, json={"publico": "sociedade"}).status_code == 400
    r = client.patch(f"/comunicados/{c['id']}", headers=h, json={"publico": "sociedade", "sociedade_id": ump})
    assert r.status_code == 200 and r.json()["sociedade_sigla"] == "UMP"


# ---------- quem lê o quê ----------

def test_publico_igreja_vale_para_qualquer_usuario(client, conta, publicado):
    c = publicado(publico="igreja")
    for perfil in (PerfilUsuario.USUARIO, PerfilUsuario.PRESBITERO):
        assert ids(client.get("/comunicados", headers=conta(perfil).h)) == [c["id"]]


def test_publico_comungantes(client, conta, publicado):
    c = publicado(publico="comungantes")
    assert ids(client.get("/comunicados", headers=conta(membro={"rol": "C"}).h)) == [c["id"]]
    assert ids(client.get("/comunicados", headers=conta(membro={"rol": "NC"}).h)) == []
    assert ids(client.get("/comunicados", headers=conta().h)) == []  # sem membro ligado


def test_comungante_fora_do_rol_nao_le_comunicado_de_comungantes(client, h, conta, publicado):
    c = publicado(publico="comungantes")
    leitor = conta(membro={"rol": "C"})
    assert ids(client.get("/comunicados", headers=leitor.h)) == [c["id"]]
    ev = {"tipo": "saida", "data": "2024-01-01", "ata_conselho": "Ata 1", "situacao_resultante": "transferido"}
    assert client.post(f"/membros/{leitor.membro['id']}/eventos", headers=h, json=ev).status_code == 201
    assert ids(client.get("/comunicados", headers=leitor.h)) == []


def test_publico_oficiais(client, conta, publicado):
    c = publicado(publico="oficiais")
    assert ids(client.get("/comunicados", headers=conta(PerfilUsuario.PRESBITERO).h)) == [c["id"]]
    assert ids(client.get("/comunicados", headers=conta(membro={"oficio": "presbitero"}).h)) == [c["id"]]
    assert ids(client.get("/comunicados", headers=conta(membro={"oficio": "diacono"}).h)) == [c["id"]]
    assert ids(client.get("/comunicados", headers=conta(membro={"rol": "C"}).h)) == []
    assert ids(client.get("/comunicados", headers=conta().h)) == []


def test_publico_sociedade_so_para_socios_e_lideres(client, h, conta, publicado, sociedades):
    ump = sociedades["UMP"]["id"]
    c = publicado(publico="sociedade", sociedade_id=ump)

    socio = conta(membro={})
    client.post(f"/sociedades/{ump}/socios", headers=h, json={"tipo": "ativo", "membro_id": socio.membro["id"]})
    cooperador = conta(membro={})
    client.post(f"/sociedades/{ump}/socios", headers=h, json={"tipo": "cooperador", "membro_id": cooperador.membro["id"]})
    lider = conta(membro={})
    client.post(f"/sociedades/{ump}/lideranca", headers=h, json={"membro_id": lider.membro["id"], "cargo": "tesoureiro"})
    de_outra = conta(membro={})
    client.post(f"/sociedades/{sociedades['UCP']['id']}/socios", headers=h,
                json={"tipo": "ativo", "membro_id": de_outra.membro["id"]})

    for quem in (socio, cooperador, lider):
        assert ids(client.get("/comunicados", headers=quem.h)) == [c["id"]]
    assert ids(client.get("/comunicados", headers=de_outra.h)) == []
    assert ids(client.get("/comunicados", headers=conta(membro={}).h)) == []

    # quem saiu da sociedade deixa de ler
    socios = client.get(f"/sociedades/{ump}/socios", headers=h).json()
    s = next(x for x in socios if x["membro_id"] == socio.membro["id"])
    client.delete(f"/sociedades/{ump}/socios/{s['id']}", headers=h)
    assert ids(client.get("/comunicados", headers=socio.h)) == []


def test_publico_ebd_so_admin_e_pastor_veem(client, h, conta, publicado, sociedades):
    c = publicado(publico="professores_ebd")
    assert ids(client.get("/comunicados", headers=h)) == [c["id"]]
    assert ids(client.get("/comunicados", headers=conta(PerfilUsuario.PASTOR).h)) == [c["id"]]
    for quem in (conta(PerfilUsuario.PRESBITERO, membro={"oficio": "presbitero"}), conta(membro={"rol": "C"})):
        assert ids(client.get("/comunicados", headers=quem.h)) == []
        assert client.get(f"/comunicados/{c['id']}", headers=quem.h).status_code == 404


def test_admin_ve_publicados_de_todos_os_publicos(client, h, publicado, sociedades):
    publicado(publico="comungantes")
    publicado(publico="oficiais")
    publicado(publico="sociedade", sociedade_id=sociedades["UMP"]["id"])
    assert client.get("/comunicados", headers=h).json()["total"] == 3


def test_detalhe_de_comunicado_fora_do_publico_da_404(client, conta, publicado):
    c = publicado(publico="oficiais")
    assert client.get(f"/comunicados/{c['id']}", headers=conta(membro={"rol": "C"}).h).status_code == 404
    assert client.get(f"/comunicados/{uuid.uuid4()}", headers=conta().h).status_code == 404


# ---------- mural: filtro e paginação ----------

def test_mural_filtra_por_categoria_e_pagina_do_mais_recente(client, h, conta, publicado):
    leitor = conta()
    feitos = [publicado(titulo=f"C{i}", categoria="evento" if i % 2 else "aviso") for i in range(5)]
    todos = client.get("/comunicados?limit=2", headers=leitor.h).json()
    assert (todos["total"], len(todos["items"]), todos["limit"], todos["offset"]) == (5, 2, 2, 0)
    assert todos["items"][0]["id"] == feitos[-1]["id"]  # mais recente primeiro
    segunda = client.get("/comunicados?limit=2&offset=2", headers=leitor.h).json()["items"]
    assert [c["id"] for c in segunda] == [feitos[2]["id"], feitos[1]["id"]]
    eventos = client.get("/comunicados?categoria=evento", headers=leitor.h).json()
    assert eventos["total"] == 2 and all(c["categoria"] == "evento" for c in eventos["items"])
    assert client.get("/comunicados?limit=0", headers=leitor.h).status_code == 422
    assert client.get("/comunicados?categoria=x", headers=leitor.h).status_code == 422


def test_gerenciar_lista_todos_os_estados_e_filtra(client, h, criar, publicado):
    rasc = criar(titulo="Rascunho")
    pub = publicado(titulo="Publicado")
    agend = criar(titulo="Agendado")
    client.post(f"/comunicados/{agend['id']}/publicar", headers=h, json={"quando": (agora() + timedelta(days=1)).isoformat()})
    assert client.get("/comunicados/gerenciar", headers=h).json()["total"] == 3
    assert ids(client.get("/comunicados/gerenciar?status=rascunho", headers=h)) == [rasc["id"]]
    assert ids(client.get("/comunicados/gerenciar?status=publicado", headers=h)) == [pub["id"]]
    assert ids(client.get("/comunicados/gerenciar?status=agendado", headers=h)) == [agend["id"]]
    assert client.get("/comunicados/gerenciar?status=x", headers=h).status_code == 422


def test_autor_e_o_nome_do_membro_ou_o_email(client, auth, h, criar, conta):
    assert criar()["autor"] == "admin@a.org"  # admin sem membro ligado
    pastor = conta(PerfilUsuario.PASTOR, membro={"nome": "Pastor João"})
    assert criar(headers=pastor.h)["autor"] == "Pastor João"  # nome do membro ligado


# ---------- a liderança escreve só para a própria sociedade ----------

@pytest.fixture
def lider(client, h, conta, sociedades):
    def _lider(sigla="UMP", cargo="presidente"):
        x = conta(membro={})
        r = client.post(f"/sociedades/{sociedades[sigla]['id']}/lideranca", headers=h,
                        json={"membro_id": x.membro["id"], "cargo": cargo})
        assert r.status_code == 201, r.text
        return x

    return _lider


def test_lider_escreve_para_a_propria_sociedade(client, lider, criar, sociedades):
    L = lider()
    c = criar(headers=L.h, publico="sociedade", sociedade_id=sociedades["UMP"]["id"])
    assert c["sociedade_sigla"] == "UMP" and c["status"] == "rascunho"
    r = client.post(f"/comunicados/{c['id']}/publicar", headers=L.h, json={})
    assert r.status_code == 200 and r.json()["status"] == "publicado"


def test_lider_nao_escreve_para_outro_publico_nem_outra_sociedade(client, lider, criar, sociedades):
    L = lider()
    criar(headers=L.h, esperado=403, publico="igreja")
    criar(headers=L.h, esperado=403, publico="comungantes")
    criar(headers=L.h, esperado=403, publico="oficiais")
    criar(headers=L.h, esperado=403, publico="sociedade", sociedade_id=sociedades["UCP"]["id"])


def test_lider_gerencia_so_os_comunicados_da_sua_sociedade(client, h, lider, criar, sociedades):
    L = lider()
    meu = criar(publico="sociedade", sociedade_id=sociedades["UMP"]["id"], titulo="Meu")
    alheio = criar(publico="sociedade", sociedade_id=sociedades["UCP"]["id"], titulo="Alheio")
    geral = criar(titulo="Geral")

    assert ids(client.get("/comunicados/gerenciar", headers=L.h)) == [meu["id"]]
    # coautor: outro líder da mesma sociedade edita e publica o rascunho do admin
    assert client.patch(f"/comunicados/{meu['id']}", headers=L.h, json={"titulo": "Meu 2"}).status_code == 200
    assert client.post(f"/comunicados/{meu['id']}/publicar", headers=L.h, json={}).status_code == 200
    assert client.post(f"/comunicados/{meu['id']}/despublicar", headers=L.h).status_code == 200
    # os demais rascunhos nem aparecem para ele
    for outro in (alheio, geral):
        assert client.get(f"/comunicados/{outro['id']}", headers=L.h).status_code == 404
        assert client.patch(f"/comunicados/{outro['id']}", headers=L.h, json={"titulo": "X"}).status_code == 404
        assert client.delete(f"/comunicados/{outro['id']}", headers=L.h).status_code == 404
    assert client.delete(f"/comunicados/{meu['id']}", headers=L.h).status_code == 204


def test_lider_nao_amplia_o_publico_de_um_comunicado(client, lider, criar, sociedades):
    L = lider()
    c = criar(headers=L.h, publico="sociedade", sociedade_id=sociedades["UMP"]["id"])
    assert client.patch(f"/comunicados/{c['id']}", headers=L.h, json={"publico": "igreja"}).status_code == 403
    r = client.patch(f"/comunicados/{c['id']}", headers=L.h,
                     json={"publico": "sociedade", "sociedade_id": sociedades["UCP"]["id"]})
    assert r.status_code == 403


def test_leitor_de_comunicado_publicado_nao_o_edita(client, conta, publicado):
    c = publicado()  # público: igreja
    leitor = conta(membro={})
    assert client.get(f"/comunicados/{c['id']}", headers=leitor.h).status_code == 200
    assert client.patch(f"/comunicados/{c['id']}", headers=leitor.h, json={"titulo": "X"}).status_code == 403
    assert client.delete(f"/comunicados/{c['id']}", headers=leitor.h).status_code == 403
    assert client.post(f"/comunicados/{c['id']}/despublicar", headers=leitor.h).status_code == 403


def test_lider_perde_a_escrita_ao_encerrar_o_mandato(client, h, lider, criar, sociedades):
    L = lider()
    ump = sociedades["UMP"]["id"]
    criar(headers=L.h, publico="sociedade", sociedade_id=ump)
    mandato = client.get(f"/sociedades/{ump}/lideranca", headers=h).json()[0]
    client.patch(f"/sociedades/{ump}/lideranca/{mandato['id']}", headers=h,
                 json={"fim": datetime.now().date().isoformat()})
    criar(headers=L.h, esperado=403, publico="sociedade", sociedade_id=ump)
    assert client.get("/comunicados/gerenciar", headers=L.h).status_code == 403


# ---------- isolamento e senha ----------

def test_outra_igreja_nao_ve_nem_altera(client, auth, criar_igreja, criar_usuario, h, publicado):
    c = publicado()
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    assert client.get("/comunicados", headers=hb).json()["total"] == 0
    assert client.get("/comunicados/gerenciar", headers=hb).json()["total"] == 0
    assert client.get(f"/comunicados/{c['id']}", headers=hb).status_code == 404
    assert client.patch(f"/comunicados/{c['id']}", headers=hb, json={"titulo": "X"}).status_code == 404
    assert client.delete(f"/comunicados/{c['id']}", headers=hb).status_code == 404
    assert client.post(f"/comunicados/{c['id']}/despublicar", headers=hb).status_code == 404


def test_troca_de_senha_pendente_bloqueia_o_mural(client, login, criar_usuario, igreja):
    u = criar_usuario(igreja, "novo@a.org", perfil=PerfilUsuario.USUARIO, troca_obrigatoria=True)
    hx = {"Authorization": f"Bearer {login(u).json()['access_token']}"}
    assert client.get("/comunicados", headers=hx).status_code == 403
