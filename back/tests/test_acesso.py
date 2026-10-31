from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from core.database import SessionLocal
from models import LogAuditoria, TokenRedefinicao, Usuario
from models.enums import PerfilUsuario, StatusUsuario

ADMIN = PerfilUsuario.ADMIN
PASTOR = PerfilUsuario.PASTOR
COMUM = PerfilUsuario.USUARIO


@pytest.fixture
def igreja(criar_igreja):
    return criar_igreja("Igreja A")


@pytest.fixture
def admin(criar_usuario, igreja):
    return criar_usuario(igreja, "admin@a.org", perfil=ADMIN)


def acoes_auditadas():
    with SessionLocal() as db:
        return [l.acao for l in db.scalars(select(LogAuditoria).order_by(LogAuditoria.criado_em))]


def usuario_db(usuario_id) -> Usuario:
    with SessionLocal() as db:
        return db.get(Usuario, usuario_id)


# ---------- login e bloqueio ----------

def test_login_ok_retorna_tokens_e_registra_ultimo_acesso(login, admin):
    r = login(admin)
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["access_token"] and corpo["refresh_token"]
    assert corpo["troca_obrigatoria"] is False
    assert usuario_db(admin.id).ultimo_acesso is not None


def test_login_senha_errada_e_email_inexistente_dao_a_mesma_resposta(login, admin):
    errada = login(admin, senha="outra-senha-123")
    inexistente = login(type("U", (), {"email": "x@y.org", "senha": "abc12345"})())
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json()


def test_bloqueia_apos_tentativas_falhas_e_registra_auditoria(login, admin):
    from core.config import settings

    for _ in range(settings.MAX_TENTATIVAS_LOGIN):
        assert login(admin, senha="errada-errada").status_code == 401

    assert usuario_db(admin.id).status == StatusUsuario.BLOQUEADO
    # Mesmo com a senha certa, a conta bloqueada não entra
    assert login(admin).status_code == 401
    assert "login_bloqueado" in acoes_auditadas()


def test_login_com_sucesso_zera_tentativas(login, admin):
    login(admin, senha="errada-errada")
    login(admin, senha="errada-errada")
    assert login(admin).status_code == 200
    assert usuario_db(admin.id).tentativas_falhas == 0


@pytest.mark.parametrize("status", [StatusUsuario.DESATIVADO, StatusUsuario.CONVITE_PENDENTE])
def test_conta_nao_ativa_nao_entra(login, criar_usuario, igreja, status):
    u = criar_usuario(igreja, "x@a.org", status=status)
    assert login(u).status_code == 401


# ---------- troca obrigatória ----------

def test_troca_obrigatoria_bloqueia_rotas_ate_trocar_a_senha(client, login, criar_usuario, igreja):
    u = criar_usuario(igreja, "novo@a.org", troca_obrigatoria=True)
    r = login(u)
    assert r.json()["troca_obrigatoria"] is True
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}

    assert client.get("/usuarios/me", headers=h).status_code == 200  # cliente precisa ler a flag
    assert client.get("/igreja", headers=h).status_code == 403

    r = client.post(
        "/auth/change-password",
        headers=h,
        json={"current_password": u.senha, "new_password": "NovaSenha@999"},
    )
    assert r.status_code == 204
    assert client.get("/igreja", headers=h).status_code == 200
    assert "senha_alterada" in acoes_auditadas()


def test_troca_de_senha_exige_senha_atual(client, auth, admin):
    r = client.post(
        "/auth/change-password",
        headers=auth(admin),
        json={"current_password": "errada-errada", "new_password": "NovaSenha@999"},
    )
    assert r.status_code == 401


# ---------- esqueci / redefinir senha ----------

def test_esqueci_senha_nao_revela_se_o_email_existe(client, mailer, admin):
    r1 = client.post("/auth/esqueci-senha", json={"email": admin.email})
    r2 = client.post("/auth/esqueci-senha", json={"email": "ninguem@x.org"})
    assert r1.status_code == r2.status_code == 204
    assert [m[0] for m in mailer.enviados] == [admin.email]


