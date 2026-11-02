import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from core.database import SessionLocal
from models import EventoEclesiastico, LogAuditoria, Membro
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
    def _novo(headers=None, **campos):
        corpo = {"nome": "Maria Silva", "rol": "C", **campos}
        r = client.post("/membros", headers=headers or h, json=corpo)
        assert r.status_code == 201, r.text
        return r.json()

    return _novo


def evento(client, h, membro_id, **campos):
    corpo = {"data": "2024-05-01", "ata_conselho": "Ata 10/2024", **campos}
    return client.post(f"/membros/{membro_id}/eventos", headers=h, json=corpo)


def auditoria(acao):
    with SessionLocal() as db:
        return list(db.scalars(select(LogAuditoria).where(LogAuditoria.acao == acao)))


# ---------- cadastro e numeração ----------

def test_numero_do_rol_e_sequencial_por_igreja(
    client, novo_membro, criar_igreja, criar_usuario, auth, h
):
    assert [novo_membro(nome=n)["numero_rol"] for n in ("A", "B", "C")] == [1, 2, 3]

    b = criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN)
    assert novo_membro(headers=auth(b), nome="X")["numero_rol"] == 1


def test_numero_explicito_duplicado_da_conflito(client, h, novo_membro):
    novo_membro(numero_rol=10)
    r = client.post("/membros", headers=h, json={"nome": "Outro", "rol": "C", "numero_rol": 10})
    assert r.status_code == 409
    # O próximo automático continua depois do maior
    assert novo_membro(nome="Seguinte")["numero_rol"] == 11


def test_alterar_numero_do_rol_para_um_em_uso_da_conflito_e_audita(client, h, novo_membro):
    a = novo_membro(nome="A")
    b = novo_membro(nome="B")
    r = client.patch(f"/membros/{b['id']}", headers=h, json={"numero_rol": a["numero_rol"]})
    assert r.status_code == 409

    ok = client.patch(f"/membros/{b['id']}", headers=h, json={"numero_rol": 50})
    assert ok.status_code == 200 and ok.json()["numero_rol"] == 50
    assert auditoria("numero_rol_alterado")[0].detalhes == {"de": 2, "para": 50}


def test_dados_invalidos(client, h):
    futuro = (date.today() + timedelta(days=1)).isoformat()
    assert client.post(
        "/membros", headers=h, json={"nome": "A", "rol": "C", "data_nascimento": futuro}
    ).status_code == 422
    assert client.post("/membros", headers=h, json={"nome": "A", "rol": "X"}).status_code == 422
    assert client.post("/membros", headers=h, json={"nome": "", "rol": "C"}).status_code == 422


def test_patch_nao_altera_situacao_rol_nem_oficio(client, h, novo_membro):
    m = novo_membro()
    r = client.patch(
        f"/membros/{m['id']}",
        headers=h,
        json={"telefone": "11 99999-0000", "situacao": "falecido", "rol": "NC", "oficio": "diacono"},
    )
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["telefone"] == "11 99999-0000"
    assert (corpo["situacao"], corpo["rol"], corpo["oficio"]) == ("ativo", "C", "nenhum")


# ---------- exclusão lógica ----------

def test_excluir_remove_do_rol_mas_mantem_a_linha_e_audita(client, h, novo_membro):
    m = novo_membro(nome="Cadastro Errado")
    assert client.delete(f"/membros/{m['id']}", headers=h).status_code == 204

    assert client.get(f"/membros/{m['id']}", headers=h).status_code == 404
    assert client.patch(f"/membros/{m['id']}", headers=h, json={"nome": "X"}).status_code == 404
    assert client.get(f"/membros/{m['id']}/eventos", headers=h).status_code == 404
    assert client.get("/membros", headers=h).json()["total"] == 0
    assert "Cadastro Errado" not in client.get("/membros/exportar", headers=h).text

    with SessionLocal() as db:
        linha = db.get(Membro, uuid.UUID(m["id"]))
        assert linha is not None and linha.excluido_em is not None
    log = auditoria("membro_excluido")
    assert len(log) == 1 and log[0].detalhes["nome"] == "Cadastro Errado"


