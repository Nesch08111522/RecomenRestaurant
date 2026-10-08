# models/notification.py
from models.base import JSONModel
from config import Config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class NotificationModel(JSONModel):
    """Modelo para gestionar notificaciones de usuarios"""
    file_path = Config.NOTIFICATIONS_FILE if hasattr(Config, 'NOTIFICATIONS_FILE') else None
    
    @classmethod
    def get_by_user(cls, user_id, limit=10):
        """Obtener notificaciones de un usuario"""
        if not cls.file_path:
            return []
        data = cls._load_data()
        user_notifications = [n for n in data if n.get('user_id') == user_id]
        user_notifications.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return user_notifications[:limit]
    
    @classmethod
    def get_unread_count(cls, user_id):
        """Contar notificaciones no leídas"""
        if not cls.file_path:
            return 0
        data = cls._load_data()
        return len([n for n in data if n.get('user_id') == user_id and not n.get('read', False)])
    
    @classmethod
    def mark_as_read(cls, user_id, notification_id):
        """Marcar una notificación como leída"""
        if not cls.file_path:
            return False
        data = cls._load_data()
        for n in data:
            if n.get('user_id') == user_id and n.get('id') == notification_id:
                n['read'] = True
                cls._save_data(data)
                return True
        return False
    
    @classmethod
    def mark_all_as_read(cls, user_id):
        """Marcar todas las notificaciones como leídas"""
        if not cls.file_path:
            return False
        data = cls._load_data()
        for n in data:
            if n.get('user_id') == user_id:
                n['read'] = True
        cls._save_data(data)
        return True
    
    @classmethod
    def create_notification(cls, user_id, title, message, type_='info', link=None):
        """Crear una nueva notificación"""
        if not cls.file_path:
            return None
        notification = {
            'user_id': user_id,
            'title': title,
            'message': message,
            'type': type_,
            'link': link,
            'read': False,
            'timestamp': datetime.now().isoformat()
        }
        return cls.create(notification)