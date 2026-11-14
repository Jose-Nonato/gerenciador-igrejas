from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select, text

from core.database import SessionLocal
from models import LogAuditoria
from models.enums import PerfilUsuario

TZ = ZoneInfo("America/Sao_Paulo")
PASTOR = PerfilUsuario.PASTOR
PRESBITERO = PerfilUsuario.PRESBITERO
ASSUNTO = "Estou passando por um momento difícil no casamento"


def dia_futuro(n: int = 3):
    return (datetime.now(TZ) + timedelta(days=n)).date()


# ---------- fixtures ----------

@pytest.fixture
def igreja(criar_igreja):
    return criar_igreja("Igreja A")


@pytest.fixture
def admin(criar_usuario, igreja):
    return criar_usuario(igreja, "admin@a.org", perfil=PerfilUsuario.ADMIN)


@pytest.fixture
def h(auth, admin):
    return auth(admin)


@pytest.fixture
def conta(client, auth, h, igreja, criar_usuario):
    """Usuário ligado a um membro (nome `Membro N`)."""
    contador = iter(range(1000))

    def _conta(perfil=PerfilUsuario.USUARIO, **membro):
        n = next(contador)
        u = criar_usuario(igreja, f"u{n}@a.org", perfil=perfil)
        r = client.post("/membros", headers=h, json={"nome": f"Membro {n}", "rol": "C", **membro})
        assert r.status_code == 201, r.text
        m = r.json()
        r = client.patch(f"/usuarios/{u.id}", headers=h, json={"membro_id": m["id"]})
        assert r.status_code == 200, r.text
        return SimpleNamespace(usuario=u, membro=m, h=auth(u), id=str(u.id))

    return _conta


@pytest.fixture
def pastor(conta):
    return conta(PASTOR)


@pytest.fixture
def membro(conta):
    return conta()


@pytest.fixture
def abrir_agenda(client):
    def _abrir(oficial, dia, inicio="09:00", fim="11:00", duracao=30, **extra):
        r = client.post(
            "/agenda/disponibilidades",
            headers=oficial.h,
            json={
                "dia_semana": dia.weekday(),
                "hora_inicio": inicio,
                "hora_fim": fim,
                "duracao_min": duracao,
                "modalidade": "presencial",
                "local": "Gabinete pastoral",
                **extra,
            },
        )
        assert r.status_code == 201, r.text
        return r.json()

    return _abrir


@pytest.fixture
def horarios(client):
    def _horarios(solicitante, oficial, dia):
        r = client.get(
            f"/agenda/oficiais/{oficial.id}/horarios",
            headers=solicitante.h,
            params={"de": dia.isoformat(), "ate": dia.isoformat()},
        )
        assert r.status_code == 200, r.text
        return r.json()

    return _horarios


@pytest.fixture
def pedir(client):
    def _pedir(solicitante, oficial, inicio, categoria="aconselhamento", assunto=ASSUNTO):
        return client.post(
            "/agenda/atendimentos",
            headers=solicitante.h,
            json={
                "oficial_id": oficial.id,
                "inicio": inicio,
                "categoria": categoria,
                "assunto": assunto,
            },
        )

    return _pedir


@pytest.fixture
def pedido(pastor, membro, abrir_agenda, horarios, pedir):
    """Um pedido já feito (status solicitado) para o primeiro horário de uma agenda aberta."""
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    inicio = horarios(membro, pastor, dia)[0]["inicio"]
    r = pedir(membro, pastor, inicio)
    assert r.status_code == 201, r.text
    return r.json()


def mover(atendimento_id: str, inicio: datetime) -> None:
    """Muda o horário direto no banco (a API não aceita marcar no passado)."""
    with SessionLocal() as db:
        db.execute(
            text("UPDATE atendimento SET inicio = :i, fim = :f WHERE id = :id"),
            {"i": inicio, "f": inicio + timedelta(minutes=30), "id": atendimento_id},
        )
        db.commit()


# ---------- fluxo ----------

def test_fluxo_completo(client, pastor, membro, abrir_agenda, horarios, pedir):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)

    livres = horarios(membro, pastor, dia)
    assert len(livres) == 4  # 09:00 às 11:00, de 30 em 30
    primeiro = datetime.fromisoformat(livres[0]["inicio"]).astimezone(TZ)
    assert (primeiro.hour, primeiro.minute) == (9, 0)
    assert livres[0]["modalidade"] == "presencial"
    assert livres[0]["local"] == "Gabinete pastoral"

    r = pedir(membro, pastor, livres[0]["inicio"])
    assert r.status_code == 201, r.text
    a = r.json()
    assert a["status"] == "solicitado"
    assert a["assunto"] == ASSUNTO
    assert a["solicitante_nome"] == membro.membro["nome"]
    assert a["oficial_nome"] == pastor.membro["nome"]
    assert len(horarios(membro, pastor, dia)) == 3  # o horário reservado sai da lista

    recebidos = client.get("/agenda/atendimentos/recebidos", headers=pastor.h).json()
    assert [x["id"] for x in recebidos] == [a["id"]]
    meus = client.get("/agenda/atendimentos/meus", headers=membro.h).json()
    assert [x["id"] for x in meus] == [a["id"]]

    r = client.post(f"/agenda/atendimentos/{a['id']}/confirmar", headers=pastor.h)
    assert r.status_code == 200 and r.json()["status"] == "confirmado"

    mover(a["id"], datetime.now(timezone.utc) - timedelta(hours=2))
    r = client.post(f"/agenda/atendimentos/{a['id']}/concluir", headers=pastor.h)
    assert r.status_code == 200 and r.json()["status"] == "realizado"


