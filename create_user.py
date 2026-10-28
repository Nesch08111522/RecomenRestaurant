"""Interactively create an administrator in the configured Supabase database."""

from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv(Path(__file__).with_name(".env"), override=False)

from models.user import UserModel


def create_user():
    username = input("Usuario administrador: ").strip()
    name = input("Nombre: ").strip()
    email = input("Correo: ").strip()
    password = getpass("Contraseña (mínimo 12 caracteres): ")
    confirmation = getpass("Repite la contraseña: ")

    if not username or not name or not email:
        raise ValueError("Usuario, nombre y correo son obligatorios.")
    if len(password) < 12:
        raise ValueError("La contraseña debe tener al menos 12 caracteres.")
    if password != confirmation:
        raise ValueError("Las contraseñas no coinciden.")
    if UserModel.get_by_username(username):
        raise ValueError("Ese usuario ya existe en Supabase.")

    user = UserModel.create(
        {
            "username": username,
            "password": generate_password_hash(password),
            "role": "admin",
            "profile": {
                "name": name,
                "email": email,
                "preferences": [],
                "restrictions": [],
            },
        }
    )
    print(f"Administrador creado en Supabase (id={user['id']}).")


if __name__ == "__main__":
    create_user()
