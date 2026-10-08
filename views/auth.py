from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.user import UserModel
from models.restaurant import RestaurantModel
from models.favorite import FavoriteModel
from config import Config
from utils.security import is_safe_redirect_url, normalize_text, session_identity
from werkzeug.security import generate_password_hash, check_password_hash
import re
import logging
from typing import Optional, Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        username = normalize_text(username, max_length=80)
        logger.info("Intento de login para usuario=%s", username or "<vacío>")

        user = UserModel.authenticate(username, password or "")

        if user:
            logger.info("Login exitoso para usuario=%s", username)
            session.clear()
            session.permanent = True
            session['user'] = session_identity(user)
            session['user_id'] = user.get('id')
            session['username'] = user.get('username')
            session['role'] = user.get('role', 'user')
            target = request.args.get('next')
            destination = target if is_safe_redirect_url(target) else url_for('main.index')
            flash('¡Bienvenido!', 'success')
            return redirect(destination)
        else:
            logger.warning("Login fallido para usuario=%s", username or "<vacío>")
            flash('Credenciales inválidas. Verifica tu usuario y contraseña.', 'error')
    
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        name = request.form.get('name')
        role = request.form.get('role', 'user')
        
        username = normalize_text(username, max_length=80)
        email = normalize_text(email, max_length=254).lower()
        name = normalize_text(name, max_length=120)
        # El rol público de registro siempre se fuerza a usuario o empresario.
        role = role if role in ['user', 'business_owner'] else 'user'
        logger.info("Registrando nuevo usuario=%s rol=%s", username or "<vacío>", role)

        if password is None or len(password) < 8 or not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            flash('La contraseña debe tener al menos 6 caracteres', 'error')
            return render_template('register.html')
        
        if not username or not re.fullmatch(r'^[a-zA-Z0-9_]{3,80}$', username):
            flash('El usuario solo puede contener letras, números y guión bajo', 'error')
            return render_template('register.html')
        
        existing = UserModel.get_by_username(username)
        if existing:
            flash('El nombre de usuario ya está en uso', 'error')
            return render_template('register.html')
        
        if email and not re.fullmatch(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            flash('El correo electrónico no tiene un formato válido', 'error')
            return render_template('register.html')

        hashed_password = generate_password_hash(password)
        
        user_data = {
            'username': username,
            'password': hashed_password,
            'role': role,
            'profile': {
                'name': name,
                'email': email,
                'preferences': [],
                'restrictions': []
            }
        }
        
        user = UserModel.create(user_data)
        logger.info(f"✅ Usuario {username} creado con ID: {user.get('id')} (Rol: {role})")
        flash('¡Registro exitoso! Ahora puedes iniciar sesión', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    username = session.get('username', 'Unknown')
    logger.info(f"👋 Usuario {username} cerró sesión")
    session.clear()
    flash('Sesión cerrada correctamente', 'info')
    return redirect(url_for('main.index'))

# ============================================
# PERFIL Y FAVORITOS
# ============================================

@auth_bp.route('/profile')
def profile():
    user = session.get('user')
    if not user:
        flash('Debes iniciar sesión para ver tu perfil', 'warning')
        return redirect(url_for('auth.login'))
    
    logger.info(f"👤 Cargando perfil de: {user.get('username')}")
    
    if user.get('id'):
        updated_user = UserModel.get_by_id(user.get('id'))
        if updated_user:
            user = session_identity(updated_user)
            session['user'] = user
            session['user_id'] = user['id']
            session['role'] = user['role']
    
    # ✅ Usar template según rol
    if user.get('role') == 'business_owner':
        return render_template('auth/profile_owner.html', user=user)
    else:
        return render_template('auth/profile.html', user=user)
    
    
    
@auth_bp.route('/favorites')
def favorites():
    """Lista de restaurantes favoritos del usuario"""
    user = session.get('user')
    if not user:
        flash('Debes iniciar sesión para ver tus favoritos', 'warning')
        return redirect(url_for('auth.login'))
    
    user_id = user.get('id')
    
    if not user_id:
        flash('Error: Usuario no válido', 'error')
        return redirect(url_for('auth.login'))
    
    logger.info(f"❤️ Cargando favoritos de usuario: {user.get('username')} (ID: {user_id})")
    
    user_favorites = FavoriteModel.get_by_user(user_id)
    favorite_ids = [fav.get('restaurant_id') for fav in user_favorites if fav.get('restaurant_id')]
    
    favorite_restaurants = []
    for fav_id in favorite_ids:
        restaurant = RestaurantModel.get_by_id(fav_id)
        if restaurant:
            favorite_restaurants.append(restaurant)
    
    logger.info(f"✅ {len(favorite_restaurants)} favoritos encontrados")
    
    return render_template('favorites.html', 
                         restaurants=favorite_restaurants,
                         total=len(favorite_restaurants))

@auth_bp.route('/profile/update', methods=['POST'])
def update_profile():
    """Actualizar perfil del usuario"""
    user = session.get('user')
    if not user:
        flash('Debes iniciar sesión para actualizar tu perfil', 'warning')
        return redirect(url_for('auth.login'))
    
    user_id = user.get('id')
    
    if not user_id:
        flash('Error: Usuario no válido', 'error')
        return redirect(url_for('auth.login'))
    
    logger.info(f"✏️ Actualizando perfil de: {user.get('username')} (ID: {user_id})")
    
    db_user = UserModel.get_by_id(user_id)
    
    if not db_user:
        session.clear()
        flash('Usuario no encontrado', 'error')
        return redirect(url_for('auth.login'))
    
    profile = dict(db_user.get('profile') or {})
    profile['name'] = normalize_text(request.form.get('name', profile.get('name')), max_length=120)
    profile['email'] = normalize_text(request.form.get('email', profile.get('email')), max_length=254).lower()
    profile['preferences'] = [normalize_text(value, max_length=80) for value in request.form.getlist('preferences')][:50]
    profile['restrictions'] = [normalize_text(value, max_length=80) for value in request.form.getlist('restrictions')][:50]
    if profile['email'] and not re.fullmatch(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', profile['email']):
        flash('El correo electrónico no tiene un formato válido', 'error')
        return redirect(url_for('auth.profile'))

    UserModel.update(user_id, {'profile': profile})
    session['user'] = session_identity({**db_user, 'profile': profile})
    
    logger.info(f"✅ Perfil actualizado para: {db_user.get('username')}")
    flash('Perfil actualizado correctamente', 'success')
    return redirect(url_for('auth.profile'))

# ============================================
# API DE FAVORITOS
# ============================================

@auth_bp.route('/api/favorites/toggle', methods=['POST'])
def toggle_favorite():
    """API para agregar/quitar favoritos"""
    try:
        user = session.get('user')
        if not user:
            return jsonify({'error': 'No autenticado'}), 401
        
        data = request.get_json(silent=True) or {}
        if not data:
            return jsonify({'error': 'Datos inválidos'}), 400
        
        try:
            restaurant_id = int(data.get('restaurant_id'))
        except (TypeError, ValueError):
            return jsonify({'error': 'ID de restaurante inválido'}), 400

        if restaurant_id <= 0:
            return jsonify({'error': 'ID de restaurante requerido'}), 400
        
        restaurant = RestaurantModel.get_by_id(restaurant_id)
        if not restaurant:
            return jsonify({'error': 'Restaurante no encontrado'}), 404
        
        user_id = user.get('id')
        username = user.get('username', 'Unknown')
        
        if not user_id:
            return jsonify({'error': 'Usuario no válido'}), 401
        
        logger.info(f"🔄 Toggle favorito - Usuario: {username}, Restaurante ID: {restaurant_id}")
        
        result = FavoriteModel.toggle(user_id, restaurant_id)
        
        favorites = FavoriteModel.get_by_user(user_id)
        favorite_ids = [fav.get('restaurant_id') for fav in favorites if fav.get('restaurant_id')]
        
        logger.info(f"✅ Favorito {'agregado' if result else 'eliminado'} para usuario {username}")
        
        return jsonify({
            'success': True,
            'favorited': result,
            'restaurant_id': restaurant_id,
            'favorites': favorite_ids
        })
        
    except Exception as e:
        logger.exception("Error en toggle_favorite")
        return jsonify({'error': 'No se pudo actualizar el favorito', 'success': False}), 500

@auth_bp.route('/api/favorites', methods=['GET'])
def get_favorites_api():
    """API para obtener favoritos del usuario"""
    try:
        user = session.get('user')
        if not user:
            return jsonify({
                'error': 'No autenticado',
                'favorites': [],
                'success': False
            }), 401
        
        user_id = user.get('id')
        username = user.get('username', 'Unknown')
        
        if not user_id:
            return jsonify({
                'error': 'Usuario no válido',
                'favorites': [],
                'success': False
            }), 401
        
        logger.info(f"📱 API: Obteniendo favoritos de {username}")
        
        favorites = FavoriteModel.get_by_user(user_id)
        
        return jsonify({
            'success': True,
            'favorites': favorites,
            'total': len(favorites)
        })
        
    except Exception as e:
        logger.exception("Error en get_favorites_api")
        return jsonify({
            'error': 'No se pudieron obtener los favoritos',
            'favorites': [],
            'success': False
        }), 500