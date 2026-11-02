import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from core.database import SessionLocal
from models import LogAuditoria, Socio
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
def ucp(client, h):
    r = client.post("/sociedades", headers=h, json={"sigla": "UCP"})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def adicionar_socio(client, h):
    def _add(sociedade_id, membro_id=None, tipo="ativo", headers=None, **extra):
        corpo = {"tipo": tipo, **({"membro_id": membro_id} if membro_id else {}), **extra}
        r = client.post(f"/sociedades/{sociedade_id}/socios", headers=headers or h, json=corpo)
        assert r.status_code == 201, r.text
        return r.json()

    return _add


def auditoria(acao):
    with SessionLocal() as db:
        return list(db.scalars(select(LogAuditoria).where(LogAuditoria.acao == acao)))


# ---------- permissões ----------

@pytest.mark.parametrize("perfil", [PerfilUsuario.PRESBITERO, PerfilUsuario.USUARIO])
def test_so_admin_e_pastor_acessam_sociedades(client, auth, criar_usuario, igreja, ucp, perfil):
    u = criar_usuario(igreja, "x@a.org", perfil=perfil)
    hx = auth(u)
    sid = ucp["id"]
    assert client.get("/sociedades", headers=hx).status_code == 403
    assert client.post("/sociedades", headers=hx, json={"sigla": "UPA"}).status_code == 403
    assert client.get(f"/sociedades/{sid}", headers=hx).status_code == 403
    assert client.get(f"/sociedades/{sid}/socios", headers=hx).status_code == 403
    assert client.get(f"/sociedades/{sid}/reunioes", headers=hx).status_code == 403
    assert client.get(f"/sociedades/{sid}/frequencia", headers=hx).status_code == 403
    assert client.post(f"/sociedades/{sid}/reunioes", headers=hx, json={"data": dias_atras(1)}).status_code == 403


def test_pastor_gerencia_sociedades(client, auth, criar_usuario, igreja, novo_membro):
    pastor = criar_usuario(igreja, "pastor@a.org", perfil=PerfilUsuario.PASTOR)
    hp = auth(pastor)
    r = client.post("/sociedades", headers=hp, json={"sigla": "SAF"})
    assert r.status_code == 201
    m = novo_membro(headers=hp)
    r = client.post(
        f"/sociedades/{r.json()['id']}/socios", headers=hp, json={"tipo": "ativo", "membro_id": m["id"]}
    )
    assert r.status_code == 201


def test_sociedades_exigem_autenticacao(client, ucp):
    assert client.get("/sociedades").status_code == 401
    assert client.get(f"/sociedades/{ucp['id']}/socios").status_code == 401


# ---------- sociedade ----------

def test_criar_listar_e_atualizar_sociedade(client, h):
    assert client.post("/sociedades", headers=h, json={"sigla": "UMP", "nome": " Mocidade Sol "}).json()["nome"] == "Mocidade Sol"
    client.post("/sociedades", headers=h, json={"sigla": "SAF"})
    lista = client.get("/sociedades", headers=h).json()
    assert [s["sigla"] for s in lista] == ["SAF", "UMP"]
    assert all(s["total_socios"] == 0 for s in lista)

    ump = next(s for s in lista if s["sigla"] == "UMP")
    r = client.patch(f"/sociedades/{ump['id']}", headers=h, json={"nome": None})
    assert r.status_code == 200 and r.json()["nome"] is None
    assert len(auditoria("sociedade_criada")) == 2


def test_sigla_repetida_na_mesma_igreja_da_conflito(client, h, ucp):
    assert client.post("/sociedades", headers=h, json={"sigla": "UCP"}).status_code == 409


def test_sigla_invalida_e_recusada(client, h):
    assert client.post("/sociedades", headers=h, json={"sigla": "XYZ"}).status_code == 422