def test_excluir_duas_vezes_da_404(client, h, novo_membro):
    m = novo_membro()
    assert client.delete(f"/membros/{m['id']}", headers=h).status_code == 204
    assert client.delete(f"/membros/{m['id']}", headers=h).status_code == 404


def test_excluir_preserva_os_eventos_do_membro(client, h, novo_membro):
    m = novo_membro()
    assert evento(client, h, m["id"], tipo="profissao_fe").status_code == 201
    assert client.delete(f"/membros/{m['id']}", headers=h).status_code == 204
    with SessionLocal() as db:
        assert db.scalar(select(EventoEclesiastico).where(EventoEclesiastico.membro_id == uuid.UUID(m["id"])))


def test_numero_do_rol_de_cadastro_excluido_volta_a_ficar_livre(client, h, novo_membro):
    a = novo_membro(numero_rol=7)
    assert client.delete(f"/membros/{a['id']}", headers=h).status_code == 204
    b = novo_membro(nome="Outra Pessoa", numero_rol=7)
    assert b["numero_rol"] == 7


def test_numero_automatico_ignora_cadastros_excluidos(client, h, novo_membro):
    novo_membro(numero_rol=1)
    ultimo = novo_membro(numero_rol=2)
    assert client.delete(f"/membros/{ultimo['id']}", headers=h).status_code == 204
    assert novo_membro()["numero_rol"] == 2


def test_excluir_desvincula_a_conta_de_usuario(client, auth, h, admin, criar_usuario, igreja, novo_membro):
    m = novo_membro()
    outro = criar_usuario(igreja, "vinculado@a.org", perfil=PerfilUsuario.USUARIO)
    r = client.patch(f"/usuarios/{outro.id}", headers=h, json={"membro_id": m["id"]})
    assert r.status_code == 200, r.text

    assert client.delete(f"/membros/{m['id']}", headers=h).status_code == 204
    lista = client.get("/usuarios", headers=h).json()
    assert next(u for u in lista if u["email"] == "vinculado@a.org")["membro_id"] is None
    assert auditoria("membro_excluido")[0].detalhes["contas_desvinculadas"] == 1


def test_nao_vincula_usuario_a_membro_excluido(client, h, admin, criar_usuario, igreja, novo_membro):
    m = novo_membro()
    client.delete(f"/membros/{m['id']}", headers=h)
    outro = criar_usuario(igreja, "x@a.org", perfil=PerfilUsuario.USUARIO)
    r = client.patch(f"/usuarios/{outro.id}", headers=h, json={"membro_id": m["id"]})
    assert r.status_code == 404


def test_presbitero_nao_exclui_membro(client, auth, criar_usuario, igreja, novo_membro):
    presb = criar_usuario(igreja, "p@a.org", perfil=PerfilUsuario.PRESBITERO)
    m = novo_membro()
    assert client.delete(f"/membros/{m['id']}", headers=auth(presb)).status_code == 403
    assert client.get(f"/membros/{m['id']}", headers=auth(presb)).status_code == 200


def test_pastor_exclui_membro(client, auth, criar_usuario, igreja, novo_membro):
    pastor = criar_usuario(igreja, "pastor@a.org", perfil=PerfilUsuario.PASTOR)
    m = novo_membro()
    assert client.delete(f"/membros/{m['id']}", headers=auth(pastor)).status_code == 204


def test_outra_igreja_nao_exclui_membro(client, h, novo_membro, criar_igreja, criar_usuario, auth):
    m = novo_membro()
    intruso = criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN)
    assert client.delete(f"/membros/{m['id']}", headers=auth(intruso)).status_code == 404
    assert client.get(f"/membros/{m['id']}", headers=h).status_code == 200


