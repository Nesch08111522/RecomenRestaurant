# generar_secret.py
import secrets

# Genera una clave secreta de 32 bytes en formato hexadecimal
secret_key = secrets.token_hex(32)
print(f"SECRET_KEY={secret_key}")