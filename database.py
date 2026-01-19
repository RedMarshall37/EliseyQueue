import sqlite3
from typing import List, Optional, Dict
from datetime import datetime

DB_PATH = "queue.db"

class QueueDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._setup_tables()

    def _setup_tables(self):
        # Таблица для ВСЕХ пользователей
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        )
        """)
        
        # Таблица для очереди
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            user_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            joined_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        """)
        
        # Таблица для статуса кабинета
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS office_status (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            status TEXT NOT NULL,
            message TEXT,
            updated_at TEXT NOT NULL
        )
        """)
        
        # Инициализируем статус кабинета, если пусто
        self.cursor.execute("SELECT COUNT(*) FROM office_status")
        if self.cursor.fetchone()[0] == 0:
            self.set_office_status("closed")
        
        self.conn.commit()

    # ---------------- Пользователи ----------------

    def add_or_update_user(self, user_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None):
        """Добавить или обновить пользователя"""
        now = datetime.now().isoformat()
        
        self.cursor.execute("""
        INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, registered_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, username, first_name, last_name, now, now))
        
        self.cursor.execute("""
        UPDATE users SET 
            username = COALESCE(?, username),
            first_name = COALESCE(?, first_name),
            last_name = COALESCE(?, last_name),
            last_seen_at = ?
        WHERE user_id = ?
        """, (username, first_name, last_name, now, user_id))
        
        self.conn.commit()

    def get_all_users(self) -> List[Dict]:
        """Получить всех пользователей бота"""
        self.cursor.execute("SELECT user_id FROM users")
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_user_ids(self) -> List[int]:
        """Получить только ID всех пользователей"""
        self.cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in self.cursor.fetchall()]

    # ---------------- Очередь ----------------

    def add_to_queue(self, user_id: int, name: str) -> int:
        """Добавить пользователя в очередь, вернуть его позицию"""
        # Проверка, не в очереди ли уже
        if self.get_user_position(user_id):
            return -1

        joined_at = datetime.now().isoformat()
        self.cursor.execute(
            "INSERT INTO queue (user_id, name, joined_at) VALUES (?, ?, ?)",
            (user_id, name, joined_at)
        )
        self.conn.commit()
        return self.get_user_position(user_id)

    def remove_from_queue(self, user_id: int) -> bool:
        """Удалить пользователя из очереди"""
        self.cursor.execute("DELETE FROM queue WHERE user_id = ?", (user_id,))
        changed = self.cursor.rowcount
        self.conn.commit()
        return changed > 0

    def get_queue(self) -> List[Dict]:
        """Получить всю очередь в порядке добавления"""
        self.cursor.execute("SELECT * FROM queue ORDER BY joined_at")
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_user_position(self, user_id: int) -> Optional[int]:
        """Получить позицию пользователя в очереди (1 = первый)"""
        queue = self.get_queue()
        for i, user in enumerate(queue, start=1):
            if user["user_id"] == user_id:
                return i
        return None

    def clear_queue(self):
        """Очистить всю очередь"""
        self.cursor.execute("DELETE FROM queue")
        self.conn.commit()

    def get_next_user(self) -> Optional[Dict]:
        """Получить следующего пользователя и удалить его из очереди"""
        self.cursor.execute("SELECT * FROM queue ORDER BY joined_at LIMIT 1")
        row = self.cursor.fetchone()
        if row:
            user = dict(row)
            self.remove_from_queue(user["user_id"])
            return user
        return None

    # ---------------- Статус кабинета ----------------

    def set_office_status(self, status: str, message: str = ""):
        """Установить статус кабинета (open/closed/paused)"""
        updated_at = datetime.now().isoformat()
        self.cursor.execute("""
        INSERT INTO office_status (id, status, message, updated_at)
        VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status=excluded.status,
            message=excluded.message,
            updated_at=excluded.updated_at
        """, (status, message, updated_at))
        self.conn.commit()

    def get_office_status(self) -> Dict:
        """Получить статус кабинета"""
        self.cursor.execute("SELECT * FROM office_status WHERE id = 1")
        row = self.cursor.fetchone()
        if row:
            return dict(row)
        return {"status": "closed", "message": "", "updated_at": datetime.now().isoformat()}

# ---------------- Экземпляр ----------------
db = QueueDB()