def test_excluir_exige_autenticacao(client, novo_membro):
    m = novo_membro()
    assert client.delete(f"/membros/{m['id']}").status_code == 401


# ---------- busca ----------

def test_busca_filtra_e_pagina(client, h, novo_membro):
    novo_membro(nome="Ana Souza", rol="C")
    novo_membro(nome="Ana Lima", rol="NC")
    novo_membro(nome="Bruno Alves", rol="C")

    r = client.get("/membros", headers=h, params={"q": "ana"}).json()
    assert r["total"] == 2
    assert [m["nome"] for m in r["items"]] == ["Ana Lima", "Ana Souza"]

    assert client.get("/membros", headers=h, params={"rol": "C"}).json()["total"] == 2

    p = client.get("/membros", headers=h, params={"limit": 2, "offset": 2}).json()
    assert p["total"] == 3 and len(p["items"]) == 1 and p["limit"] == 2

    # '%' é literal, não curinga
    assert client.get("/membros", headers=h, params={"q": "%"}).json()["total"] == 0


# ---------- permissões e isolamento ----------

def test_usuario_comum_nao_acessa_o_rol(client, auth, criar_usuario, igreja, novo_membro):
    m = novo_membro()
    comum = criar_usuario(igreja, "c@a.org")
    hc = auth(comum)
    assert client.get("/membros", headers=hc).status_code == 403
    assert client.get(f"/membros/{m['id']}", headers=hc).status_code == 403
    assert client.get("/familias", headers=hc).status_code == 403
    assert client.get("/membros/me", headers=hc).status_code == 404  # sem vínculo


def test_outra_igreja_nao_ve_nem_altera_membros(
    client, h, novo_membro, criar_igreja, criar_usuario, auth
):
    m = novo_membro()
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))

    assert client.get(f"/membros/{m['id']}", headers=hb).status_code == 404
    assert client.patch(f"/membros/{m['id']}", headers=hb, json={"nome": "X"}).status_code == 404
    assert client.get(f"/membros/{m['id']}/eventos", headers=hb).status_code == 404
    assert evento(client, hb, m["id"], tipo="batismo").status_code == 404
    assert client.get("/membros", headers=hb).json()["total"] == 0


def test_familia_de_outra_igreja_e_recusada(client, novo_membro, criar_igreja, criar_usuario, auth, h):
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    fam_b = client.post("/familias", headers=hb, json={"nome": "Silva"}).json()
    r = client.post(
        "/membros", headers=h, json={"nome": "A", "rol": "C", "familia_id": fam_b["id"]}
    )
    assert r.status_code == 404


# ---------- famílias ----------

def test_familia_crud_e_excluir_mantem_membros(client, h, novo_membro):
    f = client.post("/familias", headers=h, json={"nome": "Silva", "endereco": "Rua 1"}).json()
    m = novo_membro(familia_id=f["id"])

    assert client.patch(f"/familias/{f['id']}", headers=h, json={"nome": "Silva Souza"}).json()[
        "nome"
    ] == "Silva Souza"
    assert client.get("/membros", headers=h, params={"familia_id": f["id"]}).json()["total"] == 1

    assert client.delete(f"/familias/{f['id']}", headers=h).status_code == 204
    assert client.get(f"/familias/{f['id']}", headers=h).status_code == 404
    assert client.get(f"/membros/{m['id']}", headers=h).json()["familia_id"] is None


# ---------- eventos eclesiásticos ----------

def test_profissao_de_fe_torna_comungante_e_registra_historico(client, h, novo_membro):
    m = novo_membro(rol="NC")
    r = evento(client, h, m["id"], tipo="profissao_fe")
    assert r.status_code == 201
    assert r.json()["membro"]["rol"] == "C"
    assert r.json()["evento"]["tipo"] == "profissao_fe"

    historico = client.get(f"/membros/{m['id']}/eventos", headers=h).json()
    assert [e["tipo"] for e in historico] == ["profissao_fe"]

    log = auditoria("evento_eclesiastico_registrado")[0]
    assert log.detalhes["alteracoes"] == {"rol": {"de": "NC", "para": "C"}}