def test_cada_igreja_tem_as_suas_sociedades(client, auth, criar_igreja, criar_usuario, h, ucp):
    outra = criar_igreja("Igreja B")
    hb = auth(criar_usuario(outra, "admin@b.org", perfil=ADMIN))
    assert client.get("/sociedades", headers=hb).json() == []
    # mesma sigla em outra igreja é permitida
    assert client.post("/sociedades", headers=hb, json={"sigla": "UCP"}).status_code == 201
    # e a sociedade de A é invisível para B
    assert client.get(f"/sociedades/{ucp['id']}", headers=hb).status_code == 404
    assert client.get(f"/sociedades/{ucp['id']}/socios", headers=hb).status_code == 404
    assert client.patch(f"/sociedades/{ucp['id']}", headers=hb, json={"nome": "X"}).status_code == 404


# ---------- sócios ----------

def test_adicionar_socios_dos_tres_tipos(client, h, ucp, novo_membro, adicionar_socio):
    a = novo_membro(nome="Ana")
    b = novo_membro(nome="Bia")
    s1 = adicionar_socio(ucp["id"], a["id"], "ativo")
    s2 = adicionar_socio(ucp["id"], b["id"], "cooperador")
    s3 = adicionar_socio(ucp["id"], tipo="nao_membro", nome_externo="  Carlos Visitante ")
    assert (s1["nome"], s1["tipo"], s1["saiu_em"]) == ("Ana", "ativo", None)
    assert s1["entrou_em"] == date.today().isoformat()
    assert s2["tipo"] == "cooperador"
    assert (s3["nome"], s3["membro_id"]) == ("Carlos Visitante", None)

    lista = client.get(f"/sociedades/{ucp['id']}/socios", headers=h).json()
    assert [s["nome"] for s in lista] == ["Ana", "Bia", "Carlos Visitante"]
    assert client.get(f"/sociedades/{ucp['id']}", headers=h).json()["total_socios"] == 3
    assert len(auditoria("socio_adicionado")) == 3


@pytest.mark.parametrize(
    "corpo",
    [
        {"tipo": "ativo"},  # falta o membro
        {"tipo": "nao_membro"},  # falta o nome
        {"tipo": "nao_membro", "nome_externo": "   "},
        {"tipo": "ativo", "membro_id": str(uuid.uuid4()), "nome_externo": "Fulano"},
        {"tipo": "nao_membro", "membro_id": str(uuid.uuid4()), "nome_externo": "Fulano"},
        {"tipo": "outro", "nome_externo": "Fulano"},
    ],
)
def test_dados_invalidos_do_socio(client, h, ucp, corpo):
    assert client.post(f"/sociedades/{ucp['id']}/socios", headers=h, json=corpo).status_code == 422


def test_membro_nao_pode_ser_socio_duas_vezes(client, h, ucp, novo_membro, adicionar_socio):
    m = novo_membro()
    adicionar_socio(ucp["id"], m["id"])
    r = client.post(f"/sociedades/{ucp['id']}/socios", headers=h, json={"tipo": "cooperador", "membro_id": m["id"]})
    assert r.status_code == 409


def test_mesmo_membro_pode_estar_em_sociedades_diferentes(client, h, ucp, novo_membro, adicionar_socio):
    m = novo_membro()
    upa = client.post("/sociedades", headers=h, json={"sigla": "UPA"}).json()
    adicionar_socio(ucp["id"], m["id"])
    adicionar_socio(upa["id"], m["id"])


def test_membro_de_outra_igreja_ou_inexistente_da_404(client, auth, criar_igreja, criar_usuario, h, ucp):
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    de_b = client.post("/membros", headers=hb, json={"nome": "De B", "rol": "C"}).json()
    for membro_id in (de_b["id"], str(uuid.uuid4())):
        r = client.post(f"/sociedades/{ucp['id']}/socios", headers=h, json={"tipo": "ativo", "membro_id": membro_id})
        assert r.status_code == 404


