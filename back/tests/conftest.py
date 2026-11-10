import os
import tempfile
import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACK_DIR = Path(__file__).resolve().parent.parent

# Os testes usam um banco próprio (<banco>_test), nunca o de desenvolvimento.
# Precisa ser definido antes de importar qualquer módulo da aplicação.
_env = dotenv_values(BACK_DIR / ".env")
_dev_url = make_url(_env["DATABASE_URL"])
TEST_DB_NAME = f"{_dev_url.database}_test"
TEST_URL = _dev_url.set(database=TEST_DB_NAME)
os.environ["DATABASE_URL"] = TEST_URL.render_as_string(hide_password=False)
os.environ.setdefault("JWT_SECRET", _env["JWT_SECRET"])
# Os testes montam o banco sozinhos (fixture _banco); a migração na inicialização só atrapalharia
os.environ["AUTO_MIGRATE"] = "false"
# Imagens dos testes vão para uma pasta temporária, nunca para a de desenvolvimento
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="gi-uploads-")


def recreate_database(name: str) -> None:
    admin = create_engine(_dev_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()


def alembic_config() -> Config:
    cfg = Config(str(BACK_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACK_DIR / "migrations"))
    return cfg


@pytest.fixture(scope="session", autouse=True)
def _banco():
    recreate_database(TEST_DB_NAME)
    command.upgrade(alembic_config(), "head")


@pytest.fixture(autouse=True)
def _limpar_tabelas():
    yield
    from core.database import engine

    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE log_auditoria, token_redefinicao, refresh_tokens, usuario, igreja CASCADE"
            )
        )


class FakeMailer:
    def __init__(self) -> None:
        self.enviados: list[tuple[str, str, str]] = []

    def enviar(self, destinatario: str, assunto: str, corpo: str) -> None:
        self.enviados.append((destinatario, assunto, corpo))

    def ultimo_token(self) -> str:
        return re.search(r"token=([\w-]+)", self.enviados[-1][2]).group(1)


@pytest.fixture
def mailer():
    return FakeMailer()


@pytest.fixture
def client(mailer):
    from fastapi.testclient import TestClient

    from core.mailer import get_mailer
    from main import app

    app.dependency_overrides[get_mailer] = lambda: mailer
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


SENHA = "Senha@12345"


@pytest.fixture
def criar_igreja():
    from core.database import SessionLocal
    from repositories import IgrejaRepository

    def _criar(nome="Igreja A"):
        with SessionLocal() as db:
            return IgrejaRepository(db).create(nome).id

    return _criar


@pytest.fixture
def criar_usuario():
    from core.database import SessionLocal
    from core.security import hash_password
    from models.enums import PerfilUsuario, StatusUsuario
    from repositories import UsuarioRepository

    def _criar(
        igreja_id,
        email,
        perfil=PerfilUsuario.USUARIO,
        status=StatusUsuario.ATIVO,
        troca_obrigatoria=False,
        senha=SENHA,
    ):
        with SessionLocal() as db:
            u = UsuarioRepository(db).create(
                igreja_id, email, hash_password(senha), perfil, status, troca_obrigatoria
            )
            return SimpleNamespace(id=u.id, email=email, senha=senha, igreja_id=igreja_id)

    return _criar


@pytest.fixture
def login(client):
    def _login(usuario, senha=None):
        r = client.post(
            "/auth/login", data={"username": usuario.email, "password": senha or usuario.senha}
        )
        return r

    return _login


@pytest.fixture
def auth(login):
    def _auth(usuario):
        r = login(usuario)
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _auth
