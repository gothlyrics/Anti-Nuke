import discord
from discord.ext import commands
from datetime import datetime
import json
import asyncio
from typing import Dict, List, Optional

class ServerBackupManager:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        self.backup_interval = 30  # Минуты между бэкапами
        self.last_backup: Dict[int, float] = {}  # {guild_id: timestamp}

    async def start_backup_task(self):
        """Запуск фоновой задачи бэкапов"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                for guild in self.bot.guilds:
                    await self.create_backup(guild)
                await asyncio.sleep(self.backup_interval * 60)  # Конвертируем минуты в секунды
            except Exception as e:
                print(f"Ошибка при создании бэкапа: {e}")
                await asyncio.sleep(60)

    async def create_backup(self, guild: discord.Guild):
        """Создание бэкапа сервера"""
        try:
            backup_data = {
                "guild_id": guild.id,
                "guild_name": guild.name,
                "timestamp": datetime.utcnow().timestamp(),
                "roles": [],
                "channels": [],
                "categories": []
            }

            # Бэкап ролей
            for role in guild.roles:
                if role.name == "@everyone":
                    continue
                role_data = {
                    "id": role.id,
                    "name": role.name,
                    "color": role.color.value,
                    "hoist": role.hoist,
                    "mentionable": role.mentionable,
                    "position": role.position,
                    "permissions": role.permissions.value
                }
                backup_data["roles"].append(role_data)

            # Бэкап категорий
            for category in guild.categories:
                category_data = {
                    "id": category.id,
                    "name": category.name,
                    "position": category.position,
                    "permissions": {}
                }
                for target, overwrite in category.overwrites.items():
                    category_data["permissions"][str(target.id)] = {
                        "allow": overwrite.pair()[0].value,
                        "deny": overwrite.pair()[1].value
                    }
                backup_data["categories"].append(category_data)

            # Бэкап каналов
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    channel_data = {
                        "id": channel.id,
                        "name": channel.name,
                        "topic": channel.topic,
                        "position": channel.position,
                        "nsfw": channel.nsfw,
                        "slowmode_delay": channel.slowmode_delay,
                        "category_id": channel.category_id,
                        "permissions": {}
                    }
                    for target, overwrite in channel.overwrites.items():
                        channel_data["permissions"][str(target.id)] = {
                            "allow": overwrite.pair()[0].value,
                            "deny": overwrite.pair()[1].value
                        }
                    backup_data["channels"].append(channel_data)

            # Сохранение в БД
            await self.save_backup_to_db(guild.id, backup_data)
            self.last_backup[guild.id] = datetime.utcnow().timestamp()

        except Exception as e:
            print(f"Ошибка при создании бэкапа для {guild.name}: {e}")

    async def save_backup_to_db(self, guild_id: int, backup_data: Dict):
        """Сохранение бэкапа в БД"""
        try:
            backup_json = json.dumps(backup_data)
            await self.db.conn.execute("""
                INSERT OR REPLACE INTO server_backups (guild_id, backup_data, created_at)
                VALUES (?, ?, ?)
            """, (guild_id, backup_json, datetime.utcnow().timestamp()))
            await self.db.conn.commit()
        except Exception as e:
            print(f"Ошибка сохранения бэкапа в БД: {e}")

    async def get_latest_backup(self, guild_id: int) -> Optional[Dict]:
        """Получение последнего бэкапа"""
        try:
            cursor = await self.db.conn.execute("""
                SELECT backup_data FROM server_backups
                WHERE guild_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (guild_id,))
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
        except Exception as e:
            print(f"Ошибка получения бэкапа: {e}")
            return None

    async def restore_from_backup(self, guild: discord.Guild) -> bool:
        """Восстановление сервера из бэкапа"""
        try:
            backup_data = await self.get_latest_backup(guild.id)
            if not backup_data:
                return False

            # Восстановление ролей
            existing_roles = {role.id: role for role in guild.roles}
            for role_data in backup_data.get("roles", []):
                if role_data["id"] not in existing_roles:
                    # Создание роли
                    try:
                        new_role = await guild.create_role(
                            name=role_data["name"],
                            color=discord.Color(role_data["color"]),
                            hoist=role_data["hoist"],
                            mentionable=role_data["mentionable"],
                            permissions=discord.Permissions(role_data["permissions"]),
                            reason="Server Backup: Восстановление роли"
                        )
                        # Восстановление позиции
                        try:
                            await new_role.edit(position=role_data["position"])
                        except:
                            pass
                    except:
                        pass

            # Восстановление категорий
            existing_categories = {cat.id: cat for cat in guild.categories}
            for category_data in backup_data.get("categories", []):
                if category_data["id"] not in existing_categories:
                    try:
                        new_category = await guild.create_category(
                            name=category_data["name"],
                            reason="Server Backup: Восстановление категории"
                        )
                        # Восстановление permissions
                        for target_id_str, perm_data in category_data.get("permissions", {}).items():
                            try:
                                target_id = int(target_id_str)
                                target = guild.get_member(target_id) or guild.get_role(target_id)
                                if target:
                                    overwrite = discord.PermissionOverwrite.from_pair(
                                        discord.Permissions(perm_data["allow"]),
                                        discord.Permissions(perm_data["deny"])
                                    )
                                    await new_category.set_permissions(target, overwrite=overwrite)
                            except:
                                pass
                    except:
                        pass

            # Восстановление каналов
            existing_channels = {ch.id: ch for ch in guild.channels}
            for channel_data in backup_data.get("channels", []):
                if channel_data["id"] not in existing_channels:
                    try:
                        category = None
                        if channel_data.get("category_id"):
                            category = guild.get_channel(channel_data["category_id"])
                        
                        new_channel = await guild.create_text_channel(
                            name=channel_data["name"],
                            topic=channel_data.get("topic"),
                            nsfw=channel_data.get("nsfw", False),
                            slowmode_delay=channel_data.get("slowmode_delay", 0),
                            category=category,
                            reason="Server Backup: Восстановление канала"
                        )
                        
                        # Восстановление permissions
                        for target_id_str, perm_data in channel_data.get("permissions", {}).items():
                            try:
                                target_id = int(target_id_str)
                                target = guild.get_member(target_id) or guild.get_role(target_id)
                                if target:
                                    overwrite = discord.PermissionOverwrite.from_pair(
                                        discord.Permissions(perm_data["allow"]),
                                        discord.Permissions(perm_data["deny"])
                                    )
                                    await new_channel.set_permissions(target, overwrite=overwrite)
                            except:
                                pass
                    except:
                        pass

            return True
        except Exception as e:
            print(f"Ошибка восстановления из бэкапа: {e}")
            return False

    async def check_suspicious_changes(self, guild: discord.Guild) -> bool:
        """Проверка подозрительных изменений"""
        # Получение последнего бэкапа
        backup_data = await self.get_latest_backup(guild.id)
        if not backup_data:
            return False
        
        # Проверка количества каналов
        backup_channels_count = len(backup_data.get("channels", []))
        current_channels_count = len([ch for ch in guild.channels if isinstance(ch, discord.TextChannel)])
        
        # Если удалено более 30% каналов - подозрительно
        if backup_channels_count > 0 and current_channels_count < backup_channels_count * 0.7:
            return True
        
        # Проверка количества ролей
        backup_roles_count = len(backup_data.get("roles", []))
        current_roles_count = len([r for r in guild.roles if r.name != "@everyone"])
        
        # Если удалено более 30% ролей - подозрительно
        if backup_roles_count > 0 and current_roles_count < backup_roles_count * 0.7:
            return True
        
        return False

    async def auto_restore_if_needed(self, guild: discord.Guild):
        """Автоматическое восстановление при подозрительных изменениях"""
        if await self.check_suspicious_changes(guild):
            # Автоматическое восстановление
            await self.restore_from_backup(guild)

