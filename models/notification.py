# models/notification.py
from models.base import DataModel
from datetime import datetime
from zoneinfo import ZoneInfo
from database.repository import document_transaction

class NotificationModel(DataModel):
    """Modelo para gestionar notificaciones de usuarios"""
    collection = "notifications"
    
    @classmethod
    def get_by_user(cls, user_id, limit=10):
        """Obtener notificaciones de un usuario"""
        with document_transaction() as conn:
            rows = conn.execute("SELECT payload FROM public.app_records WHERE collection='notifications' "
                "AND payload->>'user_id'=%s ORDER BY id DESC LIMIT %s", (str(user_id),limit))
            return [r["payload"] for r in rows]
    
    @classmethod
    def get_unread_count(cls, user_id):
        """Contar notificaciones no leídas"""
        with document_transaction() as conn:
            return conn.execute("SELECT count(*) AS n FROM public.app_records WHERE collection='notifications' "
                "AND payload->>'user_id'=%s AND NOT payload @> '{\"read\": true}'::jsonb",
                (str(user_id),)).fetchone()["n"]
    
    @classmethod
    def mark_as_read(cls, user_id, notification_id):
        """Marcar una notificación como leída"""
        notification = cls.get_by_id(notification_id)
        if not notification or str(notification.get('user_id')) != str(user_id):
            return False
        return bool(cls.update(notification_id, {'read': True}))
    
    @classmethod
    def mark_all_as_read(cls, user_id):
        """Marcar todas las notificaciones como leídas"""
        with document_transaction() as conn:
            changed = conn.execute("UPDATE public.app_records SET payload=payload || '{\"read\": true}'::jsonb, "
                "updated_at=CURRENT_TIMESTAMP WHERE collection='notifications' AND payload->>'user_id'=%s "
                "AND NOT payload @> '{\"read\": true}'::jsonb", (str(user_id),))
            return bool(changed.rowcount)
    
    @classmethod
    def create_notification(cls, user_id, title, message, type_='info', link=None):
        """Crear una nueva notificación"""
        notification = {
            'user_id': user_id,
            'title': title,
            'message': message,
            'type': type_,
            'link': link,
            'read': False,
            'timestamp': datetime.now(ZoneInfo("America/Lima")).isoformat()
        }
        return cls.create(notification)