def test_faltou(client, pedido, pastor):
    client.post(f"/agenda/atendimentos/{pedido['id']}/confirmar", headers=pastor.h)
    mover(pedido["id"], datetime.now(timezone.utc) - timedelta(hours=1))
    r = client.post(f"/agenda/atendimentos/{pedido['id']}/faltou", headers=pastor.h)
    assert r.status_code == 200 and r.json()["status"] == "faltou"


def test_recusar_libera_o_horario(client, pedido, pastor, membro, horarios):
    dia = datetime.fromisoformat(pedido["inicio"]).astimezone(TZ).date()
    assert len(horarios(membro, pastor, dia)) == 3
    r = client.post(
        f"/agenda/atendimentos/{pedido['id']}/recusar",
        headers=pastor.h,
        json={"justificativa": "Estarei viajando"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "recusado"
    assert r.json()["justificativa"] == "Estarei viajando"
    assert len(horarios(membro, pastor, dia)) == 4


def test_presbitero_tambem_tem_agenda(client, conta, membro, abrir_agenda, horarios, pedir):
    presbitero = conta(PRESBITERO)
    dia = dia_futuro()
    abrir_agenda(presbitero, dia)
    oficiais = client.get("/agenda/oficiais", headers=membro.h).json()
    assert [o["id"] for o in oficiais] == [presbitero.id]
    assert oficiais[0]["perfil"] == "presbitero"
    r = pedir(membro, presbitero, horarios(membro, presbitero, dia)[0]["inicio"])
    assert r.status_code == 201


# ---------- regras de marcação ----------

def test_reserva_dupla_do_mesmo_horario(client, conta, pastor, membro, abrir_agenda, horarios, pedir):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    inicio = horarios(membro, pastor, dia)[0]["inicio"]
    assert pedir(membro, pastor, inicio).status_code == 201
    outro = conta()
    r = pedir(outro, pastor, inicio)
    assert r.status_code == 409


def test_horario_que_nao_existe_na_agenda(pastor, membro, abrir_agenda, pedir):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    quebrado = datetime.combine(dia, datetime.min.time().replace(hour=9, minute=10), TZ)
    assert pedir(membro, pastor, quebrado.isoformat()).status_code == 409
    sem_janela = datetime.combine(dia, datetime.min.time().replace(hour=15), TZ)
    assert pedir(membro, pastor, sem_janela.isoformat()).status_code == 409


def test_antecedencia_minima(pastor, membro, abrir_agenda, horarios, pedir):
    # Janela de hoje, quase toda dentro das próximas 24 h: nenhum horário é oferecido
    hoje = datetime.now(TZ).date()
    abrir_agenda(pastor, hoje, "00:00", "23:30")
    assert horarios(membro, pastor, hoje) == []
    agora = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    assert pedir(membro, pastor, (agora + timedelta(hours=2)).isoformat()).status_code == 409


def test_horizonte_maximo(client, pastor, membro, abrir_agenda, horarios):
    longe = dia_futuro(65)
    abrir_agenda(pastor, longe)
    assert horarios(membro, pastor, longe) == []
    r = client.get(
        f"/agenda/oficiais/{pastor.id}/horarios",
        headers=membro.h,
        params={"de": dia_futuro(1).isoformat(), "ate": dia_futuro(80).isoformat()},
    )
    assert r.status_code == 400


def test_limite_de_pedidos_pendentes(pastor, membro, abrir_agenda, horarios, pedir):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    livres = horarios(membro, pastor, dia)
    assert pedir(membro, pastor, livres[0]["inicio"]).status_code == 201
    assert pedir(membro, pastor, livres[1]["inicio"]).status_code == 201
    r = pedir(membro, pastor, livres[2]["inicio"])
    assert r.status_code == 409
    assert "aguardando" in r.json()["detail"]


def test_membro_nao_marca_duas_conversas_no_mesmo_horario(
    conta, pastor, membro, abrir_agenda, horarios, pedir
):
    presbitero = conta(PRESBITERO)
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    abrir_agenda(presbitero, dia)
    inicio = horarios(membro, pastor, dia)[0]["inicio"]
    assert pedir(membro, pastor, inicio).status_code == 201
    assert pedir(membro, presbitero, inicio).status_code == 409


def test_nao_agenda_consigo_mesmo(client, pastor, abrir_agenda, pedir):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    assert client.get("/agenda/oficiais", headers=pastor.h).json() == []
    r = client.get(f"/agenda/oficiais/{pastor.id}/horarios", headers=pastor.h)
    assert r.status_code == 400


def test_so_oficiais_ativos_com_agenda_aparecem(client, conta, membro, abrir_agenda):
    sem_agenda = conta(PRESBITERO)
    com_agenda = conta(PASTOR)
    abrir_agenda(com_agenda, dia_futuro())
    ids = [o["id"] for o in client.get("/agenda/oficiais", headers=membro.h).json()]
    assert ids == [com_agenda.id]
    assert sem_agenda.id not in ids


def test_oficial_inexistente_ou_nao_oficial(client, conta, membro, pedir):
    comum = conta()
    r = client.get(f"/agenda/oficiais/{comum.id}/horarios", headers=membro.h)
    assert r.status_code == 404
    r = pedir(membro, comum, datetime.now(timezone.utc).isoformat())
    assert r.status_code == 404


def test_conta_sem_membro_nao_solicita(client, igreja, criar_usuario, auth, pastor, abrir_agenda, horarios, pedir, membro):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    inicio = horarios(membro, pastor, dia)[0]["inicio"]
    sem_membro = criar_usuario(igreja, "solto@a.org")
    solto = SimpleNamespace(h=auth(sem_membro))
    assert pedir(solto, pastor, inicio).status_code == 403
    assert client.get("/agenda/atendimentos/meus", headers=solto.h).json() == []


def test_membro_fora_do_rol_nao_solicita(pastor, membro, abrir_agenda, horarios, pedir):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    inicio = horarios(membro, pastor, dia)[0]["inicio"]
    with SessionLocal() as db:
        db.execute(
            text("UPDATE membro SET situacao = 'transferido' WHERE id = :id"),
            {"id": membro.membro["id"]},
        )
        db.commit()
    assert pedir(membro, pastor, inicio).status_code == 409


# ---------- transições ----------

def test_transicoes_invalidas(client, pedido, pastor, membro):
    aid = pedido["id"]
    base = f"/agenda/atendimentos/{aid}"

    # só o oficial confirma, recusa e encerra
    assert client.post(f"{base}/confirmar", headers=membro.h).status_code == 403
    assert client.post(f"{base}/recusar", headers=membro.h).status_code == 403
    # pedido pendente: o oficial usa Recusar, não Cancelar
    assert client.post(f"{base}/cancelar", headers=pastor.h).status_code == 400
    # não dá para encerrar o que ainda não foi confirmado
    assert client.post(f"{base}/concluir", headers=pastor.h).status_code == 409

    assert client.post(f"{base}/confirmar", headers=pastor.h).status_code == 200
    assert client.post(f"{base}/confirmar", headers=pastor.h).status_code == 409
    assert client.post(f"{base}/recusar", headers=pastor.h).status_code == 409
    # confirmado, mas o horário ainda não chegou
    assert client.post(f"{base}/concluir", headers=pastor.h).status_code == 409
    assert client.post(f"{base}/faltou", headers=pastor.h).status_code == 409


def test_estados_finais_nao_mudam(client, pedido, pastor, membro):
    base = f"/agenda/atendimentos/{pedido['id']}"
    assert client.post(f"{base}/recusar", headers=pastor.h).status_code == 200
    for acao in ("confirmar", "recusar", "cancelar", "concluir", "faltou"):
        r = client.post(f"{base}/{acao}", headers=pastor.h)
        assert r.status_code == 409, acao
    assert client.post(f"{base}/cancelar", headers=membro.h).status_code == 409


def test_nao_confirma_horario_que_ja_passou(client, pedido, pastor):
    mover(pedido["id"], datetime.now(timezone.utc) - timedelta(hours=1))
    r = client.post(f"/agenda/atendimentos/{pedido['id']}/confirmar", headers=pastor.h)
    assert r.status_code == 409


def test_solicitante_cancela_pedido_pendente(client, pedido, membro, pastor, horarios):
    r = client.post(
        f"/agenda/atendimentos/{pedido['id']}/cancelar",
        headers=membro.h,
        json={"justificativa": "Não preciso mais"},
    )
    assert r.status_code == 200 and r.json()["status"] == "cancelado"
    dia = datetime.fromisoformat(pedido["inicio"]).astimezone(TZ).date()
    assert len(horarios(membro, pastor, dia)) == 4


def test_cancelamento_de_confirmado_respeita_o_prazo(client, pedido, pastor, membro):
    aid = pedido["id"]
    client.post(f"/agenda/atendimentos/{aid}/confirmar", headers=pastor.h)

    # dentro do prazo mínimo: o membro não cancela sozinho, o oficial sim
    mover(aid, datetime.now(timezone.utc) + timedelta(hours=5))
    r = client.post(f"/agenda/atendimentos/{aid}/cancelar", headers=membro.h)
    assert r.status_code == 409
    r = client.post(
        f"/agenda/atendimentos/{aid}/cancelar", headers=pastor.h, json={"justificativa": "Imprevisto"}
    )
    assert r.status_code == 200 and r.json()["status"] == "cancelado"


def test_membro_cancela_confirmado_com_antecedencia(client, pedido, pastor, membro):
    aid = pedido["id"]
    client.post(f"/agenda/atendimentos/{aid}/confirmar", headers=pastor.h)
    r = client.post(f"/agenda/atendimentos/{aid}/cancelar", headers=membro.h)
    assert r.status_code == 200 and r.json()["status"] == "cancelado"


# ---------- privacidade e isolamento ----------

def test_so_as_partes_enxergam_o_atendimento(client, conta, pedido, h, pastor, membro, criar_igreja, criar_usuario, auth):
    url = f"/agenda/atendimentos/{pedido['id']}"
    assert client.get(url, headers=membro.h).status_code == 200
    assert client.get(url, headers=pastor.h).status_code == 200

    outro_membro = conta()
    outro_oficial = conta(PRESBITERO)
    for intruso in (outro_membro, outro_oficial, SimpleNamespace(h=h)):  # h = administrador
        assert client.get(url, headers=intruso.h).status_code == 404
        for acao in ("confirmar", "recusar", "cancelar"):
            assert client.post(f"{url}/{acao}", headers=intruso.h).status_code == 404

    assert client.get("/agenda/atendimentos/meus", headers=outro_membro.h).json() == []
    assert client.get("/agenda/atendimentos/recebidos", headers=outro_oficial.h).json() == []

    # administrador não é oficial: não lê a agenda de ninguém
    assert client.get("/agenda/atendimentos/recebidos", headers=h).status_code == 403

    # outra igreja
    outra = criar_igreja("Igreja B")
    de_fora = auth(criar_usuario(outra, "fora@b.org", perfil=PASTOR))
    assert client.get(url, headers=de_fora).status_code == 404


def test_outra_igreja_nao_ve_oficiais(client, criar_igreja, criar_usuario, auth, pastor, abrir_agenda):
    abrir_agenda(pastor, dia_futuro())
    outra = criar_igreja("Igreja B")
    de_fora = auth(criar_usuario(outra, "fora@b.org"))
    assert client.get("/agenda/oficiais", headers=de_fora).json() == []
    r = client.get(f"/agenda/oficiais/{pastor.id}/horarios", headers=de_fora)
    assert r.status_code == 404


def test_auditoria_nao_guarda_o_assunto(client, pedido, pastor):
    client.post(
        f"/agenda/atendimentos/{pedido['id']}/recusar",
        headers=pastor.h,
        json={"justificativa": "Motivo reservado da recusa"},
    )
    with SessionLocal() as db:
        logs = list(db.scalars(select(LogAuditoria).where(LogAuditoria.entidade == "atendimento")))
    assert {l.acao for l in logs} == {"atendimento_solicitado", "atendimento_recusado"}
    todo_o_log = " ".join(str(l.detalhes) for l in logs)
    assert ASSUNTO not in todo_o_log
    assert "Motivo reservado" not in todo_o_log


# ---------- disponibilidade ----------

def test_so_oficial_tem_disponibilidade(client, h, membro):
    corpo = {
        "dia_semana": 1, "hora_inicio": "09:00", "hora_fim": "10:00",
        "duracao_min": 30, "modalidade": "online",
    }
    for quem in (membro.h, h):  # membro comum e administrador
        assert client.post("/agenda/disponibilidades", headers=quem, json=corpo).status_code == 403
        assert client.get("/agenda/disponibilidades", headers=quem).status_code == 403


def test_janelas_nao_podem_se_sobrepor(client, pastor, abrir_agenda):
    dia = dia_futuro()
    abrir_agenda(pastor, dia, "09:00", "11:00")
    r = client.post(
        "/agenda/disponibilidades",
        headers=pastor.h,
        json={
            "dia_semana": dia.weekday(), "hora_inicio": "10:30", "hora_fim": "12:00",
            "duracao_min": 30, "modalidade": "presencial",
        },
    )
    assert r.status_code == 409
    abrir_agenda(pastor, dia, "11:00", "12:00")  # encostar é permitido


def test_janela_invalida(client, pastor):
    base = {"dia_semana": 1, "modalidade": "online"}
    for corpo in (
        {**base, "hora_inicio": "10:00", "hora_fim": "09:00", "duracao_min": 30},
        {**base, "hora_inicio": "09:00", "hora_fim": "09:20", "duracao_min": 30},
        {**base, "hora_inicio": "09:00", "hora_fim": "10:00", "duracao_min": 5},
        {"dia_semana": 7, "hora_inicio": "09:00", "hora_fim": "10:00", "duracao_min": 30, "modalidade": "online"},
    ):
        assert client.post("/agenda/disponibilidades", headers=pastor.h, json=corpo).status_code == 422


def test_editar_desativar_e_remover_janela(client, pastor, membro, abrir_agenda, horarios):
    dia = dia_futuro()
    disp = abrir_agenda(pastor, dia)
    url = f"/agenda/disponibilidades/{disp['id']}"

    r = client.patch(url, headers=pastor.h, json={"duracao_min": 60})
    assert r.status_code == 200 and r.json()["duracao_min"] == 60
    assert len(horarios(membro, pastor, dia)) == 2

    assert client.patch(url, headers=pastor.h, json={"hora_fim": "09:30"}).status_code == 400

    client.patch(url, headers=pastor.h, json={"ativa": False})
    assert horarios(membro, pastor, dia) == []
    assert client.get("/agenda/oficiais", headers=membro.h).json() == []

    assert client.delete(url, headers=pastor.h).status_code == 204
    assert client.get("/agenda/disponibilidades", headers=pastor.h).json() == []


def test_janela_de_outro_oficial_nao_e_acessivel(client, conta, pastor, abrir_agenda):
    disp = abrir_agenda(pastor, dia_futuro())
    outro = conta(PRESBITERO)
    url = f"/agenda/disponibilidades/{disp['id']}"
    assert client.patch(url, headers=outro.h, json={"ativa": False}).status_code == 404
    assert client.delete(url, headers=outro.h).status_code == 404


# ---------- e-mails e lembretes ----------

def _para(mailer, usuario):
    return [m for m in mailer.enviados if m[0] == usuario.usuario.email]


def test_pedido_avisa_o_oficial_sem_vazar_o_assunto(
    pastor, membro, mailer, abrir_agenda, horarios, pedir
):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    mailer.enviados.clear()
    r = pedir(membro, pastor, horarios(membro, pastor, dia)[0]["inicio"])
    assert r.status_code == 201

    assert len(mailer.enviados) == 1
    destinatario, assunto, corpo = mailer.enviados[0]
    assert destinatario == pastor.usuario.email
    assert membro.membro["nome"] in assunto
    assert "09:00" in corpo and "Gabinete pastoral" in corpo
    assert "/agenda?aba=recebidos" in corpo
    assert ASSUNTO not in corpo and ASSUNTO not in assunto


def test_resposta_avisa_o_solicitante(client, pedido, pastor, membro, mailer):
    mailer.enviados.clear()
    client.post(f"/agenda/atendimentos/{pedido['id']}/confirmar", headers=pastor.h)
    assert [m[0] for m in mailer.enviados] == [membro.usuario.email]
    assert "confirmada" in mailer.enviados[0][1]


def test_recusa_nao_manda_o_motivo_por_email(client, pedido, pastor, membro, mailer):
    mailer.enviados.clear()
    client.post(
        f"/agenda/atendimentos/{pedido['id']}/recusar",
        headers=pastor.h,
        json={"justificativa": "Motivo reservado da recusa"},
    )
    assert [m[0] for m in mailer.enviados] == [membro.usuario.email]
    assert "Motivo reservado" not in mailer.enviados[0][2]
    assert ASSUNTO not in mailer.enviados[0][2]


def test_cancelamento_avisa_a_outra_parte(client, pedido, pastor, membro, mailer):
    client.post(f"/agenda/atendimentos/{pedido['id']}/confirmar", headers=pastor.h)

    mailer.enviados.clear()
    client.post(f"/agenda/atendimentos/{pedido['id']}/cancelar", headers=membro.h)
    assert [m[0] for m in mailer.enviados] == [pastor.usuario.email]

    # outro pedido, desta vez cancelado pelo oficial: quem recebe é o membro
    dia = datetime.fromisoformat(pedido["inicio"]).astimezone(TZ).date()
    r = client.get(
        f"/agenda/oficiais/{pastor.id}/horarios",
        headers=membro.h,
        params={"de": dia.isoformat(), "ate": dia.isoformat()},
    )
    novo = client.post(
        "/agenda/atendimentos",
        headers=membro.h,
        json={"oficial_id": pastor.id, "inicio": r.json()[0]["inicio"], "categoria": "outro"},
    ).json()
    client.post(f"/agenda/atendimentos/{novo['id']}/confirmar", headers=pastor.h)
    mailer.enviados.clear()
    client.post(f"/agenda/atendimentos/{novo['id']}/cancelar", headers=pastor.h)
    assert [m[0] for m in mailer.enviados] == [membro.usuario.email]


def test_concluir_nao_envia_email(client, pedido, pastor, mailer):
    client.post(f"/agenda/atendimentos/{pedido['id']}/confirmar", headers=pastor.h)
    mover(pedido["id"], datetime.now(timezone.utc) - timedelta(hours=1))
    mailer.enviados.clear()
    client.post(f"/agenda/atendimentos/{pedido['id']}/concluir", headers=pastor.h)
    assert mailer.enviados == []


def test_falha_no_email_nao_derruba_o_pedido(client, pastor, membro, mailer, abrir_agenda, horarios, pedir):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)

    def quebrado(*_):
        raise RuntimeError("SMTP fora do ar")

    mailer.enviar = quebrado
    r = pedir(membro, pastor, horarios(membro, pastor, dia)[0]["inicio"])
    assert r.status_code == 201
    assert client.get("/agenda/atendimentos/meus", headers=membro.h).json()[0]["status"] == "solicitado"


def rodar_lembretes(mailer, agora=None) -> int:
    from controllers import AtendimentoController
    from repositories import AtendimentoRepository, AuditoriaRepository, MembroRepository

    with SessionLocal() as db:
        controller = AtendimentoController(
            AtendimentoRepository(db), MembroRepository(db), AuditoriaRepository(db), db, mailer
        )
        return controller.enviar_lembretes(agora)


def test_lembrete_vai_para_os_dois_uma_unica_vez(client, pedido, pastor, membro, mailer):
    client.post(f"/agenda/atendimentos/{pedido['id']}/confirmar", headers=pastor.h)

    # faltam mais de 3 h: ainda não é hora
    mailer.enviados.clear()
    assert rodar_lembretes(mailer) == 0
    assert mailer.enviados == []

    mover(pedido["id"], datetime.now(timezone.utc) + timedelta(hours=2))
    assert rodar_lembretes(mailer) == 1
    assert sorted(m[0] for m in mailer.enviados) == sorted(
        [pastor.usuario.email, membro.usuario.email]
    )
    assert all(m[1] == "Lembrete de conversa" for m in mailer.enviados)
    assert all(ASSUNTO not in m[2] for m in mailer.enviados)

    mailer.enviados.clear()
    assert rodar_lembretes(mailer) == 0
    assert mailer.enviados == []


def test_lembrete_so_de_conversa_confirmada(client, pedido, pastor, mailer):
    # pendente: não lembra
    mover(pedido["id"], datetime.now(timezone.utc) + timedelta(hours=2))
    mailer.enviados.clear()
    assert rodar_lembretes(mailer) == 0

    # confirmada e depois cancelada: também não
    client.post(f"/agenda/atendimentos/{pedido['id']}/confirmar", headers=pastor.h)
    client.post(f"/agenda/atendimentos/{pedido['id']}/cancelar", headers=pastor.h)
    mailer.enviados.clear()
    assert rodar_lembretes(mailer) == 0
    assert mailer.enviados == []


def test_lembrete_tenta_de_novo_se_todos_os_emails_falharem(client, pedido, pastor, mailer):
    client.post(f"/agenda/atendimentos/{pedido['id']}/confirmar", headers=pastor.h)
    mover(pedido["id"], datetime.now(timezone.utc) + timedelta(hours=2))

    class Quebrado:
        def enviar(self, *_):
            raise RuntimeError("SMTP fora do ar")

    assert rodar_lembretes(Quebrado()) == 0
    mailer.enviados.clear()
    assert rodar_lembretes(mailer) == 1
    assert len(mailer.enviados) == 2


# ---------- Fase 3: bloqueios de agenda ----------

def bloquear(client, oficial, de, ate, motivo="Férias"):
    return client.post(
        "/agenda/bloqueios",
        headers=oficial.h,
        json={"de": de.isoformat(), "ate": ate.isoformat(), "motivo": motivo},
    )


def test_bloqueio_tira_os_horarios_do_periodo(client, pastor, membro, abrir_agenda, horarios, pedir):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    inicio = horarios(membro, pastor, dia)[0]["inicio"]

    r = bloquear(client, pastor, dia, dia)
    assert r.status_code == 201, r.text
    assert r.json()["atendimentos_afetados"] == 0
    assert horarios(membro, pastor, dia) == []
    assert pedir(membro, pastor, inicio).status_code == 409
    # a semana seguinte continua livre
    assert len(horarios(membro, pastor, dia + timedelta(days=7))) == 4

    assert client.delete(f"/agenda/bloqueios/{r.json()['id']}", headers=pastor.h).status_code == 204
    assert len(horarios(membro, pastor, dia)) == 4


def test_bloqueio_nao_mexe_nas_conversas_ja_marcadas_mas_avisa(client, pedido, pastor):
    dia = datetime.fromisoformat(pedido["inicio"]).astimezone(TZ).date()
    r = bloquear(client, pastor, dia - timedelta(days=1), dia + timedelta(days=1))
    assert r.json()["atendimentos_afetados"] == 1
    # a conversa continua como estava: o oficial decide o que fazer
    assert client.get(f"/agenda/atendimentos/{pedido['id']}", headers=pastor.h).json()["status"] == "solicitado"
    listados = client.get("/agenda/bloqueios", headers=pastor.h).json()
    assert [b["atendimentos_afetados"] for b in listados] == [1]


def test_bloqueio_so_do_oficial_e_valido(client, conta, h, membro, pastor):
    dia = dia_futuro()
    assert bloquear(client, membro, dia, dia).status_code == 403
    assert client.get("/agenda/bloqueios", headers=h).status_code == 403  # admin não é oficial
    assert bloquear(client, pastor, dia, dia - timedelta(days=1)).status_code == 422  # fim antes do início
    assert bloquear(client, pastor, dia, dia + timedelta(days=400)).status_code == 422  # longo demais
    passado = datetime.now(TZ).date() - timedelta(days=3)
    assert bloquear(client, pastor, passado, passado).status_code == 400

    criado = bloquear(client, pastor, dia, dia).json()
    outro = conta(PRESBITERO)
    assert client.delete(f"/agenda/bloqueios/{criado['id']}", headers=outro.h).status_code == 404
    assert client.get("/agenda/bloqueios", headers=outro.h).json() == []


def test_bloqueio_vencido_some_da_lista(client, pastor):
    hoje = datetime.now(TZ).date()
    bloquear(client, pastor, hoje, hoje)
    with SessionLocal() as db:
        db.execute(text("UPDATE bloqueio_agenda SET de = de - 10, ate = ate - 10"))
        db.commit()
    assert client.get("/agenda/bloqueios", headers=pastor.h).json() == []


# ---------- Fase 3: remarcação ----------

def proprios(client, oficial, dia):
    r = client.get(
        "/agenda/meus-horarios",
        headers=oficial.h,
        params={"de": dia.isoformat(), "ate": dia.isoformat()},
    )
    assert r.status_code == 200, r.text
    return r.json()


def remarcar(client, oficial, atendimento_id, inicio):
    return client.post(
        f"/agenda/atendimentos/{atendimento_id}/remarcar", headers=oficial.h, json={"inicio": inicio}
    )


def dia_do(pedido):
    return datetime.fromisoformat(pedido["inicio"]).astimezone(TZ).date()


def test_remarcacao_aceita(client, pedido, pastor, membro, horarios, mailer):
    dia = dia_do(pedido)
    original = pedido["inicio"]
    novo = proprios(client, pastor, dia)[0]["inicio"]
    assert novo != original

    mailer.enviados.clear()
    r = remarcar(client, pastor, pedido["id"], novo)
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["status"] == "remarcacao"
    assert datetime.fromisoformat(a["proposta_inicio"]) == datetime.fromisoformat(novo)
    assert a["proposta_modalidade"] == "presencial"
    assert a["inicio"] == pedido["inicio"]  # nada muda até o membro aceitar
    assert [m[0] for m in mailer.enviados] == [membro.usuario.email]
    assert "Novo horário proposto" in mailer.enviados[0][1]

    # o horário proposto fica guardado; o original volta a ficar livre
    livres = [datetime.fromisoformat(h["inicio"]) for h in horarios(membro, pastor, dia)]
    assert datetime.fromisoformat(novo) not in livres
    assert datetime.fromisoformat(original) in livres

    mailer.enviados.clear()
    r = client.post(f"/agenda/atendimentos/{pedido['id']}/aceitar-remarcacao", headers=membro.h)
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["status"] == "confirmado"
    assert datetime.fromisoformat(a["inicio"]) == datetime.fromisoformat(novo)
    assert a["proposta_inicio"] is None and a["proposta_local"] is None
    assert [m[0] for m in mailer.enviados] == [pastor.usuario.email]


def test_membro_recusa_a_remarcacao_cancelando(client, pedido, pastor, membro, horarios):
    dia = dia_do(pedido)
    remarcar(client, pastor, pedido["id"], proprios(client, pastor, dia)[0]["inicio"])

    r = client.post(f"/agenda/atendimentos/{pedido['id']}/cancelar", headers=membro.h)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelado"
    assert r.json()["proposta_inicio"] is None
    assert len(horarios(membro, pastor, dia)) == 4  # os dois horários ficaram livres


def test_oficial_retira_a_proposta(client, pedido, pastor):
    remarcar(client, pastor, pedido["id"], proprios(client, pastor, dia_do(pedido))[0]["inicio"])
    r = client.post(f"/agenda/atendimentos/{pedido['id']}/cancelar", headers=pastor.h)
    assert r.status_code == 200 and r.json()["status"] == "cancelado"


def test_remarcar_conversa_confirmada(client, pedido, pastor, membro):
    client.post(f"/agenda/atendimentos/{pedido['id']}/confirmar", headers=pastor.h)
    r = remarcar(client, pastor, pedido["id"], proprios(client, pastor, dia_do(pedido))[0]["inicio"])
    assert r.status_code == 200 and r.json()["status"] == "remarcacao"
    r = client.post(f"/agenda/atendimentos/{pedido['id']}/aceitar-remarcacao", headers=membro.h)
    assert r.json()["status"] == "confirmado"


def test_aceitar_remarcacao_reinicia_o_lembrete(client, pedido, pastor, membro):
    dia = dia_do(pedido)
    client.post(f"/agenda/atendimentos/{pedido['id']}/confirmar", headers=pastor.h)
    with SessionLocal() as db:
        db.execute(text("UPDATE atendimento SET lembrete_enviado_em = now()"))
        db.commit()
    remarcar(client, pastor, pedido["id"], proprios(client, pastor, dia)[0]["inicio"])
    client.post(f"/agenda/atendimentos/{pedido['id']}/aceitar-remarcacao", headers=membro.h)
    with SessionLocal() as db:
        assert db.execute(text("SELECT lembrete_enviado_em FROM atendimento")).scalar() is None


def test_remarcacao_regras(client, conta, pedido, pastor, membro):
    dia = dia_do(pedido)
    livre = proprios(client, pastor, dia)[0]["inicio"]
    base = f"/agenda/atendimentos/{pedido['id']}"

    # só o oficial propõe; só o membro aceita
    assert remarcar(client, membro, pedido["id"], livre).status_code == 403
    assert client.post(f"{base}/aceitar-remarcacao", headers=pastor.h).status_code == 403
    # sem proposta em aberto
    assert client.post(f"{base}/aceitar-remarcacao", headers=membro.h).status_code == 409
    # horário que não existe na agenda, e o próprio horário atual (ocupado pela conversa)
    fora = datetime.combine(dia, datetime.min.time().replace(hour=15), TZ).isoformat()
    assert remarcar(client, pastor, pedido["id"], fora).status_code == 409
    assert remarcar(client, pastor, pedido["id"], pedido["inicio"]).status_code == 409
    # terceiros não enxergam
    intruso = conta(PRESBITERO)
    assert remarcar(client, intruso, pedido["id"], livre).status_code == 404
    assert client.post(f"{base}/aceitar-remarcacao", headers=intruso.h).status_code == 404

    # conversa já encerrada não é remarcada
    client.post(f"{base}/recusar", headers=pastor.h)
    assert remarcar(client, pastor, pedido["id"], livre).status_code == 409


def test_nao_aceita_horario_proposto_que_passou_ou_foi_bloqueado(client, pedido, pastor, membro):
    dia = dia_do(pedido)
    base = f"/agenda/atendimentos/{pedido['id']}"

    remarcar(client, pastor, pedido["id"], proprios(client, pastor, dia)[0]["inicio"])
    bloquear(client, pastor, dia, dia)  # o oficial passou a não atender nesse dia
    assert client.post(f"{base}/aceitar-remarcacao", headers=membro.h).status_code == 409

    with SessionLocal() as db:
        passado = datetime.now(timezone.utc) - timedelta(hours=3)
        db.execute(
            text("UPDATE atendimento SET proposta_inicio = :i, proposta_fim = :f"),
            {"i": passado, "f": passado + timedelta(minutes=30)},
        )
        db.execute(text("DELETE FROM bloqueio_agenda"))
        db.commit()
    assert client.post(f"{base}/aceitar-remarcacao", headers=membro.h).status_code == 409


def test_com_remarcacao_em_aberto_as_outras_acoes_nao_se_aplicam(client, pedido, pastor):
    remarcar(client, pastor, pedido["id"], proprios(client, pastor, dia_do(pedido))[0]["inicio"])
    base = f"/agenda/atendimentos/{pedido['id']}"
    for acao in ("confirmar", "recusar", "concluir", "faltou"):
        assert client.post(f"{base}/{acao}", headers=pastor.h).status_code == 409, acao


def test_meus_horarios_so_para_oficial(client, membro, pastor, abrir_agenda):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    assert len(proprios(client, pastor, dia)) == 4
    assert client.get("/agenda/meus-horarios", headers=membro.h).status_code == 403


# ---------- Fase 3: relatório ----------

def test_relatorio_conta_por_mes_e_situacao(client, conta, pastor, membro, abrir_agenda, horarios, pedir):
    dia = dia_futuro()
    abrir_agenda(pastor, dia)
    livres = horarios(membro, pastor, dia)
    ids = [pedir(membro, pastor, livres[i]["inicio"]).json()["id"] for i in range(2)]
    ids.append(pedir(conta(), pastor, livres[2]["inicio"]).json()["id"])

    # um realizado (no passado), um recusado, um ainda pendente
    client.post(f"/agenda/atendimentos/{ids[0]}/confirmar", headers=pastor.h)
    mover(ids[0], datetime.now(timezone.utc) - timedelta(hours=2))
    client.post(f"/agenda/atendimentos/{ids[0]}/concluir", headers=pastor.h)
    client.post(f"/agenda/atendimentos/{ids[1]}/recusar", headers=pastor.h)

    r = client.get("/agenda/relatorio", headers=pastor.h)
    assert r.status_code == 200, r.text
    meses = r.json()
    assert len(meses) == 12  # padrão: últimos 12 meses, inclusive os vazios
    hoje = datetime.now(TZ)
    assert meses[-1]["mes"] == f"{hoje.year:04d}-{hoje.month:02d}"

    # o pendente cai no mês da data marcada (pode ser o seguinte): consulta até lá
    r = client.get(
        "/agenda/relatorio",
        headers=pastor.h,
        params={"de": hoje.date().isoformat(), "ate": (dia + timedelta(days=1)).isoformat()},
    )
    chaves = ("total", "realizados", "recusados", "em_andamento", "faltas", "cancelados")
    total = {k: sum(m[k] for m in r.json()) for k in chaves}
    assert total == {"total": 3, "realizados": 1, "recusados": 1, "em_andamento": 1, "faltas": 0, "cancelados": 0}


def test_relatorio_e_privado_e_limitado(client, conta, h, membro, pastor, pedido):
    assert client.get("/agenda/relatorio", headers=membro.h).status_code == 403
    assert client.get("/agenda/relatorio", headers=h).status_code == 403  # admin não é oficial
    # outro oficial só vê o próprio: nada
    outro = conta(PRESBITERO)
    assert sum(m["total"] for m in client.get("/agenda/relatorio", headers=outro.h).json()) == 0
    # período
    hoje = datetime.now(TZ).date()
    ontem = (hoje - timedelta(days=1)).isoformat()
    r = client.get("/agenda/relatorio", headers=pastor.h, params={"de": hoje.isoformat(), "ate": ontem})
    assert r.status_code == 400
    longe = (hoje - timedelta(days=900)).isoformat()
    r = client.get("/agenda/relatorio", headers=pastor.h, params={"de": longe, "ate": hoje.isoformat()})
    assert r.status_code == 400
    # nada que identifique alguém
    corpo = client.get("/agenda/relatorio", headers=pastor.h).text
    assert ASSUNTO not in corpo and membro.membro["nome"] not in corpo
