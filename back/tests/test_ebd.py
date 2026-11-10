from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from core.database import SessionLocal
from models import LogAuditoria
from models.enums import PerfilUsuario

ADMIN = PerfilUsuario.ADMIN
HOJE = date.today()


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
    """Cria um usuário ligado a um membro (nome `Membro N`)."""
    contador = iter(range(1000))

    def _conta(perfil=PerfilUsuario.USUARIO, **membro):
        n = next(contador)
        u = criar_usuario(igreja, f"u{n}@a.org", perfil=perfil)
        m = novo_membro(nome=f"Membro {n}", **membro)
        r = client.patch(f"/usuarios/{u.id}", headers=h, json={"membro_id": m["id"]})
        assert r.status_code == 200, r.text
        return SimpleNamespace(usuario=u, membro=m, h=auth(u))

    return _conta


@pytest.fixture
def classe(client, h):
    r = client.post("/ebd/classes", headers=h, json={"nome": "Adolescentes", "faixa_etaria": "12 a 17"})
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def professor(client, h, conta, classe):
    """Usuário comum que é professor em exercício da `classe`."""
    p = conta()
    r = client.post(f"/ebd/classes/{classe['id']}/professores", headers=h, json={"membro_id": p.membro["id"]})
    assert r.status_code == 201, r.text
    return p


def auditoria(acao):
    with SessionLocal() as db:
        return list(db.scalars(select(LogAuditoria).where(LogAuditoria.acao == acao)))


def url(classe, *partes):
    return "/".join(["/ebd/classes", classe["id"], *partes])


# ---------- classes ----------

def test_gestor_cria_e_lista_classes(client, h, classe):
    assert classe["nome"] == "Adolescentes"
    assert (classe["ativa"], classe["total_alunos"], classe["total_professores"]) == (True, 0, 0)
    assert [c["id"] for c in client.get("/ebd/classes", headers=h).json()] == [classe["id"]]
    assert auditoria("ebd_classe_criada")


def test_nome_da_classe_e_unico_sem_distinguir_maiusculas(client, h, classe):
    r = client.post("/ebd/classes", headers=h, json={"nome": "ADOLESCENTES"})
    assert r.status_code == 409
    outra = client.post("/ebd/classes", headers=h, json={"nome": "Jovens"}).json()
    r = client.patch(url(outra), headers=h, json={"nome": "adolescentes"})
    assert r.status_code == 409


def test_pastor_tambem_gerencia(client, conta, classe):
    pastor = conta(PerfilUsuario.PASTOR)
    assert client.post("/ebd/classes", headers=pastor.h, json={"nome": "Casais"}).status_code == 201


def test_desativar_e_reativar_classe(client, h, classe):
    r = client.patch(url(classe), headers=h, json={"ativa": False})
    assert (r.status_code, r.json()["ativa"]) == (200, False)
    # classe desativada não recebe alterações...
    assert client.post(url(classe, "alunos"), headers=h, json={"nome_externo": "Ana"}).status_code == 409
    # ...até ser reativada
    client.patch(url(classe), headers=h, json={"ativa": True})
    assert client.post(url(classe, "alunos"), headers=h, json={"nome_externo": "Ana"}).status_code == 201


def test_atualizar_exige_algum_campo(client, h, classe):
    assert client.patch(url(classe), headers=h, json={}).status_code == 422


# ---------- permissões ----------

def test_usuario_comum_nao_ve_classes_nem_cria(client, conta, classe):
    comum = conta()
    assert client.get("/ebd/classes", headers=comum.h).json() == []
    assert client.get(url(classe), headers=comum.h).status_code == 403
    assert client.post("/ebd/classes", headers=comum.h, json={"nome": "X"}).status_code == 403


def test_professor_ve_so_a_propria_classe(client, h, professor, classe):
    outra = client.post("/ebd/classes", headers=h, json={"nome": "Jovens"}).json()
    lista = client.get("/ebd/classes", headers=professor.h).json()
    assert [c["id"] for c in lista] == [classe["id"]]
    assert client.get(url(outra), headers=professor.h).status_code == 403
    assert client.get(url(outra, "alunos"), headers=professor.h).status_code == 403


def test_professor_nao_gerencia_classe_nem_professores(client, h, professor, conta, classe):
    assert client.patch(url(classe), headers=professor.h, json={"nome": "Outro"}).status_code == 403
    outro = conta()
    r = client.post(url(classe, "professores"), headers=professor.h, json={"membro_id": outro.membro["id"]})
    assert r.status_code == 403


