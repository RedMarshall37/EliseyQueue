import redis
import json
from typing import List, Optional, Dict
from datetime import datetime
import config

class QueueDB:
    def __init__(self):
        self.redis = redis.from_url(config.config.REDIS_URL, decode_responses=True)
    
    # Очередь
    def add_to_queue(self, user_id: int, name: str) -> int:
        """Добавить пользователя в очередь, вернуть его номер"""
        queue_key = "office:queue"
        
        # Проверяем, не в очереди ли уже
        if self.redis.hexists("office:users", user_id):
            return -1
        
        # Генерируем ID для позиции
        position_id = self.redis.incr("office:counter")
        
        user_data = {
            "user_id": user_id,
            "name": name,
            "position": position_id,
            "joined_at": datetime.now().isoformat()
        }
        
        # Сохраняем в хэше пользователей
        self.redis.hset("office:users", user_id, json.dumps(user_data))
        # Добавляем в очередь
        self.redis.rpush(queue_key, user_id)
        
        return position_id
    
    def remove_from_queue(self, user_id: int) -> bool:
        """Удалить пользователя из очереди"""
        if self.redis.hexists("office:users", user_id):
            self.redis.hdel("office:users", user_id)
            self.redis.lrem("office:queue", 0, user_id)
            return True
        return False
    
    def get_queue(self) -> List[Dict]:
        """Получить всю очередь"""
        user_ids = self.redis.lrange("office:queue", 0, -1)
        queue = []
        
        for user_id in user_ids:
            user_data = self.redis.hget("office:users", user_id)
            if user_data:
                queue.append(json.loads(user_data))
        
        return queue
    
    def get_user_position(self, user_id: int) -> Optional[int]:
        """Получить позицию пользователя в очереди"""
        user_ids = self.redis.lrange("office:queue", 0, -1)
        
        try:
            position = user_ids.index(str(user_id)) + 1
            return position
        except ValueError:
            return None
    
    # Управление кабинетом
    def set_office_status(self, status: str, message: str = ""):
        """Установить статус кабинета (open/closed/paused)"""
        data = {
            "status": status,
            "message": message,
            "updated_at": datetime.now().isoformat()
        }
        self.redis.set("office:status", json.dumps(data))
    
    def get_office_status(self) -> Dict:
        """Получить статус кабинета"""
        data = self.redis.get("office:status")
        if data:
            return json.loads(data)
        return {"status": "closed", "message": "", "updated_at": datetime.now().isoformat()}
    
    def clear_queue(self):
        """Очистить всю очередь"""
        self.redis.delete("office:queue")
        self.redis.delete("office:users")
    
    def get_next_user(self) -> Optional[Dict]:
        """Получить следующего пользователя и удалить из очереди"""
        user_id = self.redis.lpop("office:queue")
        if user_id:
            user_data = self.redis.hget("office:users", user_id)
            self.redis.hdel("office:users", user_id)
            if user_data:
                return json.loads(user_data)
        return None

db = QueueDB()