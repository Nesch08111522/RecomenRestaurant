"""Manually check credentials against the configured Supabase database."""

from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=False)

from models.user import UserModel


def check_authentication():
    username = input("Usuario: ").strip()
    password = getpass("Contraseña: ")
    user = UserModel.authenticate(username, password)
    print("Credenciales válidas." if user else "Credenciales inválidas.")


if __name__ == "__main__":
    check_authentication()