def test_professor_cuida_de_alunos_aulas_e_presenca(client, professor, classe, novo_membro):
    m = novo_membro(nome="Pedro Lima")
    r = client.post(url(classe, "alunos"), headers=professor.h, json={"membro_id": m["id"]})
    assert r.status_code == 201, r.text
    aluno = r.json()
    r = client.post(
        url(classe, "aulas"), headers=professor.h,
        json={"data": HOJE.isoformat(), "licao": "Romanos 1", "presencas": [{"aluno_id": aluno["id"], "status": "P"}]},
    )
    assert r.status_code == 201, r.text
    assert (r.json()["presentes"], r.json()["licao"]) == (1, "Romanos 1")


def test_professor_encerrado_perde_o_acesso(client, h, professor, classe):
    p = client.get(url(classe, "professores"), headers=h).json()[0]
    r = client.patch(url(classe, "professores", p["id"]), headers=h, json={"fim": HOJE.isoformat()})
    assert r.status_code == 200
    assert client.get(url(classe), headers=professor.h).status_code == 403
    assert client.get("/ebd/classes", headers=professor.h).json() == []


def test_classe_de_outra_igreja_nao_aparece(client, classe, auth, criar_igreja, criar_usuario):
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    assert client.get(url(classe), headers=hb).status_code == 404
    assert client.get("/ebd/classes", headers=hb).json() == []


# ---------- professores ----------

def test_professor_repetido_e_membro_fora_do_rol(client, h, classe, professor, conta):
    r = client.post(url(classe, "professores"), headers=h, json={"membro_id": professor.membro["id"]})
    assert r.status_code == 409
    saiu = conta()
    ev = {"tipo": "saida", "data": (HOJE - timedelta(days=1)).isoformat(), "ata_conselho": "Ata 1",
          "situacao_resultante": "transferido"}
    assert client.post(f"/membros/{saiu.membro['id']}/eventos", headers=h, json=ev).status_code == 201
    r = client.post(url(classe, "professores"), headers=h, json={"membro_id": saiu.membro["id"]})
    assert r.status_code == 409


def test_encerrar_e_voltar_a_ser_professor(client, h, classe, professor):
    p = client.get(url(classe, "professores"), headers=h).json()[0]
    client.patch(url(classe, "professores", p["id"]), headers=h, json={"fim": HOJE.isoformat()})
    assert client.get(url(classe, "professores"), headers=h).json() == []
    assert len(client.get(url(classe, "professores"), headers=h, params={"incluir_encerrados": True}).json()) == 1
    r = client.post(url(classe, "professores"), headers=h, json={"membro_id": professor.membro["id"]})
    assert r.status_code == 201


def test_fim_nao_pode_ser_antes_do_inicio(client, h, classe, professor):
    p = client.get(url(classe, "professores"), headers=h).json()[0]
    r = client.patch(
        url(classe, "professores", p["id"]), headers=h, json={"fim": (HOJE - timedelta(days=400)).isoformat()}
    )
    assert r.status_code == 400


# ---------- alunos ----------

def test_aluno_membro_e_visitante(client, h, classe, novo_membro):
    m = novo_membro(nome="Pedro Lima")
    a = client.post(url(classe, "alunos"), headers=h, json={"membro_id": m["id"]}).json()
    v = client.post(url(classe, "alunos"), headers=h, json={"nome_externo": "  Visitante Joana "}).json()
    assert (a["nome"], v["nome"], v["membro_id"]) == ("Pedro Lima", "Visitante Joana", None)
    assert [x["nome"] for x in client.get(url(classe, "alunos"), headers=h).json()] == ["Pedro Lima", "Visitante Joana"]
    assert client.get(url(classe), headers=h).json()["total_alunos"] == 2


def test_aluno_exige_membro_ou_nome(client, h, classe, novo_membro):
    m = novo_membro()
    assert client.post(url(classe, "alunos"), headers=h, json={}).status_code == 422
    r = client.post(url(classe, "alunos"), headers=h, json={"membro_id": m["id"], "nome_externo": "X"})
    assert r.status_code == 422


def test_membro_nao_entra_duas_vezes_mas_pode_voltar(client, h, classe, novo_membro):
    m = novo_membro()
    a = client.post(url(classe, "alunos"), headers=h, json={"membro_id": m["id"]}).json()
    assert client.post(url(classe, "alunos"), headers=h, json={"membro_id": m["id"]}).status_code == 409
    assert client.delete(url(classe, "alunos", a["id"]), headers=h).status_code == 204
    assert client.delete(url(classe, "alunos", a["id"]), headers=h).status_code == 409
    assert client.post(url(classe, "alunos"), headers=h, json={"membro_id": m["id"]}).status_code == 201