def test_batismo_nao_exige_ata_nem_altera_membro(client, h, novo_membro):
    m = novo_membro(rol="NC")
    r = client.post(
        f"/membros/{m['id']}/eventos", headers=h, json={"tipo": "batismo", "data": "2010-01-10"}
    )
    assert r.status_code == 201
    assert r.json()["membro"]["rol"] == "NC"


@pytest.mark.parametrize(
    "tipo", ["profissao_fe", "recepcao", "ordenacao", "disciplina", "restauracao", "saida"]
)
def test_demais_eventos_exigem_ata(client, h, novo_membro, tipo):
    m = novo_membro()
    r = client.post(f"/membros/{m['id']}/eventos", headers=h, json={"tipo": tipo, "data": "2024-01-01"})
    assert r.status_code == 400 and "ata" in r.json()["detail"].lower()


def test_evento_com_data_futura_e_recusado(client, h, novo_membro):
    m = novo_membro()
    futuro = (date.today() + timedelta(days=2)).isoformat()
    assert evento(client, h, m["id"], tipo="batismo", data=futuro).status_code == 422


def test_ciclo_disciplina_e_restauracao(client, h, novo_membro):
    m = novo_membro()
    assert evento(client, h, m["id"], tipo="restauracao").status_code == 409  # não está em disciplina

    r = evento(client, h, m["id"], tipo="disciplina")
    assert r.json()["membro"]["situacao"] == "em_disciplina"
    assert evento(client, h, m["id"], tipo="disciplina").status_code == 409
    assert evento(client, h, m["id"], tipo="ordenacao", oficio="diacono").status_code == 409

    r = evento(client, h, m["id"], tipo="restauracao")
    assert r.json()["membro"]["situacao"] == "ativo"


def test_ordenacao(client, h, novo_membro):
    comungante = novo_membro(rol="C")
    crianca = novo_membro(nome="Criança", rol="NC")

    assert evento(client, h, comungante["id"], tipo="ordenacao").status_code == 400  # sem ofício
    assert evento(
        client, h, comungante["id"], tipo="ordenacao", oficio="nenhum"
    ).status_code == 400
    assert evento(client, h, crianca["id"], tipo="ordenacao", oficio="diacono").status_code == 409

    r = evento(client, h, comungante["id"], tipo="ordenacao", oficio="presbitero")
    assert r.status_code == 201 and r.json()["membro"]["oficio"] == "presbitero"
    assert r.json()["evento"]["oficio"] == "presbitero"


def test_recepcao_exige_forma_e_reativa_membro_transferido(client, h, novo_membro):
    m = novo_membro()
    r = evento(client, h, m["id"], tipo="saida", situacao_resultante="transferido")
    assert r.json()["membro"]["situacao"] == "transferido"

    # Fora do rol, só a recepção é aceita
    assert evento(client, h, m["id"], tipo="disciplina").status_code == 409
    assert evento(client, h, m["id"], tipo="recepcao").status_code == 400  # sem forma

    r = evento(
        client, h, m["id"], tipo="recepcao",
        forma_recepcao="transferencia", igreja_relacionada="IPB Central",
    )
    assert r.status_code == 201
    assert r.json()["membro"]["situacao"] == "ativo"
    assert r.json()["evento"]["igreja_relacionada"] == "IPB Central"


def test_saida_exige_motivo_e_falecido_encerra_o_historico(client, h, novo_membro):
    m = novo_membro()
    assert evento(client, h, m["id"], tipo="saida").status_code == 400
    assert evento(client, h, m["id"], tipo="saida", situacao_resultante="ativo").status_code == 400

    assert evento(client, h, m["id"], tipo="saida", situacao_resultante="falecido").status_code == 201
    assert evento(client, h, m["id"], tipo="recepcao", forma_recepcao="jurisdicao").status_code == 409


