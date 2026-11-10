"""Armazenamento local de imagens (desenvolvimento).

Só guarda o nome do arquivo no banco; trocar por S3 ou similar depois exige mexer só aqui.
O tipo é identificado pelo conteúdo (assinatura do arquivo), nunca pelo nome ou Content-Type
enviados pelo cliente, e o nome em disco é sempre gerado pelo servidor.
"""
import uuid
from pathlib import Path

from core.config import settings

BACK_DIR = Path(__file__).resolve().parent.parent

# extensão -> Content-Type
TIPOS = {"jpg": "image/jpeg", "png": "image/png", "gif": "image/gif", "webp": "image/webp"}


def pasta() -> Path:
    base = Path(settings.UPLOAD_DIR)
    return (base if base.is_absolute() else BACK_DIR / base) / "comunicados"


def detectar_extensao(dados: bytes) -> str | None:
    if dados.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if dados.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return "webp"
    return None


def salvar(dados: bytes, extensao: str) -> str:
    destino = pasta()
    destino.mkdir(parents=True, exist_ok=True)
    nome = f"{uuid.uuid4().hex}.{extensao}"
    (destino / nome).write_bytes(dados)
    return nome


def caminho(nome: str) -> Path | None:
    """Caminho do arquivo, ou None se não existir (ou o nome for suspeito)."""
    if Path(nome).name != nome:
        return None
    arquivo = pasta() / nome
    return arquivo if arquivo.is_file() else None


def media_type(nome: str) -> str:
    return TIPOS.get(nome.rsplit(".", 1)[-1], "application/octet-stream")


def remover(nome: str | None) -> None:
    if not nome:
        return
    arquivo = caminho(nome)
    if arquivo is not None:
        arquivo.unlink(missing_ok=True)
