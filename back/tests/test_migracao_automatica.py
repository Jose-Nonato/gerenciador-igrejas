from sqlalchemy import text

import main
from core.database import engine
from core.migracoes import aplicar_migracoes


def _versao() -> str:
    with engine.connect() as conn:
        return conn.execute(text("SELECT version_num FROM alembic_version")).scalar()


def test_aplicar_migracoes_e_idempotente_e_nao_deixa_lock(client):
    antes = _versao()
    aplicar_migracoes()
    aplicar_migracoes()
    assert _versao() == antes

    # o lock consultivo foi liberado: ninguém o está segurando
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM pg_locks WHERE locktype = 'advisory'")).scalar() == 0


def test_api_migra_ao_iniciar_quando_habilitado(monkeypatch):
    from fastapi.testclient import TestClient

    chamadas = []
    monkeypatch.setattr(main, "aplicar_migracoes", lambda: chamadas.append(1))
    monkeypatch.setattr(main.settings, "AUTO_MIGRATE", True)
    with TestClient(main.app):
        pass
    assert chamadas == [1]


def test_api_nao_migra_quando_desabilitado(monkeypatch):
    from fastapi.testclient import TestClient

    chamadas = []
    monkeypatch.setattr(main, "aplicar_migracoes", lambda: chamadas.append(1))
    monkeypatch.setattr(main.settings, "AUTO_MIGRATE", False)
    with TestClient(main.app):
        pass
    assert chamadas == []


def test_falha_na_migracao_impede_a_api_de_subir(monkeypatch):
    import pytest
    from fastapi.testclient import TestClient

    def quebra():
        raise RuntimeError("migração falhou")

    monkeypatch.setattr(main, "aplicar_migracoes", quebra)
    monkeypatch.setattr(main.settings, "AUTO_MIGRATE", True)
    with pytest.raises(RuntimeError, match="migração falhou"):
        with TestClient(main.app):
            pass
