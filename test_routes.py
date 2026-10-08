# test_routes.py
from app import create_app

app = create_app()

# Crear un contexto de aplicación activo
with app.app_context():
    # Necesitamos un contexto de solicitud para url_for
    with app.test_request_context():
        from flask import url_for
        
        print("=== VERIFICANDO RUTAS DE AUTH ===\n")
        
        try:
            print("✅ auth.login:", url_for('auth.login'))
        except Exception as e:
            print("❌ auth.login:", e)
        
        try:
            print("✅ auth.register:", url_for('auth.register'))
        except Exception as e:
            print("❌ auth.register:", e)
        
        try:
            print("✅ auth.profile:", url_for('auth.profile'))
        except Exception as e:
            print("❌ auth.profile:", e)
        
        try:
            print("✅ auth.favorites:", url_for('auth.favorites'))
        except Exception as e:
            print("❌ auth.favorites:", e)
        
        try:
            print("✅ auth.logout:", url_for('auth.logout'))
        except Exception as e:
            print("❌ auth.logout:", e)
        
        try:
            print("✅ auth.update_profile:", url_for('auth.update_profile'))
        except Exception as e:
            print("❌ auth.update_profile:", e)
        
        try:
            print("✅ auth.toggle_favorite:", url_for('auth.toggle_favorite'))
        except Exception as e:
            print("❌ auth.toggle_favorite:", e)
        
        try:
            print("✅ auth.get_favorites_api:", url_for('auth.get_favorites_api'))
        except Exception as e:
            print("❌ auth.get_favorites_api:", e)
        
        print("\n=== VERIFICANDO RUTAS DE MAIN ===\n")
        
        try:
            print("✅ main.index:", url_for('main.index'))
        except Exception as e:
            print("❌ main.index:", e)
        
        try:
            print("✅ main.detail:", url_for('main.detail', restaurant_id=1))
        except Exception as e:
            print("❌ main.detail:", e)
        
        print("\n=== VERIFICANDO RUTAS DE ADMIN ===\n")
        
        try:
            print("✅ admin.dashboard:", url_for('admin.dashboard'))
        except Exception as e:
            print("❌ admin.dashboard:", e)
        
        print("\n=== VERIFICANDO RUTAS DE SEARCH ===\n")
        
        try:
            print("✅ main.search:", url_for('main.search'))
        except Exception as e:
            print("❌ main.search:", e)
            