def test_campos_que_nao_se_aplicam_ao_tipo_sao_recusados(client, h, novo_membro):
    m = novo_membro()
    assert evento(client, h, m["id"], tipo="batismo", forma_recepcao="transferencia").status_code == 400
    assert evento(client, h, m["id"], tipo="disciplina", oficio="diacono").status_code == 400
    assert evento(
        client, h, m["id"], tipo="batismo", situacao_resultante="falecido"
    ).status_code == 400


def test_evento_invalido_nao_deixa_rastro(client, h, novo_membro):
    m = novo_membro()
    evento(client, h, m["id"], tipo="restauracao")  # 409
    with SessionLocal() as db:
        assert db.scalars(select(EventoEclesiastico)).first() is None
    assert auditoria("evento_eclesiastico_registrado") == []


# ---------- vínculo usuário × membro ----------

def test_vinculo_entre_usuario_e_membro(client, auth, h, admin, criar_usuario, igreja, novo_membro):
    m = novo_membro(nome="Pedro")
    outra = criar_usuario(igreja, "pedro@a.org")

    r = client.patch(f"/usuarios/{outra.id}", headers=h, json={"membro_id": m["id"]})
    assert r.status_code == 200 and r.json()["membro_id"] == m["id"]
    assert client.get("/membros/me", headers=auth(outra)).json()["nome"] == "Pedro"

    # Um membro, uma conta
    segundo = criar_usuario(igreja, "outro@a.org")
    r = client.patch(f"/usuarios/{segundo.id}", headers=h, json={"membro_id": m["id"]})
    assert r.status_code == 409

    # Desvincular com null explícito
    r = client.patch(f"/usuarios/{outra.id}", headers=h, json={"membro_id": None})
    assert r.status_code == 200 and r.json()["membro_id"] is None
    assert {"membro_vinculado"} <= {l.acao for l in auditoria("membro_vinculado")}


def test_nao_vincula_membro_de_outra_igreja(client, h, criar_usuario, criar_igreja, igreja, auth):
    hb = auth(criar_usuario(criar_igreja("Igreja B"), "admin@b.org", perfil=ADMIN))
    m_b = client.post("/membros", headers=hb, json={"nome": "Z", "rol": "C"}).json()
    alvo = criar_usuario(igreja, "alvo@a.org")
    r = client.patch(f"/usuarios/{alvo.id}", headers=h, json={"membro_id": m_b["id"]})
    assert r.status_code == 404


def test_admin_pode_vincular_a_si_mesmo(client, h, admin, novo_membro):
    m = novo_membro()
    r = client.patch(f"/usuarios/{admin.id}", headers=h, json={"membro_id": m["id"]})
    assert r.status_code == 200
    assert client.get("/membros/me", headers=h).json()["id"] == m["id"]


# ---------- exportação ----------

def test_exportar_csv_respeita_filtros_neutraliza_formulas_e_audita(client, h, novo_membro):
    novo_membro(nome="=HYPERLINK(\"http://x\")", rol="C")
    novo_membro(nome="Joana", rol="NC")

    r = client.get("/membros/exportar", headers=h, params={"rol": "C"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    linhas = r.text.lstrip("﻿").splitlines()
    assert linhas[0].startswith("numero_rol;nome;rol")
    assert len(linhas) == 2
    assert "'=HYPERLINK" in linhas[1]  # prefixado: não vira fórmula
    assert auditoria("rol_exportado")[0].detalhes == {"registros": 1}


def test_exportar_exige_perfil_de_oficial(client, auth, criar_usuario, igreja):
    comum = criar_usuario(igreja, "c@a.org")
    assert client.get("/membros/exportar", headers=auth(comum)).status_code == 403
