from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from models.user import UserModel
from models.restaurant import RestaurantModel
from models.favorite import FavoriteModel
from utils.security import is_safe_redirect_url, normalize_text, session_identity
from core.profile import normalize_profile_patch
from werkzeug.security import generate_password_hash
import re
import logging
from utils import account_security as protection

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
        if not password or len(password) > 256:
            flash("Revisa tus credenciales.", "warning")
            return render_template("login.html")
        if not protection.allow_attempt("login", username, request.remote_addr or ""):
            flash("Demasiados intentos. Vuelve en diez minutos.", "warning")
            return render_template("login.html"), 429
        user = protection.authenticate(username, password or "", request.form.get("otp", ""))

        if user:
            logger.info("Login exitoso para usuario=%s", username)
            session.clear()
            session.permanent = request.form.get('remember') == 'on'
            session["auth_epoch"] = user.get("auth_epoch", 0)
            session['user'] = session_identity(user)
            session['user_id'] = user.get('id')
            session['username'] = user.get('username')
            session['role'] = user.get('role', 'user')
            target = request.args.get('next')
            dashboard = {"admin": "admin.dashboard", "business_owner": "owner.dashboard"}.get(user.get("role"), "main.index")
            destination = target if is_safe_redirect_url(target) else url_for(dashboard)
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

        if 'password_confirm' in request.form and request.form.get('password_confirm') != password:
            flash('Las contraseñas no coinciden.', 'error')
            return render_template('register.html')
        from core.food_experience import normalize_business_details
        try:
            business_details = normalize_business_details(request.form) if role == 'business_owner' else {}
        except ValueError as error:
            flash(str(error), 'error')
            return render_template('register.html')

        if not protection.password_valid(password or ""):
            flash('La contraseña debe tener al menos 8 caracteres e incluir letras y números', 'error')
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
        if business_details:
            user_data['profile']['business_details'] = business_details
        
        from database.repository import document_transaction
        from models.communication import admins, notify
        with document_transaction():
            user = UserModel.create(user_data)
            notify([a["id"] for a in admins()], "Nuevo registro", f"Se registró la cuenta {username}.",
                   url_for("admin.users"))
        logger.info(f"✅ Usuario {username} creado con ID: {user.get('id')} (Rol: {role})")
        flash('¡Registro exitoso! Ahora puedes iniciar sesión', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')

@auth_bp.route("/seguridad", methods=["GET", "POST"])
def account_security():
    if not session.get("user_id"):
        return redirect(url_for("auth.login", next=request.path))
    result = {}
    if request.method == "POST":
        if not protection.allow_attempt("settings", str(session["user_id"]), request.remote_addr or ""):
            return render_template("auth/security.html", result={}, recovery=False), 429
        try:
            result = protection.configure(session["user_id"], request.form.get("password", ""),
                                          request.form.get("action"), request.form.get("otp", ""),
                                          email=request.form.get('email'), phone=request.form.get('phone'))
            if "epoch" in result:
                session["auth_epoch"] = result["epoch"]
        except ValueError as error:
            flash(str(error), "warning")
    return render_template("auth/security.html", result=result, recovery=False)


@auth_bp.after_request
def private_account_response(response):
    if request.endpoint in ('auth.recover', 'auth.profile', 'auth.account_security', 'auth.profile_photo'):
        response.headers['Cache-Control'] = 'no-store, private'
        response.headers['Referrer-Policy'] = 'no-referrer'
    return response


@auth_bp.route("/recuperar", methods=["GET", "POST"])
def recover():
    from utils import password_codes
    from utils.security_delivery import DeliveryUnavailable
    state = session.get('password_recovery') or {}
    if request.method == 'POST':
        action = request.form.get('action', 'backup')
        username = state.get('username', '') if action in ('verify_code', 'reset_password') else normalize_text(request.form.get('username'), max_length=80)
        if not protection.allow_attempt('recover', username, request.remote_addr or ''):
            flash('Demasiados intentos. Vuelve en diez minutos.', 'warning')
            return render_template('auth/recovery.html', state=state), 429
        if action == 'send_code':
            channel = request.form.get('channel', 'email')
            if channel not in ('email', 'sms'):
                flash('Selecciona correo o celular.', 'warning')
            else:
                try:
                    challenge = password_codes.issue(username, channel, state.get('challenge') if state.get('username') == username else None)
                    state = {'username': username, 'challenge': challenge, 'step': 'code', 'channel': channel}
                    session['password_recovery'] = state
                    flash('Si la cuenta tiene ese contacto asociado, recibira un codigo. Revisa correo no deseado. La entrega depende del proveedor.', 'success')
                except DeliveryUnavailable:
                    flash('El canal no esta disponible. Usa tu clave guardada o contacta con soporte.', 'warning')
        elif action == 'verify_code' and state.get('step') == 'code':
            token = password_codes.verify(username, state.get('challenge'), request.form.get('code', ''))
            if token:
                state = {**state, 'step': 'password', 'token': token}
                session['password_recovery'] = state
                flash('Codigo verificado. Puedes cambiar tu contrasena durante cinco minutos.', 'success')
            else:
                flash('Codigo no valido o vencido. Solicita otro si agotaste los cinco intentos.', 'warning')
        elif action in ('reset_password', 'backup'):
            password = request.form.get('password', '')
            if password != request.form.get('password_confirm', password) or not protection.password_valid(password):
                flash('Las contrasenas deben coincidir: 8 a 256 caracteres, letras y numeros.', 'warning')
            elif (action == 'reset_password' and state.get('step') == 'password' and password_codes.complete(username, state.get('challenge'), state.get('token'), password)) or (action == 'backup' and protection.reset_password(username, request.form.get('code', ''), password)):
                session.clear()
                flash('Contrasena actualizada. Inicia sesion de nuevo.', 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Autorizacion no valida o vencida. Solicita otro codigo.', 'warning')
        return redirect(url_for('auth.recover'))
    return render_template('auth/recovery.html', state=state)


@auth_bp.post('/logout')
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
    from utils.security import fresh_session_user
    user = fresh_session_user()
    if not user:
        flash('Debes iniciar sesión para ver tu perfil', 'warning')
        return redirect(url_for('auth.login', next=request.path))
    
    logger.info(f"👤 Cargando perfil de: {user.get('username')}")
    
    if user.get('id'):
        updated_user = UserModel.get_by_id(user.get('id'))
        if updated_user:
            user = session_identity(updated_user)
            session['user'] = user
            user = {**user, 'profile': updated_user.get('profile') or {}}
            session['user_id'] = user['id']
            session['role'] = user['role']
    
    # ✅ Usar template según rol
    if user.get('role') == 'business_owner':
        return render_template('auth/profile_owner.html', user=user)
    else:
        from models.review import ReviewModel
        from models.market import kitchen
        from logic.market import now
        coupons = []
        for fav in FavoriteModel.get_by_user(user["id"]):
            shop = RestaurantModel.get_by_id(fav["restaurant_id"])
            if shop and shop.get("verified"):
                coupon = kitchen(shop["id"]).get("coupon") or {}
                if coupon.get("until", "") >= now().date().isoformat():
                    coupons.append((shop, coupon))
        return render_template("auth/profile.html", user=user, reviews=ReviewModel.get_by_user(user["id"]), coupons=coupons)
    
    
    
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

@auth_bp.get('/profile/photo/<kind>')
def profile_photo(kind):
    from flask import current_app, send_from_directory, abort
    from pathlib import Path
    from utils.security import fresh_session_user
    identity = fresh_session_user()
    if not identity:
        abort(401)
    if kind not in ('avatar', 'background'):
        abort(404)
    user = UserModel.get_by_id(identity['id'])
    filename = (user.get('profile') or {}).get(kind, '')
    if not re.fullmatch(r'[a-f0-9]{48}\.jpg', filename):
        abort(404)
    return send_from_directory(Path(current_app.instance_path) / 'profile_images' / str(identity['id']), filename, mimetype='image/jpeg')


@auth_bp.route('/profile/update', methods=['POST'])
def update_profile():
    """Actualizar perfil del usuario"""
    from utils.security import fresh_session_user
    user = fresh_session_user()
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

    def failed(message, status=400):
        if request.headers.get('Accept') == 'application/json':
            return jsonify(success=False, error=message), status
        submitted = dict(profile)
        for key in ('name', 'email', 'phone', 'birthday', 'daily_budget', 'weekly_budget'):
            if key in request.form:
                submitted[key] = request.form[key]
        submitted.update(preferences=request.form.getlist('preferences'),
                         restrictions=request.form.getlist('restrictions'),
                         addresses=request.form.get('addresses', '').splitlines(),
                         notification_preferences={
                             'transactional': request.form.get('transactional_notifications') == 'on',
                             'marketing': request.form.get('promotions_opt_in') == 'on',
                             'reviews': request.form.get('review_notifications') == 'on',
                             'waitlist': request.form.get('waitlist_notifications') == 'on'},
                         location_consent=request.form.get('location_consent') == 'on',
                         cookies_consent=request.form.get('cookies_consent') == 'on')
        template = 'auth/profile_owner.html' if user.get('role') == 'business_owner' else 'auth/profile.html'
        return render_template(template, user={**user, 'profile': submitted},
                               profile_error=message, reviews=[], coupons=[]), status

    try:
        payload = {
            'name': request.form.get('name', profile.get('name')),
            'email': request.form.get('email', profile.get('email')),
            'phone': request.form.get('phone', profile.get('phone', '')),
            'preferences': request.form.getlist('preferences'),
            'restrictions': request.form.getlist('restrictions'),
            'addresses': request.form.get('addresses', '').splitlines(),
            'daily_budget': request.form.get('daily_budget'),
            'weekly_budget': request.form.get('weekly_budget'),
            'notification_preferences': {
                'transactional': request.form.get('transactional_notifications') == 'on',
                'marketing': request.form.get('promotions_opt_in') == 'on',
                'reviews': request.form.get('review_notifications') == 'on',
                'waitlist': request.form.get('waitlist_notifications') == 'on',
            },
            'location_consent': request.form.get('location_consent') == 'on',
            'cookies_consent': request.form.get('cookies_consent') == 'on',
        }
        if 'birthday' in request.form:
            payload['birthday'] = request.form.get('birthday')
        changes = normalize_profile_patch(payload)
    except ValueError as error:
        return failed(str(error))
    if not protection.allow_attempt('profile', str(user_id), request.remote_addr or ''):
        return failed('Demasiados intentos. Vuelve en diez minutos.', 429)
    try:
        from core.profile import save_profile_image
        from database.repository import document_transaction, PostgresDocumentRepository
        epoch = None
        with document_transaction():
            db_user = PostgresDocumentRepository.get_by_id('users', user_id, for_update=True)
            if not UserModel.is_active(db_user) or db_user.get('auth_epoch', 0) != session.get('auth_epoch', 0):
                raise ValueError('La sesion cambio. Inicia sesion de nuevo.')
            profile = dict(db_user.get('profile') or {})
            if changes.get('email') != profile.get('email', '') or changes.get('phone') != profile.get('phone', ''):
                result = protection.configure(user_id, request.form.get('current_password', ''),
                                              'contacts', request.form.get('otp', ''),
                                              email=changes['email'], phone=changes['phone'])
                epoch = result['epoch']
                profile = dict(UserModel.get_by_id(user_id).get('profile') or {})
            for kind in ('avatar', 'background'):
                upload = request.files.get(kind)
                if upload and upload.filename:
                    changes[kind] = save_profile_image(upload, user_id, kind)
            profile.update(changes)
            profile['promotions_opt_in'] = profile.get('notification_preferences', {}).get('marketing', False)
            saved = UserModel.update(user_id, {'profile': profile})
            if not saved or saved.get('profile') != profile:
                raise ValueError('No se pudo guardar el perfil. Intenta de nuevo.')
    except ValueError as error:
        return failed(str(error))
    if epoch is not None:
        session['auth_epoch'] = epoch
    session['user'] = session_identity(saved)
    
    logger.info(f"✅ Perfil actualizado para: {db_user.get('username')}")
    if request.headers.get('Accept') == 'application/json':
        return jsonify(success=True, message='Perfil actualizado correctamente')
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
        if not isinstance(data, dict) or not data:
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

@auth_bp.route("/api/favorites", methods=["GET"])
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


def _reset_with_code(username, code, password):
    from utils.password_codes import consume
    if len(code)==6 and code.isdigit():
        return consume(username,session.get('password_challenge',''),code,password)
    return protection.reset_password(username,code,password)