def test_so_visitante_tem_o_nome_corrigido(client, h, classe, novo_membro):
    m = novo_membro()
    a = client.post(url(classe, "alunos"), headers=h, json={"membro_id": m["id"]}).json()
    v = client.post(url(classe, "alunos"), headers=h, json={"nome_externo": "Joana"}).json()
    assert client.patch(url(classe, "alunos", a["id"]), headers=h, json={"nome_externo": "X"}).status_code == 400
    r = client.patch(url(classe, "alunos", v["id"]), headers=h, json={"nome_externo": "Joana Souza"})
    assert (r.status_code, r.json()["nome"]) == (200, "Joana Souza")


def test_membro_excluido_some_dos_alunos(client, h, classe, novo_membro):
    m = novo_membro()
    client.post(url(classe, "alunos"), headers=h, json={"membro_id": m["id"]})
    assert client.delete(f"/membros/{m['id']}", headers=h).status_code in (200, 204)
    assert client.get(url(classe, "alunos"), headers=h).json() == []


def test_busca_de_membros_devolve_so_o_resumo(client, h, professor, classe, novo_membro):
    novo_membro(nome="Zacarias Teste")
    r = client.get(url(classe, "membros"), headers=professor.h, params={"q": "Zacar"})
    assert r.status_code == 200
    assert set(r.json()[0]) == {"id", "nome", "numero_rol"}


# ---------- aulas e presença ----------

@pytest.fixture
def alunos(client, h, classe):
    return [
        client.post(url(classe, "alunos"), headers=h, json={"nome_externo": n}).json()
        for n in ("Ana", "Bruno", "Carla")
    ]


def test_cria_aula_com_presencas_e_conta(client, h, classe, alunos):
    ana, bruno, carla = alunos
    r = client.post(
        url(classe, "aulas"), headers=h,
        json={
            "data": HOJE.isoformat(),
            "presencas": [
                {"aluno_id": ana["id"], "status": "P"},
                {"aluno_id": bruno["id"], "status": "A"},
                {"aluno_id": carla["id"], "status": "J"},
            ],
        },
    )
    assert r.status_code == 201, r.text
    corpo = r.json()
    assert (corpo["presentes"], corpo["ausentes"], corpo["justificados"]) == (1, 1, 1)
    assert [(p["nome"], p["status"]) for p in corpo["presencas"]] == [("Ana", "P"), ("Bruno", "A"), ("Carla", "J")]
    assert client.get(url(classe, "aulas"), headers=h).json()[0]["presentes"] == 1


def test_uma_aula_por_data_e_data_nao_pode_ser_futura(client, h, classe):
    assert client.post(url(classe, "aulas"), headers=h, json={"data": HOJE.isoformat()}).status_code == 201
    assert client.post(url(classe, "aulas"), headers=h, json={"data": HOJE.isoformat()}).status_code == 409
    futuro = (HOJE + timedelta(days=1)).isoformat()
    assert client.post(url(classe, "aulas"), headers=h, json={"data": futuro}).status_code == 422


def test_lancar_presencas_em_lote_corrige_o_que_ja_existe(client, h, classe, alunos):
    ana, bruno, _ = alunos
    aula = client.post(
        url(classe, "aulas"), headers=h,
        json={"data": HOJE.isoformat(), "presencas": [{"aluno_id": ana["id"], "status": "A"}]},
    ).json()
    r = client.put(
        url(classe, "aulas", aula["id"], "presencas"), headers=h,
        json={"presencas": [{"aluno_id": ana["id"], "status": "P"}, {"aluno_id": bruno["id"], "status": "P"}]},
    )
    assert r.status_code == 200, r.text
    assert (r.json()["presentes"], r.json()["ausentes"]) == (2, 0)
    assert auditoria("ebd_presencas_lancadas")


def test_presenca_repetida_ou_de_aluno_de_outra_classe(client, h, classe, alunos):
    ana = alunos[0]
    r = client.post(
        url(classe, "aulas"), headers=h,
        json={"data": HOJE.isoformat(), "presencas": [{"aluno_id": ana["id"], "status": "P"}] * 2},
    )
    assert r.status_code == 422
    outra = client.post("/ebd/classes", headers=h, json={"nome": "Jovens"}).json()
    estranho = client.post(url(outra, "alunos"), headers=h, json={"nome_externo": "Zé"}).json()
    r = client.post(
        url(classe, "aulas"), headers=h,
        json={"data": HOJE.isoformat(), "presencas": [{"aluno_id": estranho["id"], "status": "P"}]},
    )
    assert r.status_code == 404
    # a validação vem antes de gravar: a aula não foi criada
    assert client.get(url(classe, "aulas"), headers=h).json() == []


def test_aluno_que_saiu_nao_recebe_presenca_depois_da_saida(client, h, classe, alunos):
    ana = alunos[0]
    client.delete(url(classe, "alunos", ana["id"]), headers=h)
    # saiu hoje: não pode ter presença numa data posterior a hoje (data futura é recusada),
    # mas pode numa data anterior, que é o histórico
    antes = (HOJE - timedelta(days=7)).isoformat()
    r = client.post(
        url(classe, "aulas"), headers=h,
        json={"data": antes, "presencas": [{"aluno_id": ana["id"], "status": "P"}]},
    )
    assert r.status_code == 201, r.text