def test_redefinir_senha_uso_unico_e_encerra_sessoes(client, mailer, login, admin):
    refresh = login(admin).json()["refresh_token"]
    client.post("/auth/esqueci-senha", json={"email": admin.email})
    token = mailer.ultimo_token()

    r = client.post("/auth/redefinir-senha", json={"token": token, "nova_senha": "Nova@Senha123"})
    assert r.status_code == 204
    assert login(admin).status_code == 401  # senha antiga
    assert login(admin, senha="Nova@Senha123").status_code == 200
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 401
    assert "senha_redefinida" in acoes_auditadas()

    reuso = client.post("/auth/redefinir-senha", json={"token": token, "nova_senha": "Outra@Senha1"})
    assert reuso.status_code == 400


def test_token_expirado_ou_inventado_e_recusado(client, mailer, admin):
    client.post("/auth/esqueci-senha", json={"email": admin.email})
    token = mailer.ultimo_token()
    with SessionLocal() as db:
        t = db.scalar(select(TokenRedefinicao))
        t.expira_em = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    for tk in (token, "token-inventado"):
        r = client.post("/auth/redefinir-senha", json={"token": tk, "nova_senha": "Nova@Senha123"})
        assert r.status_code == 400


def test_token_guardado_apenas_como_hash(client, mailer, admin):
    client.post("/auth/esqueci-senha", json={"email": admin.email})
    token = mailer.ultimo_token()
    with SessionLocal() as db:
        guardado = db.scalar(select(TokenRedefinicao)).token_hash
    assert guardado != token and len(guardado) == 64


def test_novo_link_invalida_o_anterior(client, mailer, admin):
    client.post("/auth/esqueci-senha", json={"email": admin.email})
    primeiro = mailer.ultimo_token()
    client.post("/auth/esqueci-senha", json={"email": admin.email})
    r = client.post("/auth/redefinir-senha", json={"token": primeiro, "nova_senha": "Nova@Senha123"})
    assert r.status_code == 400


def test_conta_bloqueada_nao_redefine_senha(client, mailer, criar_usuario, igreja):
    u = criar_usuario(igreja, "b@a.org")
    client.post("/auth/esqueci-senha", json={"email": u.email})
    token = mailer.ultimo_token()
    with SessionLocal() as db:
        db.get(Usuario, u.id).status = StatusUsuario.BLOQUEADO
        db.commit()
    r = client.post("/auth/redefinir-senha", json={"token": token, "nova_senha": "Nova@Senha123"})
    assert r.status_code == 400
    assert usuario_db(u.id).status == StatusUsuario.BLOQUEADO


# ---------- convite ----------

def test_convite_ponta_a_ponta(client, mailer, auth, login, admin):
    r = client.post(
        "/usuarios", headers=auth(admin), json={"email": "Novo@A.org", "perfil": "pastor"}
    )
    assert r.status_code == 201
    novo = r.json()
    assert novo["email"] == "novo@a.org"
    assert novo["status"] == "convite_pendente" and novo["perfil"] == "pastor"
    assert novo["igreja_id"] == str(admin.igreja_id)
    assert mailer.enviados[-1][0] == "novo@a.org"

    client.post(
        "/auth/redefinir-senha", json={"token": mailer.ultimo_token(), "nova_senha": "Minha@Senha1"}
    )
    ok = client.post("/auth/login", data={"username": "novo@a.org", "password": "Minha@Senha1"})
    assert ok.status_code == 200
    assert usuario_db(novo["id"]).status == StatusUsuario.ATIVO
    assert {"usuario_criado", "convite_aceito"} <= set(acoes_auditadas())


def test_convite_com_email_repetido_da_conflito(client, auth, admin):
    r = client.post("/usuarios", headers=auth(admin), json={"email": admin.email})
    assert r.status_code == 409


