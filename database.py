import os
import sqlite3

from config import Config
from logger import log


class Database:
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DATABASE_PATH

        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
            log.info(f"Создана директория для БД: {db_dir}")

        self.conn = None
        self._connect()
        self._create_tables()

    def _connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            log.info(f"Подключение к базе данных: {self.db_path}")
        except Exception as e:
            log.error(f"Ошибка подключения к БД: {e}")
            raise

    def _create_tables(self):
        cursor = self.conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                weight REAL NOT NULL,
                height INTEGER NOT NULL,
                gender TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS diet_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                profile_id INTEGER NOT NULL,
                plan_text TEXT NOT NULL,
                days_count INTEGER DEFAULT 7,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (profile_id) REFERENCES user_profiles(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (plan_id) REFERENCES diet_plans(id),
                UNIQUE(user_id, plan_id)
            )
        """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_profiles_user_id ON user_profiles(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_plans_user_id ON diet_plans(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id)")

        self.conn.commit()
        log.info("Таблицы базы данных созданы/проверены")

    def add_or_update_user(self, user_id, username=None, first_name=None, last_name=None):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (user_id, username, first_name, last_name))
            self.conn.commit()
            return True
        except Exception as e:
            log.error(f"Ошибка добавления пользователя в БД: {e}")
            return False

    def save_user_profile(self, user_id, profile_data):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO user_profiles (user_id, name, age, weight, height, gender)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                profile_data['name'],
                profile_data['age'],
                profile_data['weight'],
                profile_data['height'],
                profile_data['gender']
            ))
            self.conn.commit()
            profile_id = cursor.lastrowid
            log.info(f"Профиль пользователя {user_id} сохранен с ID: {profile_id}")
            return profile_id
        except Exception as e:
            log.error(f"Ошибка сохранения профиля в БД: {e}")
            return None

    def get_last_user_profile(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT name, age, weight, height, gender, created_at
                FROM user_profiles
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            log.error(f"Ошибка получения профиля из БД: {e}")
            return None

    def save_diet_plan(self, user_id, profile_id, plan_text, days_count=7):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT INTO diet_plans (user_id, profile_id, plan_text, days_count)
                VALUES (?, ?, ?, ?)
            """, (user_id, profile_id, plan_text, days_count))
            self.conn.commit()
            plan_id = cursor.lastrowid
            log.info(f"План питания сохранен с ID: {plan_id}")
            return plan_id
        except Exception as e:
            log.error(f"Ошибка сохранения плана в БД: {e}")
            return None

    def get_diet_plan(self, plan_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, user_id, plan_text, days_count, created_at
                FROM diet_plans
                WHERE id = ?
            """, (plan_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            log.error(f"Ошибка получения плана из БД: {e}")
            return None

    def get_last_diet_plan(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, user_id, plan_text, days_count, created_at
                FROM diet_plans
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            log.error(f"Ошибка получения последнего плана из БД: {e}")
            return None

    def add_to_favorites(self, user_id, plan_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO favorites (user_id, plan_id)
                VALUES (?, ?)
            """, (user_id, plan_id))
            self.conn.commit()
            if cursor.rowcount > 0:
                log.info(f"План {plan_id} добавлен в избранное пользователю {user_id}")
                return True
            return False
        except Exception as e:
            log.error(f"Ошибка добавления в избранное: {e}")
            return False

    def remove_from_favorites(self, user_id, plan_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM favorites
                WHERE user_id = ? AND plan_id = ?
            """, (user_id, plan_id))
            self.conn.commit()
            return True
        except Exception as e:
            log.error(f"Ошибка удаления из избранного: {e}")
            return False

    def is_in_favorites(self, user_id, plan_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT 1 FROM favorites
                WHERE user_id = ? AND plan_id = ?
            """, (user_id, plan_id))
            return cursor.fetchone() is not None
        except Exception as e:
            log.error(f"Ошибка проверки избранного: {e}")
            return False

    def get_favorites(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT dp.id, dp.plan_text, dp.days_count, dp.created_at, f.saved_at
                FROM diet_plans dp
                JOIN favorites f ON dp.id = f.plan_id
                WHERE f.user_id = ?
                ORDER BY f.saved_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            log.error(f"Ошибка получения избранных планов: {e}")
            return []

    def get_user_plan_count(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM diet_plans WHERE user_id = ?
            """, (user_id,))
            return cursor.fetchone()[0]
        except Exception as e:
            log.error(f"Ошибка получения количества планов: {e}")
            return 0

    def close(self):
        if self.conn:
            self.conn.close()
            log.info("Подключение к базе данных закрыто")


db = Database()