def test_alterar_data_e_licao_da_aula(client, h, classe):
    aula = client.post(url(classe, "aulas"), headers=h, json={"data": HOJE.isoformat(), "licao": "A"}).json()
    outra = client.post(url(classe, "aulas"), headers=h, json={"data": (HOJE - timedelta(days=7)).isoformat()}).json()
    r = client.patch(url(classe, "aulas", aula["id"]), headers=h, json={"data": outra["data"]})
    assert r.status_code == 409
    r = client.patch(url(classe, "aulas", aula["id"]), headers=h, json={"licao": None})
    assert (r.status_code, r.json()["licao"]) == (200, None)
    assert client.patch(url(classe, "aulas", aula["id"]), headers=h, json={}).status_code == 422


# ---------- frequência ----------

def test_frequencia_por_aluno_e_periodo(client, h, classe, alunos):
    ana, bruno, _ = alunos
    datas = [HOJE - timedelta(days=14), HOJE - timedelta(days=7), HOJE]
    status = {datas[0]: ("P", "A"), datas[1]: ("P", "J"), datas[2]: ("A", None)}
    for d, (sa, sb) in status.items():
        itens = [{"aluno_id": ana["id"], "status": sa}] + ([{"aluno_id": bruno["id"], "status": sb}] if sb else [])
        assert client.post(url(classe, "aulas"), headers=h, json={"data": d.isoformat(), "presencas": itens}).status_code == 201

    f = client.get(url(classe, "frequencia"), headers=h).json()
    assert f["total_aulas"] == 3
    por_nome = {a["nome"]: a for a in f["alunos"]}
    assert (por_nome["Ana"]["presentes"], por_nome["Ana"]["ausentes"], por_nome["Ana"]["percentual_presenca"]) == (2, 1, 66.7)
    assert (por_nome["Bruno"]["justificados"], por_nome["Bruno"]["sem_registro"]) == (1, 1)
    assert por_nome["Carla"]["percentual_presenca"] is None and por_nome["Carla"]["sem_registro"] == 3

    f = client.get(url(classe, "frequencia"), headers=h, params={"de": datas[1].isoformat()}).json()
    assert f["total_aulas"] == 2
    r = client.get(url(classe, "frequencia"), headers=h, params={"de": datas[2].isoformat(), "ate": datas[0].isoformat()})
    assert r.status_code == 400


def test_aluno_que_saiu_so_aparece_na_frequencia_se_teve_presenca(client, h, classe, alunos):
    ana, bruno, _ = alunos
    client.post(url(classe, "aulas"), headers=h, json={
        "data": (HOJE - timedelta(days=7)).isoformat(), "presencas": [{"aluno_id": ana["id"], "status": "P"}]})
    client.delete(url(classe, "alunos", ana["id"]), headers=h)
    client.delete(url(classe, "alunos", bruno["id"]), headers=h)
    nomes = [a["nome"] for a in client.get(url(classe, "frequencia"), headers=h).json()["alunos"]]
    assert nomes == ["Ana", "Carla"]


# ---------- comunicados para professores ----------

def test_comunicado_para_professores_da_ebd(client, h, professor, conta, classe):
    c = client.post(
        "/comunicados", headers=h,
        json={"titulo": "Reunião de professores", "corpo": "Sábado às 9h.", "categoria": "aviso", "publico": "professores_ebd"},
    ).json()
    client.post(f"/comunicados/{c['id']}/publicar", headers=h, json={})

    ids = lambda quem: [x["id"] for x in client.get("/comunicados", headers=quem.h).json()["items"]]  # noqa: E731
    assert ids(professor) == [c["id"]]
    assert client.get(f"/comunicados/{c['id']}", headers=professor.h).status_code == 200
    assert ids(conta()) == []

    # encerrado o exercício, deixa de ler
    p = client.get(url(classe, "professores"), headers=h).json()[0]
    client.patch(url(classe, "professores", p["id"]), headers=h, json={"fim": HOJE.isoformat()})
    assert ids(professor) == []


def test_professor_de_classe_desativada_nao_le_comunicado_de_professores(client, h, professor, classe):
    c = client.post(
        "/comunicados", headers=h,
        json={"titulo": "Aviso", "corpo": "Texto.", "categoria": "aviso", "publico": "professores_ebd"},
    ).json()
    client.post(f"/comunicados/{c['id']}/publicar", headers=h, json={})
    client.patch(url(classe), headers=h, json={"ativa": False})
    assert client.get("/comunicados", headers=professor.h).json()["items"] == []
