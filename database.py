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
        # Таблица для системных данных
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS system (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """)

        # Таблица для ВСЕХ пользователей (основная таблица)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            display_name TEXT NOT NULL,  -- Имя, отображаемое в очереди
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            registered_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        )
        """)
        
        # Таблица для очереди (связь через user_id)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS queue (
            user_id INTEGER PRIMARY KEY,
            joined_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
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
        
        # Включаем внешние ключи
        self.cursor.execute("PRAGMA foreign_keys = ON")
        
        # Инициализируем статус кабинета, если пусто
        self.cursor.execute("SELECT COUNT(*) FROM office_status")
        if self.cursor.fetchone()[0] == 0:
            self.set_office_status("closed")
        
        self.conn.commit()

    # ---------------- Пользователи ----------------

    def add_or_update_user(self, user_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> str:
        """Добавить или обновить пользователя, возвращает display_name"""
        now = datetime.now().isoformat()
        
        # Формируем display_name из данных Telegram
        display_name = first_name or ""
        if last_name:
            if display_name:
                display_name += f" {last_name}"
            else:
                display_name = last_name
        
        # Если нет имени и фамилии, используем username
        if not display_name or display_name.strip() == "":
            if username:
                display_name = f"@{username}"
            else:
                display_name = f"User_{user_id}"
        
        # Добавляем/обновляем пользователя
        self.cursor.execute("""
        INSERT OR IGNORE INTO users 
        (user_id, display_name, username, first_name, last_name, registered_at, last_seen_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, display_name, username, first_name, last_name, now, now))
        
        self.cursor.execute("""
        UPDATE users SET 
            display_name = COALESCE(?, display_name),
            username = COALESCE(?, username),
            first_name = COALESCE(?, first_name),
            last_name = COALESCE(?, last_name),
            last_seen_at = ?
        WHERE user_id = ?
        """, (display_name, username, first_name, last_name, now, user_id))
        
        self.conn.commit()
        return display_name

    def get_all_users(self) -> List[Dict]:
        """Получить всех пользователей бота"""
        self.cursor.execute("SELECT * FROM users")
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

    def get_all_user_ids(self) -> List[int]:
        """Получить только ID всех пользователей"""
        self.cursor.execute("SELECT user_id FROM users")
        return [row[0] for row in self.cursor.fetchall()]

    def update_user_display_name(self, user_id: int, new_display_name: str) -> bool:
        """Изменить отображаемое имя пользователя (обновляет и в очереди через связь)"""
        if len(new_display_name.strip()) < 2:
            return False
        
        now = datetime.now().isoformat()
        
        # Обновляем имя в таблице users
        self.cursor.execute("""
        UPDATE users SET 
            display_name = ?,
            last_seen_at = ?
        WHERE user_id = ?
        """, (new_display_name.strip(), now, user_id))
        
        changed = self.cursor.rowcount
        self.conn.commit()
        
        return changed > 0

    def get_user_display_name(self, user_id: int) -> Optional[str]:
        """Получить отображаемое имя пользователя"""
        self.cursor.execute(
            "SELECT display_name FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = self.cursor.fetchone()
        return row[0] if row else None

    def get_user_full_info(self, user_id: int) -> Optional[Dict]:
        """Получить полную информацию о пользователе"""
        self.cursor.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        row = self.cursor.fetchone()
        return dict(row) if row else None

    # ---------------- Очередь ----------------

    def add_to_queue(self, user_id: int, name: str = None) -> int:
        """Добавить пользователя в очередь, вернуть его позицию"""
        # Проверка, не в очереди ли уже
        if self.get_user_position(user_id):
            return -1
        
        # Если имя не указано, берем из таблицы users
        if not name:
            name = self.get_user_display_name(user_id)
            if not name:
                # Создаем пользователя с базовыми данными
                name = f"User_{user_id}"
        
        # Убеждаемся, что пользователь есть в таблице users
        self.cursor.execute("SELECT COUNT(*) FROM users WHERE user_id = ?", (user_id,))
        if self.cursor.fetchone()[0] == 0:
            # Добавляем пользователя с минимальными данными
            self.cursor.execute(
                "INSERT INTO users (user_id, display_name, registered_at, last_seen_at) VALUES (?, ?, ?, ?)",
                (user_id, name, datetime.now().isoformat(), datetime.now().isoformat())
            )
        else:
            # Обновляем display_name если нужно
            self.cursor.execute(
                "UPDATE users SET display_name = ?, last_seen_at = ? WHERE user_id = ?",
                (name, datetime.now().isoformat(), user_id)
            )
        
        # Добавляем в очередь
        joined_at = datetime.now().isoformat()
        self.cursor.execute(
            "INSERT INTO queue (user_id, joined_at) VALUES (?, ?)",
            (user_id, joined_at)
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
        """Получить всю очередь в порядке добавления с именами пользователей"""
        self.cursor.execute("""
        SELECT q.user_id, u.display_name as name, q.joined_at
        FROM queue q
        LEFT JOIN users u ON q.user_id = u.user_id
        ORDER BY q.joined_at
        """)
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
        self.cursor.execute("""
        SELECT q.user_id, u.display_name as name, q.joined_at
        FROM queue q
        LEFT JOIN users u ON q.user_id = u.user_id
        ORDER BY q.joined_at LIMIT 1
        """)
        row = self.cursor.fetchone()
        if row:
            user = dict(row)
            self.remove_from_queue(user["user_id"])
            return user
        return None

    def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Получить информацию о пользователе в очереди"""
        self.cursor.execute("""
        SELECT q.user_id, u.display_name as name, q.joined_at
        FROM queue q
        LEFT JOIN users u ON q.user_id = u.user_id
        WHERE q.user_id = ?
        """, (user_id,))
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def search_user_by_name(self, search_term: str) -> List[Dict]:
        """Поиск пользователя по имени (частичному совпадению)"""
        self.cursor.execute("""
        SELECT q.user_id, u.display_name as name, q.joined_at
        FROM queue q
        LEFT JOIN users u ON q.user_id = u.user_id
        WHERE u.display_name LIKE ? 
        ORDER BY q.joined_at
        """, (f"%{search_term}%",))
        rows = self.cursor.fetchall()
        return [dict(row) for row in rows]

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

    # ---------------- Управление очередью ----------------
    def get_first_user_in_queue(self) -> Optional[Dict]:
        """Получить первого пользователя в очереди (без удаления)"""
        self.cursor.execute("""
        SELECT q.user_id, u.display_name as name, q.joined_at
        FROM queue q
        LEFT JOIN users u ON q.user_id = u.user_id
        ORDER BY q.joined_at LIMIT 1
        """)
        row = self.cursor.fetchone()
        return dict(row) if row else None

    def get_current_serving_user(self) -> Optional[int]:
        """Получить ID пользователя, которого сейчас принимают (если есть)"""
        self.cursor.execute("SELECT value FROM system WHERE key = 'current_serving'")
        row = self.cursor.fetchone()
        return int(row[0]) if row else None

    def set_current_serving_user(self, user_id: Optional[int]):
        """Установить ID пользователя, которого сейчас принимают"""
        if user_id is None:
            self.cursor.execute("DELETE FROM system WHERE key = 'current_serving'")
        else:
            self.cursor.execute("""
            INSERT OR REPLACE INTO system (key, value)
            VALUES ('current_serving', ?)
            """, (str(user_id),))
        self.conn.commit()

    def is_user_being_served(self, user_id: int) -> bool:
        """Проверяет, обслуживается ли пользователь сейчас"""
        current = self.get_current_serving_user()
        return current == user_id

# ---------------- Экземпляр ----------------
db = QueueDB()
