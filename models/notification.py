# models/notification.py
from models.base import DataModel
from datetime import datetime

class NotificationModel(DataModel):
    """Modelo para gestionar notificaciones de usuarios"""
    collection = "notifications"
    
    @classmethod
    def get_by_user(cls, user_id, limit=10):
        """Obtener notificaciones de un usuario"""
        data = cls._load_data()
        user_notifications = [n for n in data if n.get('user_id') == user_id]
        user_notifications.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return user_notifications[:limit]
    
    @classmethod
    def get_unread_count(cls, user_id):
        """Contar notificaciones no leídas"""
        data = cls._load_data()
        return len([n for n in data if n.get('user_id') == user_id and not n.get('read', False)])
    
    @classmethod
    def mark_as_read(cls, user_id, notification_id):
        """Marcar una notificación como leída"""
        notification = cls.get_by_id(notification_id)
        if not notification or notification.get('user_id') != user_id:
            return False
        return bool(cls.update(notification_id, {'read': True}))
    
    @classmethod
    def mark_all_as_read(cls, user_id):
        """Marcar todas las notificaciones como leídas"""
        notifications = [n for n in cls._load_data() if n.get('user_id') == user_id]
        for notification in notifications:
            cls.update(notification.get('id'), {'read': True})
        return bool(notifications)
    
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
            'timestamp': datetime.now().isoformat()
        }
        return cls.create(notification)