def test_reenviar_convite_so_para_pendentes(client, mailer, auth, admin, criar_usuario, igreja):
    pendente = criar_usuario(igreja, "p@a.org", status=StatusUsuario.CONVITE_PENDENTE)
    ativo = criar_usuario(igreja, "ok@a.org")
    h = auth(admin)
    assert client.post(f"/usuarios/{pendente.id}/convite", headers=h).status_code == 204
    assert mailer.enviados[-1][0] == "p@a.org"
    assert client.post(f"/usuarios/{ativo.id}/convite", headers=h).status_code == 409


# ---------- permissões por perfil ----------

def test_listagem_depende_do_perfil(client, auth, criar_usuario, igreja, admin):
    comum = criar_usuario(igreja, "c@a.org", perfil=COMUM)
    pastor = criar_usuario(igreja, "p@a.org", perfil=PASTOR)
    assert client.get("/usuarios", headers=auth(comum)).status_code == 403
    r = client.get("/usuarios", headers=auth(pastor))
    assert r.status_code == 200 and len(r.json()) == 3


def test_apenas_admin_gerencia_usuarios_e_igreja(client, auth, criar_usuario, igreja):
    pastor = criar_usuario(igreja, "p@a.org", perfil=PASTOR)
    alvo = criar_usuario(igreja, "alvo@a.org")
    h = auth(pastor)
    assert client.post("/usuarios", headers=h, json={"email": "z@a.org"}).status_code == 403
    assert client.patch(f"/usuarios/{alvo.id}", headers=h, json={"perfil": "admin"}).status_code == 403
    assert client.patch("/igreja", headers=h, json={"nome": "Outro"}).status_code == 403


def test_rotas_exigem_autenticacao(client):
    assert client.get("/usuarios/me").status_code == 401
    assert client.get("/igreja").status_code == 401


def test_admin_nao_altera_a_propria_conta(client, auth, admin):
    r = client.patch(f"/usuarios/{admin.id}", headers=auth(admin), json={"status": "desativado"})
    assert r.status_code == 403


# ---------- alteração de perfil/status ----------

def test_mudar_perfil_audita_e_derruba_sessoes(client, auth, login, admin, criar_usuario, igreja):
    alvo = criar_usuario(igreja, "alvo@a.org")
    refresh = login(alvo).json()["refresh_token"]

    r = client.patch(f"/usuarios/{alvo.id}", headers=auth(admin), json={"perfil": "presbitero"})
    assert r.status_code == 200 and r.json()["perfil"] == "presbitero"
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 401

    with SessionLocal() as db:
        log = db.scalar(select(LogAuditoria).where(LogAuditoria.acao == "perfil_alterado"))
    assert log.usuario_id == admin.id and log.entidade_id == alvo.id
    assert log.detalhes == {"de": "usuario", "para": "presbitero"}


def test_admin_desbloqueia_usuario_e_zera_tentativas(client, auth, login, admin, criar_usuario, igreja):
    alvo = criar_usuario(igreja, "alvo@a.org")
    for _ in range(5):
        login(alvo, senha="errada-errada")
    assert login(alvo).status_code == 401

    r = client.patch(f"/usuarios/{alvo.id}", headers=auth(admin), json={"status": "ativo"})
    assert r.status_code == 200
    assert login(alvo).status_code == 200


def test_status_convite_pendente_nao_e_atribuivel(client, auth, admin, criar_usuario, igreja):
    alvo = criar_usuario(igreja, "alvo@a.org")
    r = client.patch(f"/usuarios/{alvo.id}", headers=auth(admin), json={"status": "convite_pendente"})
    assert r.status_code == 409


def test_patch_vazio_e_recusado(client, auth, admin, criar_usuario, igreja):
    alvo = criar_usuario(igreja, "alvo@a.org")
    assert client.patch(f"/usuarios/{alvo.id}", headers=auth(admin), json={}).status_code == 422


# ---------- atualização de dados do usuário ----------

