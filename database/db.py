import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict

class Database:
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Подключение к базе данных"""
        self.conn = await aiosqlite.connect(self.db_path)
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.create_tables()

    async def close(self):
        """Закрытие соединения"""
        if self.conn:
            await self.conn.close()

    async def create_tables(self):
        """Создание всех необходимых таблиц"""
        # Таблица для кэша капч
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS captcha_cache (
                user_id INTEGER PRIMARY KEY,
                captcha_code TEXT NOT NULL,
                expires_at REAL NOT NULL,
                message_id INTEGER
            )
        """)

        # Таблица для предупреждений
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                timestamp REAL NOT NULL
            )
        """)

        # Таблица для мутов
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS mutes (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                expires_at REAL,
                reason TEXT,
                moderator_id INTEGER,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        # Таблица для анти-спама (отслеживание сообщений)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS spam_tracking (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                message_count INTEGER DEFAULT 1,
                first_message_time REAL NOT NULL,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        # Таблица для анти-нюка (отслеживание действий)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS nuke_tracking (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                count INTEGER DEFAULT 1,
                first_action_time REAL NOT NULL,
                PRIMARY KEY (user_id, guild_id, action_type)
            )
        """)

        # Таблица для верифицированных пользователей
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS verified_users (
                user_id INTEGER PRIMARY KEY,
                guild_id INTEGER NOT NULL,
                verified_at REAL NOT NULL
            )
        """)

        # Таблица для бэкапа сервера (название, иконка)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS server_backup (
                guild_id INTEGER PRIMARY KEY,
                server_name TEXT,
                server_icon TEXT,
                updated_at REAL NOT NULL
            )
        """)

        # Таблица для активности администраторов
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS admin_activity (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                last_activity REAL NOT NULL,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        # Таблица для whitelist ботов
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_whitelist (
                bot_id INTEGER PRIMARY KEY,
                added_by INTEGER NOT NULL,
                added_at REAL NOT NULL
            )
        """)

        # Таблица для чёрного списка
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS blacklist (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                added_by INTEGER NOT NULL,
                added_at REAL NOT NULL,
                expires_at REAL,
                reason TEXT,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        # Таблица для теней (Protection Shadows)
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS protection_shadows (
                guild_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                shadow_data TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (guild_id, item_type, item_id)
            )
        """)

        # Таблица для Trust Levels
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trust_levels (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                trust_score INTEGER NOT NULL,
                last_updated REAL NOT NULL,
                PRIMARY KEY (user_id, guild_id)
            )
        """)

        # Таблица для статистики защиты
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS security_stats (
                guild_id INTEGER PRIMARY KEY,
                nuke_attempts INTEGER DEFAULT 0,
                blocked_attacks INTEGER DEFAULT 0,
                raid_detections INTEGER DEFAULT 0,
                last_updated REAL NOT NULL
            )
        """)

        # Таблица для бэкапов сервера
        await self.conn.execute("""
            CREATE TABLE IF NOT EXISTS server_backups (
                guild_id INTEGER NOT NULL,
                backup_data TEXT NOT NULL,
                created_at REAL NOT NULL,
                PRIMARY KEY (guild_id, created_at)
            )
        """)

        await self.conn.commit()

    # Капча методы
    async def save_captcha(self, user_id: int, captcha_code: str, expires_at: float, message_id: int):
        """Сохранение капчи в кэш"""
        await self.conn.execute("""
            INSERT OR REPLACE INTO captcha_cache (user_id, captcha_code, expires_at, message_id)
            VALUES (?, ?, ?, ?)
        """, (user_id, captcha_code, expires_at, message_id))
        await self.conn.commit()

    async def get_captcha(self, user_id: int) -> Optional[Dict]:
        """Получение капчи из кэша"""
        cursor = await self.conn.execute("""
            SELECT captcha_code, expires_at, message_id
            FROM captcha_cache
            WHERE user_id = ?
        """, (user_id,))
        row = await cursor.fetchone()
        if row:
            return {
                "code": row[0],
                "expires_at": row[1],
                "message_id": row[2]
            }
        return None

    async def delete_captcha(self, user_id: int):
        """Удаление капчи из кэша"""
        await self.conn.execute("DELETE FROM captcha_cache WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    # Предупреждения
    async def add_warning(self, user_id: int, moderator_id: int, reason: str):
        """Добавление предупреждения"""
        await self.conn.execute("""
            INSERT INTO warnings (user_id, moderator_id, reason, timestamp)
            VALUES (?, ?, ?, ?)
        """, (user_id, moderator_id, reason, datetime.now().timestamp()))
        await self.conn.commit()

    async def get_warnings(self, user_id: int) -> List[Dict]:
        """Получение всех предупреждений пользователя"""
        cursor = await self.conn.execute("""
            SELECT id, moderator_id, reason, timestamp
            FROM warnings
            WHERE user_id = ?
            ORDER BY timestamp DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "moderator_id": row[1],
                "reason": row[2],
                "timestamp": row[3]
            }
            for row in rows
        ]

    async def remove_warning(self, warning_id: int):
        """Удаление предупреждения"""
        await self.conn.execute("DELETE FROM warnings WHERE id = ?", (warning_id,))
        await self.conn.commit()

    # Муты
    async def add_mute(self, user_id: int, guild_id: int, expires_at: Optional[float], reason: str, moderator_id: int):
        """Добавление мута"""
        await self.conn.execute("""
            INSERT OR REPLACE INTO mutes (user_id, guild_id, expires_at, reason, moderator_id)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, guild_id, expires_at, reason, moderator_id))
        await self.conn.commit()

    async def get_mute(self, user_id: int, guild_id: int) -> Optional[Dict]:
        """Получение мута"""
        cursor = await self.conn.execute("""
            SELECT expires_at, reason, moderator_id
            FROM mutes
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))
        row = await cursor.fetchone()
        if row:
            return {
                "expires_at": row[0],
                "reason": row[1],
                "moderator_id": row[2]
            }
        return None

    async def remove_mute(self, user_id: int, guild_id: int):
        """Удаление мута"""
        await self.conn.execute("DELETE FROM mutes WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        await self.conn.commit()

    async def get_all_expired_mutes(self, current_time: float) -> List[Dict]:
        """Получение всех истёкших мутов"""
        cursor = await self.conn.execute("""
            SELECT user_id, guild_id, expires_at, reason, moderator_id
            FROM mutes
            WHERE expires_at IS NOT NULL AND expires_at <= ?
        """, (current_time,))
        rows = await cursor.fetchall()
        return [
            {
                "user_id": row[0],
                "guild_id": row[1],
                "expires_at": row[2],
                "reason": row[3],
                "moderator_id": row[4]
            }
            for row in rows
        ]

    # Анти-спам
    async def track_message(self, user_id: int, guild_id: int):
        """Отслеживание сообщения для анти-спама"""
        now = datetime.now().timestamp()
        cursor = await self.conn.execute("""
            SELECT message_count, first_message_time
            FROM spam_tracking
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))
        row = await cursor.fetchone()
        
        if row:
            await self.conn.execute("""
                UPDATE spam_tracking
                SET message_count = message_count + 1
                WHERE user_id = ? AND guild_id = ?
            """, (user_id, guild_id))
        else:
            await self.conn.execute("""
                INSERT INTO spam_tracking (user_id, guild_id, message_count, first_message_time)
                VALUES (?, ?, 1, ?)
            """, (user_id, guild_id, now))
        await self.conn.commit()

    async def get_spam_count(self, user_id: int, guild_id: int, time_window: int) -> int:
        """Получение количества сообщений за период"""
        cutoff = datetime.now().timestamp() - time_window
        cursor = await self.conn.execute("""
            SELECT message_count, first_message_time
            FROM spam_tracking
            WHERE user_id = ? AND guild_id = ? AND first_message_time > ?
        """, (user_id, guild_id, cutoff))
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def reset_spam_tracking(self, user_id: int, guild_id: int):
        """Сброс отслеживания спама"""
        await self.conn.execute("""
            DELETE FROM spam_tracking
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))
        await self.conn.commit()

    # Анти-нюк
    async def track_nuke_action(self, user_id: int, guild_id: int, action_type: str):
        """Отслеживание действия для анти-нюка"""
        now = datetime.now().timestamp()
        cursor = await self.conn.execute("""
            SELECT count, first_action_time
            FROM nuke_tracking
            WHERE user_id = ? AND guild_id = ? AND action_type = ?
        """, (user_id, guild_id, action_type))
        row = await cursor.fetchone()
        
        if row:
            await self.conn.execute("""
                UPDATE nuke_tracking
                SET count = count + 1
                WHERE user_id = ? AND guild_id = ? AND action_type = ?
            """, (user_id, guild_id, action_type))
        else:
            await self.conn.execute("""
                INSERT INTO nuke_tracking (user_id, guild_id, action_type, count, first_action_time)
                VALUES (?, ?, ?, 1, ?)
            """, (user_id, guild_id, action_type, now))
        await self.conn.commit()

    async def get_nuke_count(self, user_id: int, guild_id: int, action_type: str, time_window: int) -> int:
        """Получение количества действий за период"""
        cutoff = datetime.now().timestamp() - time_window
        cursor = await self.conn.execute("""
            SELECT count, first_action_time
            FROM nuke_tracking
            WHERE user_id = ? AND guild_id = ? AND action_type = ? AND first_action_time > ?
        """, (user_id, guild_id, action_type, cutoff))
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def reset_nuke_tracking(self, user_id: int, guild_id: int, action_type: str):
        """Сброс отслеживания нюка"""
        await self.conn.execute("""
            DELETE FROM nuke_tracking
            WHERE user_id = ? AND guild_id = ? AND action_type = ?
        """, (user_id, guild_id, action_type))
        await self.conn.commit()

    # Верификация
    async def mark_verified(self, user_id: int, guild_id: int):
        """Отметка пользователя как верифицированного"""
        await self.conn.execute("""
            INSERT OR REPLACE INTO verified_users (user_id, guild_id, verified_at)
            VALUES (?, ?, ?)
        """, (user_id, guild_id, datetime.now().timestamp()))
        await self.conn.commit()

    async def is_verified(self, user_id: int, guild_id: int) -> bool:
        """Проверка верификации"""
        cursor = await self.conn.execute("""
            SELECT 1 FROM verified_users
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))
        return await cursor.fetchone() is not None

    # Бэкап сервера
    async def save_server_backup(self, guild_id: int, server_name: str, server_icon: Optional[str]):
        """Сохранение бэкапа сервера"""
        await self.conn.execute("""
            INSERT OR REPLACE INTO server_backup (guild_id, server_name, server_icon, updated_at)
            VALUES (?, ?, ?, ?)
        """, (guild_id, server_name, server_icon, datetime.now().timestamp()))
        await self.conn.commit()

    async def get_server_backup(self, guild_id: int) -> Optional[Dict]:
        """Получение бэкапа сервера"""
        cursor = await self.conn.execute("""
            SELECT server_name, server_icon
            FROM server_backup
            WHERE guild_id = ?
        """, (guild_id,))
        row = await cursor.fetchone()
        if row:
            return {
                "name": row[0],
                "icon": row[1]
            }
        return None

    # Whitelist ботов
    async def add_bot_to_whitelist(self, bot_id: int, added_by: int):
        """Добавление бота в whitelist"""
        await self.conn.execute("""
            INSERT OR REPLACE INTO bot_whitelist (bot_id, added_by, added_at)
            VALUES (?, ?, ?)
        """, (bot_id, added_by, datetime.now().timestamp()))
        await self.conn.commit()

    async def is_bot_whitelisted(self, bot_id: int) -> bool:
        """Проверка whitelist"""
        cursor = await self.conn.execute("""
            SELECT 1 FROM bot_whitelist WHERE bot_id = ?
        """, (bot_id,))
        return await cursor.fetchone() is not None

    async def remove_bot_from_whitelist(self, bot_id: int):
        """Удаление бота из whitelist"""
        await self.conn.execute("DELETE FROM bot_whitelist WHERE bot_id = ?", (bot_id,))
        await self.conn.commit()

    # Активность администраторов
    async def update_admin_activity(self, user_id: int, guild_id: int):
        """Обновление активности администратора"""
        await self.conn.execute("""
            INSERT OR REPLACE INTO admin_activity (user_id, guild_id, last_activity)
            VALUES (?, ?, ?)
        """, (user_id, guild_id, datetime.now().timestamp()))
        await self.conn.commit()

    async def get_admin_activity(self, user_id: int, guild_id: int) -> Optional[float]:
        """Получение последней активности"""
        cursor = await self.conn.execute("""
            SELECT last_activity FROM admin_activity
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))
        row = await cursor.fetchone()
        return row[0] if row else None

    # Чёрный список
    async def add_to_blacklist(self, user_id: int, guild_id: int, added_by: int, expires_at: Optional[float], reason: str):
        """Добавление пользователя в чёрный список"""
        await self.conn.execute("""
            INSERT OR REPLACE INTO blacklist (user_id, guild_id, added_by, added_at, expires_at, reason)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, guild_id, added_by, datetime.now().timestamp(), expires_at, reason))
        await self.conn.commit()

    async def is_blacklisted(self, user_id: int, guild_id: int) -> Optional[Dict]:
        """Проверка, находится ли пользователь в чёрном списке"""
        import time
        current_time = time.time()
        cursor = await self.conn.execute("""
            SELECT added_by, added_at, expires_at, reason
            FROM blacklist
            WHERE user_id = ? AND guild_id = ? AND (expires_at IS NULL OR expires_at > ?)
        """, (user_id, guild_id, current_time))
        row = await cursor.fetchone()
        if row:
            return {
                "added_by": row[0],
                "added_at": row[1],
                "expires_at": row[2],
                "reason": row[3]
            }
        return None

    async def remove_from_blacklist(self, user_id: int, guild_id: int):
        """Удаление пользователя из чёрного списка"""
        await self.conn.execute("DELETE FROM blacklist WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
        await self.conn.commit()

    async def get_blacklist_info(self, user_id: int, guild_id: int) -> Optional[Dict]:
        """Получение информации о пользователе в чёрном списке"""
        cursor = await self.conn.execute("""
            SELECT added_by, added_at, expires_at, reason
            FROM blacklist
            WHERE user_id = ? AND guild_id = ?
        """, (user_id, guild_id))
        row = await cursor.fetchone()
        if row:
            return {
                "added_by": row[0],
                "added_at": row[1],
                "expires_at": row[2],
                "reason": row[3]
            }
        return None