def test_membro_que_saiu_do_rol_nao_pode_ser_socio(client, h, ucp, novo_membro):
    m = novo_membro()
    ev = {"tipo": "saida", "data": dias_atras(1), "ata_conselho": "Ata 1", "situacao_resultante": "transferido"}
    assert client.post(f"/membros/{m['id']}/eventos", headers=h, json=ev).status_code == 201
    r = client.post(f"/sociedades/{ucp['id']}/socios", headers=h, json={"tipo": "ativo", "membro_id": m["id"]})
    assert r.status_code == 409


def test_membro_excluido_logicamente_sai_das_listas_e_da_contagem(client, h, ucp, novo_membro, adicionar_socio):
    m = novo_membro(nome="Cadastro Errado")
    adicionar_socio(ucp["id"], m["id"])
    assert client.get(f"/sociedades/{ucp['id']}", headers=h).json()["total_socios"] == 1

    assert client.delete(f"/membros/{m['id']}", headers=h).status_code == 204
    assert client.get(f"/sociedades/{ucp['id']}/socios?incluir_ex=true", headers=h).json() == []
    assert client.get(f"/sociedades/{ucp['id']}", headers=h).json()["total_socios"] == 0
    r = client.post(f"/sociedades/{ucp['id']}/socios", headers=h, json={"tipo": "ativo", "membro_id": m["id"]})
    assert r.status_code == 404


def test_remover_socio_mantem_o_registro_e_permite_voltar(client, h, ucp, novo_membro, adicionar_socio):
    m = novo_membro()
    s = adicionar_socio(ucp["id"], m["id"])
    assert client.delete(f"/sociedades/{ucp['id']}/socios/{s['id']}", headers=h).status_code == 204

    assert client.get(f"/sociedades/{ucp['id']}/socios", headers=h).json() == []
    todos = client.get(f"/sociedades/{ucp['id']}/socios?incluir_ex=true", headers=h).json()
    assert [x["saiu_em"] for x in todos] == [date.today().isoformat()]
    assert client.get(f"/sociedades/{ucp['id']}", headers=h).json()["total_socios"] == 0
    assert client.delete(f"/sociedades/{ucp['id']}/socios/{s['id']}", headers=h).status_code == 409
    assert len(auditoria("socio_removido")) == 1

    # voltar a ser sócio cria um novo vínculo; o histórico antigo permanece
    adicionar_socio(ucp["id"], m["id"])
    assert len(client.get(f"/sociedades/{ucp['id']}/socios?incluir_ex=true", headers=h).json()) == 2


def test_alterar_socio(client, h, ucp, novo_membro, adicionar_socio):
    m = novo_membro()
    membro = adicionar_socio(ucp["id"], m["id"], "ativo")
    externo = adicionar_socio(ucp["id"], tipo="nao_membro", nome_externo="Visitante")
    base = f"/sociedades/{ucp['id']}/socios"

    r = client.patch(f"{base}/{membro['id']}", headers=h, json={"tipo": "cooperador"})
    assert r.status_code == 200 and r.json()["tipo"] == "cooperador"
    r = client.patch(f"{base}/{externo['id']}", headers=h, json={"nome_externo": "Visitante Corrigido"})
    assert r.json()["nome"] == "Visitante Corrigido"

    # não converte entre membro e não membro, nem renomeia membro
    assert client.patch(f"{base}/{membro['id']}", headers=h, json={"tipo": "nao_membro"}).status_code == 400
    assert client.patch(f"{base}/{externo['id']}", headers=h, json={"tipo": "ativo"}).status_code == 400
    assert client.patch(f"{base}/{membro['id']}", headers=h, json={"nome_externo": "X"}).status_code == 400
    assert client.patch(f"{base}/{membro['id']}", headers=h, json={}).status_code == 422
    assert client.patch(f"{base}/{uuid.uuid4()}", headers=h, json={"tipo": "ativo"}).status_code == 404

    client.delete(f"{base}/{membro['id']}", headers=h)
    assert client.patch(f"{base}/{membro['id']}", headers=h, json={"tipo": "ativo"}).status_code == 409


