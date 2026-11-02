import uuid

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, text

from tests.conftest import _dev_url, alembic_config, recreate_database

DB = f"{_dev_url.database}_mig"


def _engine():
    return create_engine(_dev_url.set(database=DB))


def test_migracao_preserva_usuarios_existentes_e_reverte():
    recreate_database(DB)
    cfg = alembic_config()
    user_id = uuid.uuid4()

    with _engine().begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "0001")
        conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, is_active) "
                "VALUES (:id, 'dev@x.org', 'hash', true)"
            ),
            {"id": user_id},
        )
        conn.execute(
            text(
                "INSERT INTO refresh_tokens (jti, user_id, expires_at, revoked) "
                "VALUES ('j1', :id, now(), false)"
            ),
            {"id": user_id},
        )

        command.upgrade(cfg, "head")
        row = conn.execute(
            text("SELECT email, senha_hash, perfil, status, igreja_id FROM usuario")
        ).one()
        assert row[:4] == ("dev@x.org", "hash", "admin", "ativo")
        assert conn.execute(text("SELECT count(*) FROM igreja")).scalar() == 1
        assert conn.execute(text("SELECT usuario_id FROM refresh_tokens")).scalar() == user_id

        command.downgrade(cfg, "0001")
        assert conn.execute(text("SELECT email FROM users")).scalar() == "dev@x.org"
        assert conn.execute(text("SELECT user_id FROM refresh_tokens")).scalar() == user_id


def test_migracoes_batem_com_os_modelos():
    """Se falhar, falta uma migração para alguma mudança feita nos models."""
    recreate_database(DB)
    cfg = alembic_config()
    with _engine().begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")

        import models  # noqa: F401
        from core.database import Base

        diff = compare_metadata(MigrationContext.configure(conn, opts={"compare_type": True}), Base.metadata)
        assert diff == []


def test_downgrade_da_exclusao_logica_libera_numero_repetido_de_excluido():
    recreate_database(DB)
    cfg = alembic_config()
    with _engine().begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
        igreja = uuid.uuid4()
        conn.execute(text("INSERT INTO igreja (id, nome) VALUES (:i, 'A')"), {"i": igreja})
        ativo, excluido = uuid.uuid4(), uuid.uuid4()
        for id_, extra in ((ativo, "NULL"), (excluido, "now()")):
            conn.execute(
                text(
                    "INSERT INTO membro (id, igreja_id, numero_rol, rol, nome, situacao, oficio, excluido_em) "
                    f"VALUES (:id, :ig, 5, 'C', 'M', 'ativo', 'nenhum', {extra})"
                ),
                {"id": id_, "ig": igreja},
            )

        command.downgrade(cfg, "0003")

        numeros = dict(conn.execute(text("SELECT id, numero_rol FROM membro")).all())
        assert numeros[ativo] == 5 and numeros[excluido] is None
