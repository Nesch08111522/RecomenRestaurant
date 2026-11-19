"""Single-use ten-minute password challenges, hashed and transactionally limited."""
import hmac,re,secrets,time
from flask import current_app
from werkzeug.security import generate_password_hash
from database.repository import PostgresDocumentRepository as Repo, document_transaction
from models.user import UserModel
from utils.account_security import digest,password_valid
from utils.security_delivery import configured,send_code,DeliveryUnavailable
from utils.audit import record_event

COLLECTION='password_challenges'

# Delivery codes are unrelated to meal-recommendation history or account MFA seeds.

def contact(user,channel):
    profile=user.get('profile') or {}
    value=str(profile.get('phone' if channel=='sms' else 'email') or '').strip()
    valid=re.fullmatch(r'\+[1-9]\d{7,14}',value) if channel=='sms' else re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value)
    return value if valid and '\r' not in value and '\n' not in value else ''

def issue(username,channel,existing_challenge=None):
    if channel not in ('email','sms'):raise ValueError('Selecciona correo o SMS.')
    if not configured(channel):raise DeliveryUnavailable('delivery_not_configured')
    challenge=secrets.token_urlsafe(24)
    user=UserModel.get_by_username(username)
    if not UserModel.is_active(user) or not contact(user,channel):return challenge
    uid=user['id'];destination=contact(user,channel);code=f'{secrets.randbelow(1000000):06d}';stamp=time.time()
    with document_transaction():
        Repo.get_by_id('users',uid,for_update=True)
        old=Repo.get_by_id(COLLECTION,uid,for_update=True)
        if old and stamp-old.get('issued',0)<60:
            # A second click must not invalidate the code already sent to this session.
            return old['challenge'] if isinstance(existing_challenge,str) and hmac.compare_digest(old['challenge'],existing_challenge) else challenge
        fields={'challenge':challenge,'hash':digest('password-otp',str(uid)+':'+challenge+':'+code).hex(),'until':stamp+600,'issued':stamp,'attempts':0,'used':False,'delivered':False,'channel':channel,'contact_hash':digest('otp-contact',destination).hex(),'epoch':user.get('auth_epoch',0)}
        if old:Repo.update(COLLECTION,uid,fields)
        else:Repo.create(COLLECTION,{'id':uid,**fields})
    try:
        send_code(channel,destination,code,challenge)
    except DeliveryUnavailable:
        current_app.logger.warning('Security code delivery failed; no code or destination logged')
        return challenge
    with document_transaction():
        row=Repo.get_by_id(COLLECTION,uid,for_update=True)
        if row and row['challenge']==challenge:Repo.update(COLLECTION,uid,{'delivered':True})
        record_event('PASSWORD_CODE_SENT',resource_type='cuenta',resource_id=uid,metadata={'channel':channel})
    return challenge

def verify(username, challenge, code):
    if not re.fullmatch(r'[0-9]{6}', code or '') or not challenge or len(challenge) > 128:
        return None
    user = UserModel.get_by_username(username)
    if not UserModel.is_active(user):
        return None
    uid = user['id']
    with document_transaction():
        account = Repo.get_by_id('users', uid, for_update=True)
        row = Repo.get_by_id(COLLECTION, uid, for_update=True)
        if not UserModel.is_active(account) or not row or row.get('used') or not row.get('delivered') or row.get('attempts', 0) >= 5 or row.get('until', 0) <= time.time() or row['challenge'] != challenge or row.get('epoch') != account.get('auth_epoch', 0):
            return None
        if not hmac.compare_digest(row.get('contact_hash', ''), digest('otp-contact', contact(account, row['channel'])).hex()):
            return None
        Repo.update(COLLECTION, uid, {'attempts': row['attempts'] + 1})
        if not hmac.compare_digest(row['hash'], digest('password-otp', str(uid)+':'+challenge+':'+code).hex()):
            return None
        token = secrets.token_urlsafe(32)
        profile = dict(account.get('profile') or {})
        profile['phone_verified' if row['channel'] == 'sms' else 'email_verified'] = True
        Repo.update('users', uid, {'profile': profile})
        Repo.update(COLLECTION, uid, {'hash': '', 'reset_hash': digest('password-reset', token).hex(), 'reset_until': time.time()+300})
        return token


def complete(username, challenge, token, password):
    if not password_valid(password) or not token or len(token) > 128:
        return False
    user = UserModel.get_by_username(username)
    if not UserModel.is_active(user):
        return False
    uid = user['id']
    with document_transaction():
        account = Repo.get_by_id('users', uid, for_update=True)
        row = Repo.get_by_id(COLLECTION, uid, for_update=True)
        if not UserModel.is_active(account) or not row or row.get('used') or row.get('reset_until', 0) <= time.time() or row.get('challenge') != challenge or row.get('epoch') != account.get('auth_epoch', 0):
            return False
        if not hmac.compare_digest(row.get('reset_hash', ''), digest('password-reset', token).hex()) or not hmac.compare_digest(row.get('contact_hash', ''), digest('otp-contact', contact(account, row['channel'])).hex()):
            return False
        Repo.update('users', uid, {'password': generate_password_hash(password), 'auth_epoch': account.get('auth_epoch', 0)+1})
        Repo.update(COLLECTION, uid, {'used': True, 'hash': '', 'reset_hash': ''})
        record_event('PASSWORD_CHANGED_BY_CODE', resource_type='cuenta', resource_id=uid, actor_user_id=uid)
        return True


def consume(username,challenge,code,password):
    if not password_valid(password) or not re.fullmatch(r'[0-9]{6}',code or '') or len(challenge or '')>128:return False
    user=UserModel.get_by_username(username)
    if not UserModel.is_active(user):return False
    uid=user['id']
    with document_transaction():
        account=Repo.get_by_id('users',uid,for_update=True)
        row=Repo.get_by_id(COLLECTION,uid,for_update=True)
        if not UserModel.is_active(account) or not row or row.get('used') or not row.get('delivered') or row.get('attempts',0)>=5 or row.get('until',0)<=time.time() or row['challenge']!=challenge or row.get('epoch')!=account.get('auth_epoch',0):return False
        destination=contact(account,row['channel'])
        if not hmac.compare_digest(row.get('contact_hash',''),digest('otp-contact',destination).hex()):return False
        Repo.update(COLLECTION,uid,{'attempts':row['attempts']+1})
        if not hmac.compare_digest(row['hash'],digest('password-otp',str(uid)+':'+challenge+':'+code).hex()):return False
        Repo.update('users',uid,{'password':generate_password_hash(password),'auth_epoch':account.get('auth_epoch',0)+1})
        Repo.update(COLLECTION,uid,{'used':True,'hash':''})
        record_event('PASSWORD_CHANGED_BY_CODE',resource_type='cuenta',resource_id=uid,actor_user_id=uid)
    return True