def test_socio_so_e_visto_pela_sociedade_certa(client, h, ucp, novo_membro, adicionar_socio):
    upa = client.post("/sociedades", headers=h, json={"sigla": "UPA"}).json()
    s = adicionar_socio(ucp["id"], novo_membro()["id"])
    assert client.patch(f"/sociedades/{upa['id']}/socios/{s['id']}", headers=h, json={"tipo": "cooperador"}).status_code == 404
    assert client.delete(f"/sociedades/{upa['id']}/socios/{s['id']}", headers=h).status_code == 404


# ---------- reuniões ----------

@pytest.fixture
def tres_socios(novo_membro, adicionar_socio, ucp):
    return [
        adicionar_socio(ucp["id"], novo_membro(nome=n)["id"]) for n in ("Ana", "Bia", "Cris")
    ]


def test_criar_reuniao_com_presencas(client, h, ucp, tres_socios):
    ana, bia, cris = tres_socios
    corpo = {
        "data": dias_atras(7),
        "tema": " Culto de abertura ",
        "presencas": [
            {"socio_id": ana["id"], "status": "P"},
            {"socio_id": bia["id"], "status": "A"},
            {"socio_id": cris["id"], "status": "J"},
        ],
    }
    r = client.post(f"/sociedades/{ucp['id']}/reunioes", headers=h, json=corpo)
    assert r.status_code == 201, r.text
    corpo_r = r.json()
    assert corpo_r["tema"] == "Culto de abertura"
    assert (corpo_r["presentes"], corpo_r["ausentes"], corpo_r["justificados"]) == (1, 1, 1)
    assert [(p["nome"], p["status"]) for p in corpo_r["presencas"]] == [("Ana", "P"), ("Bia", "A"), ("Cris", "J")]
    assert auditoria("reuniao_criada")[0].detalhes["presencas"] == 3


def test_reuniao_sem_presencas_e_listagem_do_mais_recente_ao_mais_antigo(client, h, ucp, tres_socios):
    base = f"/sociedades/{ucp['id']}/reunioes"
    client.post(base, headers=h, json={"data": dias_atras(14)})
    client.post(base, headers=h, json={"data": dias_atras(7), "presencas": [{"socio_id": tres_socios[0]["id"], "status": "P"}]})
    lista = client.get(base, headers=h).json()
    assert [r["data"] for r in lista] == [dias_atras(7), dias_atras(14)]
    assert [r["presentes"] for r in lista] == [1, 0]


def test_reuniao_exige_data_valida_e_unica_por_sociedade(client, h, ucp):
    base = f"/sociedades/{ucp['id']}/reunioes"
    futura = (date.today() + timedelta(days=1)).isoformat()
    assert client.post(base, headers=h, json={"data": futura}).status_code == 422
    assert client.post(base, headers=h, json={}).status_code == 422
    assert client.post(base, headers=h, json={"data": dias_atras(3)}).status_code == 201
    assert client.post(base, headers=h, json={"data": dias_atras(3)}).status_code == 409
    # outra sociedade pode ter reunião no mesmo dia
    upa = client.post("/sociedades", headers=h, json={"sigla": "UPA"}).json()
    assert client.post(f"/sociedades/{upa['id']}/reunioes", headers=h, json={"data": dias_atras(3)}).status_code == 201


def test_reuniao_com_presenca_invalida_nao_deixa_rastro(client, h, ucp, tres_socios):
    base = f"/sociedades/{ucp['id']}/reunioes"
    corpo = {"data": dias_atras(2), "presencas": [
        {"socio_id": tres_socios[0]["id"], "status": "P"},
        {"socio_id": str(uuid.uuid4()), "status": "P"},
    ]}
    assert client.post(base, headers=h, json=corpo).status_code == 404
    assert client.get(base, headers=h).json() == []
    # e a data continua livre
    assert client.post(base, headers=h, json={"data": dias_atras(2)}).status_code == 201


