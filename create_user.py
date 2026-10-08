# create_user.py
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

def create_user():
    """Crea un usuario con contraseña específica"""
    
    username = "admin"
    password = "admin123"
    
    hashed = generate_password_hash(password)
    
    print(f"🔑 Usuario: {username}")
    print(f"🔑 Contraseña: {password}")
    print(f"🔑 Hash generado: {hashed}")
    print(f"✅ Verificación: {check_password_hash(hashed, password)}")
    
    # Leer usuarios existentes
    users_file = 'data/users.json'
    if os.path.exists(users_file):
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
    else:
        users = []
    
    # Actualizar o agregar usuario
    found = False
    for user in users:
        if user.get('username') == username:
            user['password'] = hashed
            found = True
            print(f"✅ Usuario {username} actualizado")
            break
    
    if not found:
        new_user = {
            "id": len(users) + 1,
            "username": username,
            "password": hashed,
            "profile": {
                "name": "Administrador",
                "email": "admin@smartresto.com",
                "preferences": [],
                "restrictions": []
            },
            "role": "admin"
        }
        users.append(new_user)
        print(f"✅ Usuario {username} creado")
    
    # Guardar
    with open(users_file, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False)
    
    print("✅ Archivo de usuarios actualizado")

if __name__ == "__main__":
    create_user()