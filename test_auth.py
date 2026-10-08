# test_auth.py
import json
import os
from werkzeug.security import generate_password_hash, check_password_hash

def test_authentication():
    """Prueba la autenticación de usuarios"""
    
    users_file = 'data/users.json'
    
    if not os.path.exists(users_file):
        print("❌ No se encontró el archivo de usuarios")
        return
    
    with open(users_file, 'r', encoding='utf-8') as f:
        users = json.load(f)
    
    print("=" * 60)
    print("🔍 PROBANDO AUTENTICACIÓN DE USUARIOS")
    print("=" * 60)
    
    for user in users:
        username = user.get('username')
        stored_hash = user.get('password', '')
        
        print(f"\n👤 Usuario: {username}")
        print(f"   Hash: {stored_hash[:30]}...")
        
        # Probar con la contraseña correcta (si es admin o usuario)
        test_passwords = {
            'admin': 'admin123',
            'usuario': 'usuario123'
        }
        
        test_password = test_passwords.get(username)
        if test_password:
            is_valid = check_password_hash(stored_hash, test_password)
            print(f"   ✅ Contraseña '{test_password}': {'CORRECTA' if is_valid else 'INCORRECTA'}")
        
        # Probar con una contraseña incorrecta
        is_valid = check_password_hash(stored_hash, 'contraseña_incorrecta')
        print(f"   ❌ Contraseña incorrecta: {'FALLA BIEN' if not is_valid else 'ERROR (debería fallar)'}")

if __name__ == "__main__":
    test_authentication()