def test_usuario_troca_o_proprio_email_com_a_senha_atual(client, auth, login, criar_usuario, igreja):
    u = criar_usuario(igreja, "velho@a.org")
    h = auth(u)
    refresh = login(u).json()["refresh_token"]

    r = client.patch("/usuarios/me", headers=h, json={"email": "Novo@A.org", "senha_atual": u.senha})
    assert r.status_code == 200 and r.json()["email"] == "novo@a.org"
    assert client.post("/auth/refresh", json={"refresh_token": refresh}).status_code == 401
    ok = client.post("/auth/login", data={"username": "novo@a.org", "password": u.senha})
    assert ok.status_code == 200
    assert "email_alterado" in acoes_auditadas()


def test_troca_do_proprio_email_exige_senha_correta(client, auth, criar_usuario, igreja):
    u = criar_usuario(igreja, "velho@a.org")
    r = client.patch(
        "/usuarios/me", headers=auth(u), json={"email": "novo@a.org", "senha_atual": "errada-errada"}
    )
    assert r.status_code == 401
    assert usuario_db(u.id).email == "velho@a.org"


def test_troca_de_email_para_um_ja_cadastrado_da_conflito(client, auth, admin, criar_usuario, igreja):
    u = criar_usuario(igreja, "velho@a.org")
    r = client.patch(
        "/usuarios/me", headers=auth(u), json={"email": admin.email, "senha_atual": u.senha}
    )
    assert r.status_code == 409


def test_admin_troca_email_de_outro_usuario(client, auth, admin, criar_usuario, igreja):
    alvo = criar_usuario(igreja, "alvo@a.org")
    r = client.patch(f"/usuarios/{alvo.id}", headers=auth(admin), json={"email": "certo@a.org"})
    assert r.status_code == 200 and r.json()["email"] == "certo@a.org"


def test_corrigir_email_de_convite_pendente_reenvia_para_o_novo_endereco(
    client, mailer, auth, admin
):
    r = client.post("/usuarios", headers=auth(admin), json={"email": "errado@a.org"})
    antigo = mailer.ultimo_token()
    client.patch(f"/usuarios/{r.json()['id']}", headers=auth(admin), json={"email": "certo@a.org"})

    assert mailer.enviados[-1][0] == "certo@a.org"
    senha = {"nova_senha": "Nova@Senha123"}
    assert client.post("/auth/redefinir-senha", json={"token": antigo, **senha}).status_code == 400
    novo = mailer.ultimo_token()
    assert client.post("/auth/redefinir-senha", json={"token": novo, **senha}).status_code == 204


# ---------- isolamento entre igrejas ----------

def test_admin_de_outra_igreja_nao_ve_nem_altera(client, auth, criar_igreja, criar_usuario, admin, igreja):
    outra = criar_igreja("Igreja B")
    admin_b = criar_usuario(outra, "admin@b.org", perfil=ADMIN)
    alvo_a = criar_usuario(igreja, "alvo@a.org")
    h = auth(admin_b)

    emails = [u["email"] for u in client.get("/usuarios", headers=h).json()]
    assert emails == ["admin@b.org"]
    r = client.patch(f"/usuarios/{alvo_a.id}", headers=h, json={"perfil": "admin"})
    assert r.status_code == 404
    assert client.post(f"/usuarios/{alvo_a.id}/convite", headers=h).status_code == 404
    assert usuario_db(alvo_a.id).perfil == COMUM


def test_cada_admin_edita_so_a_propria_igreja(client, auth, criar_igreja, criar_usuario, admin):
    outra = criar_igreja("Igreja B")
    admin_b = criar_usuario(outra, "admin@b.org", perfil=ADMIN)
    client.patch("/igreja", headers=auth(admin_b), json={"nome": "B Renovada", "presbiterio": "P1"})

    assert client.get("/igreja", headers=auth(admin)).json()["nome"] == "Igreja A"
    corpo = client.get("/igreja", headers=auth(admin_b)).json()
    assert corpo["nome"] == "B Renovada" and corpo["presbiterio"] == "P1"
