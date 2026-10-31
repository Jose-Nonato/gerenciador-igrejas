"""Cria uma igreja e o seu primeiro administrador.

Uso (a partir de back/):
    python -m scripts.criar_igreja --nome "Igreja Presbiteriana X" --email admin@exemplo.com

A senha é pedida no terminal (não vai em argumento nem fica no histórico do shell).
"""

import argparse
import getpass
import sys

from core import security
from core.database import SessionLocal
from models.enums import PerfilUsuario, StatusUsuario
from repositories import IgrejaRepository, UsuarioRepository

MIN_SENHA = 8


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--nome", required=True, help="Nome da igreja")
    parser.add_argument("--email", required=True, help="E-mail do administrador")
    parser.add_argument("--cnpj")
    parser.add_argument("--presbiterio")
    parser.add_argument("--endereco")
    args = parser.parse_args()

    senha = getpass.getpass("Senha do administrador: ")
    if len(senha) < MIN_SENHA:
        print(f"A senha precisa ter ao menos {MIN_SENHA} caracteres.", file=sys.stderr)
        return 1
    if senha != getpass.getpass("Repita a senha: "):
        print("As senhas não conferem.", file=sys.stderr)
        return 1

    email = args.email.lower()
    with SessionLocal() as db:
        usuarios = UsuarioRepository(db)
        if usuarios.get_by_email(email):
            print(f"Já existe um usuário com o e-mail {email}.", file=sys.stderr)
            return 1
        igreja = IgrejaRepository(db).create(
            args.nome, cnpj=args.cnpj, presbiterio=args.presbiterio, endereco=args.endereco
        )
        usuarios.create(
            igreja.id,
            email,
            security.hash_password(senha),
            perfil=PerfilUsuario.ADMIN,
            status=StatusUsuario.ATIVO,
        )
    print(f"Igreja '{args.nome}' criada com o administrador {email}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
