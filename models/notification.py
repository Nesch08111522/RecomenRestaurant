# models/notification.py
from models.base import DataModel
from datetime import datetime
from zoneinfo import ZoneInfo
from database.repository import document_transaction

class NotificationModel(DataModel):
    """Modelo para gestionar notificaciones de usuarios"""
    collection = "notifications"
    
    @classmethod
    def get_by_user(cls, user_id, limit=10, archived=False, before=None):
        """Obtener notificaciones de un usuario"""
        with document_transaction() as conn:
            rows = conn.execute("SELECT payload FROM public.app_records WHERE collection='notifications' "
                "AND payload->>'user_id'=%s AND NOT payload @> '{\"deleted\": true}'::jsonb "
                "AND (payload @> '{\"archived\": true}'::jsonb)=%s "
                "AND (%s::bigint IS NULL OR id < %s) ORDER BY id DESC LIMIT %s",
                (str(user_id), archived, before, before, min(max(int(limit), 1), 100)))
            return [r["payload"] for r in rows]
    
    @classmethod
    def get_unread_count(cls, user_id):
        """Contar notificaciones no leídas"""
        with document_transaction() as conn:
            return conn.execute("SELECT count(*) AS n FROM public.app_records WHERE collection='notifications' "
                "AND payload->>'user_id'=%s AND NOT payload @> '{\"read\": true}'::jsonb "
                "AND NOT payload @> '{\"archived\": true}'::jsonb AND NOT payload @> '{\"deleted\": true}'::jsonb",
                (str(user_id),)).fetchone()["n"]
    
    @classmethod
    def mark_as_read(cls, user_id, notification_id):
        """Marcar una notificación como leída"""
        return cls.change_state(user_id, notification_id, 'read')

    @classmethod
    def change_state(cls, user_id, notification_id, action):
        changes = {'read': {'read': True}, 'archive': {'archived': True},
                   'restore': {'archived': False}, 'delete': {'deleted': True}}
        if action not in changes:
            raise ValueError('Invalid notification action')
        from database.repository import PostgresDocumentRepository as Repo
        with document_transaction():
            notification = Repo.get_by_id(cls.collection, notification_id, for_update=True)
            if (not notification or notification.get('deleted') or
                    str(notification.get('user_id')) != str(user_id)):
                return False
            return bool(cls.update(notification_id, changes[action]))
    
    @classmethod
    def mark_all_as_read(cls, user_id):
        """Marcar todas las notificaciones como leídas"""
        with document_transaction() as conn:
            changed = conn.execute("UPDATE public.app_records SET payload=payload || '{\"read\": true}'::jsonb, "
                "updated_at=CURRENT_TIMESTAMP WHERE collection='notifications' AND payload->>'user_id'=%s "
                "AND NOT payload @> '{\"read\": true}'::jsonb "
                "AND NOT payload @> '{\"deleted\": true}'::jsonb "
                "AND NOT payload @> '{\"archived\": true}'::jsonb", (str(user_id),))
            return bool(changed.rowcount)
    
    @classmethod
    def create_notification(cls, user_id, title, message, type_='info', link=None, event_key=None):
        """Crear una nueva notificación"""
        # Legacy producers (including companies/radar) already use this gateway.
        # Classify their existing event vocabulary without changing recipients.
        if type_ == 'info':
            import unicodedata
            normalized = ''.join(c for c in unicodedata.normalize('NFD', title.casefold())
                                 if unicodedata.category(c) != 'Mn')
            for kind, terms in (('order', ('pedido',)), ('subscription', ('suscripcion', 'empresa', 'plan')),
                                ('commercial', ('prospecto',)), ('message', ('mensaje',)),
                                ('warning', ('agotado', 'inventario', 'reclamo')),
                                ('reservation', ('mesa', 'reserva')), ('review', ('resena',))):
                if any(term in normalized for term in terms):
                    type_ = kind
                    break
        notification = {
            'user_id': user_id,
            'title': title,
            'message': message,
            'type': type_,
            'link': link,
            'read': False,
            'timestamp': datetime.now(ZoneInfo("America/Lima")).isoformat()
        }
        if user_id is None:
            raise ValueError('Notification recipient is required')
        if event_key is None:
            return cls.create(notification)
        # The key is scoped to one recipient; never deduplicate distinct business events by text.
        import hashlib
        key = str(event_key)
        notification['event_key'] = key
        lock = int.from_bytes(hashlib.sha256(f'{user_id}:{key}'.encode()).digest()[:8], 'big', signed=True)
        with document_transaction() as conn:
            conn.execute('SELECT pg_advisory_xact_lock(%s)', (lock,))
            row = conn.execute("SELECT payload FROM public.app_records WHERE collection='notifications' "
                "AND payload->>'user_id'=%s AND payload->>'event_key'=%s LIMIT 1",
                (str(user_id), key)).fetchone()
            return row['payload'] if row else cls.create(notification)