def test_status_de_presenca_e_socios_repetidos_sao_validados(client, h, ucp, tres_socios):
    base = f"/sociedades/{ucp['id']}/reunioes"
    sid = tres_socios[0]["id"]
    assert client.post(base, headers=h, json={"data": dias_atras(1), "presencas": [{"socio_id": sid, "status": "X"}]}).status_code == 422
    dup = [{"socio_id": sid, "status": "P"}, {"socio_id": sid, "status": "A"}]
    assert client.post(base, headers=h, json={"data": dias_atras(1), "presencas": dup}).status_code == 422


def test_presenca_de_socio_de_outra_sociedade_e_recusada(client, h, ucp, novo_membro, adicionar_socio):
    upa = client.post("/sociedades", headers=h, json={"sigla": "UPA"}).json()
    de_upa = adicionar_socio(upa["id"], novo_membro()["id"])
    r = client.post(f"/sociedades/{ucp['id']}/reunioes", headers=h, json={
        "data": dias_atras(1), "presencas": [{"socio_id": de_upa["id"], "status": "P"}]})
    assert r.status_code == 404


def test_lancar_e_corrigir_presencas_em_lote(client, h, ucp, tres_socios):
    ana, bia, cris = tres_socios
    reuniao = client.post(f"/sociedades/{ucp['id']}/reunioes", headers=h, json={
        "data": dias_atras(5), "presencas": [{"socio_id": ana["id"], "status": "P"}]}).json()
    url = f"/sociedades/{ucp['id']}/reunioes/{reuniao['id']}/presencas"

    r = client.put(url, headers=h, json={"presencas": [
        {"socio_id": ana["id"], "status": "A"},  # corrige
        {"socio_id": bia["id"], "status": "P"},  # novo
    ]})
    assert r.status_code == 200, r.text
    assert {p["nome"]: p["status"] for p in r.json()["presencas"]} == {"Ana": "A", "Bia": "P"}
    assert (r.json()["presentes"], r.json()["ausentes"]) == (1, 1)  # Cris não foi tocada nem criada

    assert client.put(url, headers=h, json={"presencas": [
        {"socio_id": ana["id"], "status": "P"}, {"socio_id": ana["id"], "status": "A"}]}).status_code == 422
    assert client.put(url, headers=h, json={}).status_code == 422
    assert len(auditoria("presencas_lancadas")) == 1


def test_socio_que_ja_saiu_nao_recebe_presenca_depois_da_saida(client, h, ucp, tres_socios):
    ana = tres_socios[0]
    with SessionLocal() as db:
        socio = db.get(Socio, uuid.UUID(ana["id"]))
        socio.saiu_em = date.today() - timedelta(days=10)
        db.commit()
    base = f"/sociedades/{ucp['id']}/reunioes"
    # antes da saída: permitido (corrigir o histórico)
    assert client.post(base, headers=h, json={"data": dias_atras(20), "presencas": [{"socio_id": ana["id"], "status": "P"}]}).status_code == 201
    # depois da saída: recusado
    r = client.post(base, headers=h, json={"data": dias_atras(2), "presencas": [{"socio_id": ana["id"], "status": "P"}]})
    assert r.status_code == 409


def test_atualizar_reuniao(client, h, ucp):
    base = f"/sociedades/{ucp['id']}/reunioes"
    a = client.post(base, headers=h, json={"data": dias_atras(9), "tema": "Velho"}).json()
    b = client.post(base, headers=h, json={"data": dias_atras(8)}).json()
    assert client.patch(f"{base}/{a['id']}", headers=h, json={"tema": "Novo"}).json()["tema"] == "Novo"
    assert client.patch(f"{base}/{a['id']}", headers=h, json={"tema": None}).json()["tema"] is None
    assert client.patch(f"{base}/{a['id']}", headers=h, json={"data": dias_atras(4)}).json()["data"] == dias_atras(4)
    assert client.patch(f"{base}/{b['id']}", headers=h, json={"data": dias_atras(4)}).status_code == 409
    assert client.patch(f"{base}/{a['id']}", headers=h, json={}).status_code == 422
    assert client.patch(f"{base}/{uuid.uuid4()}", headers=h, json={"tema": "x"}).status_code == 404


