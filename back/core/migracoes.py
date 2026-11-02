"""Aplica as migrações do Alembic (`alembic upgrade head`) ao iniciar a aplicação."""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import text

from core.database import engine

logger = logging.getLogger(__name__)

BACK_DIR = Path(__file__).resolve().parent.parent
# Chave do lock consultivo do Postgres: vários processos subindo juntos (workers,
# réplicas) migram um de cada vez, e os demais esperam e encontram o banco já atualizado
_CHAVE_LOCK = 7_238_114_001


def aplicar_migracoes() -> None:
    config = Config(str(BACK_DIR / "alembic.ini"))
    # Caminho absoluto: não depende do diretório de onde o uvicorn foi iniciado
    config.set_main_option("script_location", str(BACK_DIR / "migrations"))

    # AUTOCOMMIT: a conexão do lock não fica com uma transação aberta durante a migração
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as lock:
        lock.execute(text("SELECT pg_advisory_lock(:chave)"), {"chave": _CHAVE_LOCK})
        try:
            logger.info("Aplicando migrações do banco (alembic upgrade head)")
            command.upgrade(config, "head")
        finally:
            lock.execute(text("SELECT pg_advisory_unlock(:chave)"), {"chave": _CHAVE_LOCK})
