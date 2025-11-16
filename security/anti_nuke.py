import discord
from discord.ext import commands
from datetime import datetime
import time
from typing import Optional, Dict, List

class AntiNuke:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        self.action_tracking: Dict[int, Dict[str, List[float]]] = {}  # {user_id: {action_type: [timestamps]}}

    async def check_action(self, user: discord.Member, action_type: str) -> bool:
        """Проверка действия на подозрительность. Возвращает True если действие разрешено"""
        if not self.config.is_enabled("security", "anti_nuke"):
            return True

        # Игнорируем владельца сервера и самого бота
        if user.id == user.guild.owner_id or user.id == self.bot.user.id:
            return True

        config = self.config.get_security_config("anti_nuke")
        max_actions = config.get(f"max_{action_type}", 3)
        time_window = config.get("time_window", 10)

        # Отслеживание действия
        await self.db.track_nuke_action(user.id, user.guild.id, action_type)
        count = await self.db.get_nuke_count(user.id, user.guild.id, action_type, time_window)

        if count > max_actions:
            # Подозрительная активность обнаружена
            await self.handle_nuke_attempt(user, action_type, count)
            return False

        return True

    async def handle_nuke_attempt(self, user: discord.Member, action_type: str, count: int):
        """Обработка попытки нюка"""
        try:
            # Бан злоумышленника
            try:
                await user.ban(reason=f"Anti-Nuke: Подозрительная активность ({action_type})")
            except:
                try:
                    await user.kick(reason=f"Anti-Nuke: Подозрительная активность ({action_type})")
                except:
                    pass

            # Логирование
            await self.log_nuke_attempt(user, action_type, count)
        except Exception as e:
            print(f"Ошибка при обработке нюка: {e}")

    async def log_nuke_attempt(self, user: discord.Member, action_type: str, count: int):
        """Логирование попытки нюка"""
        log_channel_id = self.config.get_channel("security_logs")
        if not log_channel_id:
            return

        guild = user.guild
        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        action_names = {
            "channels_delete": "Массовое удаление каналов",
            "roles_create": "Массовое создание ролей",
            "bans": "Массовые баны",
            "kicks": "Массовые кики",
            "permissions": "Изменение прав ролей"
        }

        embed = discord.Embed(
            title="🚨 Обнаружена попытка нюка!",
            description=f"**Пользователь:** {user.mention} (`{user.id}`)\n**Действие:** {action_names.get(action_type, action_type)}\n**Количество:** {count}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)
        embed.add_field(name="Действие", value="Пользователь был забанен", inline=False)

        await log_channel.send(embed=embed)

    async def handle_channel_delete(self, channel: discord.abc.GuildChannel):
        """Обработка удаления канала (для восстановления)"""
        if not self.config.is_enabled("security", "anti_nuke"):
            return

        # Здесь можно добавить логику восстановления канала
        # Для этого нужно сохранять информацию о каналах перед удалением
        pass

    async def handle_role_delete(self, role: discord.Role):
        """Обработка удаления роли (для восстановления)"""
        if not self.config.is_enabled("security", "anti_nuke"):
            return

        # Проверка, не пытаются ли удалить роль бота
        if role.guild.me.top_role <= role:
            # Попытка удалить роль выше или равную роли бота
            await self.log_nuke_attempt(
                role.guild.me,  # В данном случае логируем попытку
                "role_delete_bot",
                1
            )