def test_reuniao_de_outra_igreja_ou_sociedade_nao_e_acessivel(client, auth, criar_igreja, criar_usuario, h, ucp):
    r = client.post(f"/sociedades/{ucp['id']}/reunioes", headers=h, json={"data": dias_atras(1)}).json()
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    assert client.get(f"/sociedades/{ucp['id']}/reunioes/{r['id']}", headers=hb).status_code == 404
    upa = client.post("/sociedades", headers=h, json={"sigla": "UPA"}).json()
    assert client.get(f"/sociedades/{upa['id']}/reunioes/{r['id']}", headers=h).status_code == 404


# ---------- frequência ----------

def lancar(client, h, sociedade_id, data, presencas):
    r = client.post(f"/sociedades/{sociedade_id}/reunioes", headers=h, json={
        "data": data, "presencas": [{"socio_id": s, "status": st} for s, st in presencas]})
    assert r.status_code == 201, r.text


def test_frequencia_por_socio(client, h, ucp, tres_socios):
    ana, bia, cris = (s["id"] for s in tres_socios)
    lancar(client, h, ucp["id"], dias_atras(21), [(ana, "P"), (bia, "A"), (cris, "J")])
    lancar(client, h, ucp["id"], dias_atras(14), [(ana, "P"), (bia, "P")])
    lancar(client, h, ucp["id"], dias_atras(7), [(ana, "A")])

    r = client.get(f"/sociedades/{ucp['id']}/frequencia", headers=h).json()
    assert r["total_reunioes"] == 3
    por_nome = {s["nome"]: s for s in r["socios"]}
    assert (por_nome["Ana"]["presentes"], por_nome["Ana"]["ausentes"], por_nome["Ana"]["percentual_presenca"]) == (2, 1, 66.7)
    assert (por_nome["Bia"]["presentes"], por_nome["Bia"]["ausentes"], por_nome["Bia"]["sem_registro"]) == (1, 1, 1)
    assert (por_nome["Cris"]["justificados"], por_nome["Cris"]["percentual_presenca"], por_nome["Cris"]["sem_registro"]) == (1, 0.0, 2)


def test_frequencia_respeita_o_periodo_e_sem_lancamento_nao_tem_percentual(client, h, ucp, tres_socios):
    ana, bia, _ = (s["id"] for s in tres_socios)
    lancar(client, h, ucp["id"], dias_atras(30), [(ana, "P")])
    lancar(client, h, ucp["id"], dias_atras(5), [(ana, "A")])
    base = f"/sociedades/{ucp['id']}/frequencia"

    r = client.get(base, params={"de": dias_atras(10)}, headers=h).json()
    assert r["total_reunioes"] == 1
    ana_r = next(s for s in r["socios"] if s["nome"] == "Ana")
    assert (ana_r["presentes"], ana_r["ausentes"]) == (0, 1)
    bia_r = next(s for s in r["socios"] if s["nome"] == "Bia")
    assert bia_r["percentual_presenca"] is None and bia_r["sem_registro"] == 1

    assert client.get(base, params={"de": dias_atras(1), "ate": dias_atras(9)}, headers=h).status_code == 400
    assert client.get(base, params={"de": "ontem"}, headers=h).status_code == 422


def test_ex_socio_so_aparece_na_frequencia_se_tiver_presenca_no_periodo(client, h, ucp, tres_socios):
    ana, bia, _ = tres_socios
    lancar(client, h, ucp["id"], dias_atras(10), [(ana["id"], "P")])
    for s in (ana, bia):
        client.delete(f"/sociedades/{ucp['id']}/socios/{s['id']}", headers=h)

    nomes = [s["nome"] for s in client.get(f"/sociedades/{ucp['id']}/frequencia", headers=h).json()["socios"]]
    assert "Ana" in nomes and "Bia" not in nomes
    # fora do período em que Ana tinha presença, ela também some
    nomes = [s["nome"] for s in client.get(f"/sociedades/{ucp['id']}/frequencia?de={dias_atras(2)}", headers=h).json()["socios"]]
    assert "Ana" not in nomes
