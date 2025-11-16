import discord
from discord.ext import commands
from datetime import datetime
import time
from typing import Dict, List

class AntiRaid:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        self.join_tracking: Dict[int, List[float]] = {}  # {guild_id: [timestamps]}

    async def check_join(self, member: discord.Member) -> bool:
        """Проверка присоединения на RAID. Возвращает True если присоединение разрешено"""
        if not self.config.is_enabled("security", "anti_raid"):
            return True

        if member.bot:
            return True

        guild_id = member.guild.id
        config = self.config.get_security_config("anti_raid")
        max_joins = config.get("max_joins", 5)
        time_window = config.get("time_window", 10)

        # Отслеживание присоединения
        now = time.time()
        if guild_id not in self.join_tracking:
            self.join_tracking[guild_id] = []

        # Очистка старых записей
        self.join_tracking[guild_id] = [
            ts for ts in self.join_tracking[guild_id]
            if now - ts < time_window
        ]

        # Добавление нового присоединения
        self.join_tracking[guild_id].append(now)

        # Проверка на RAID
        if len(self.join_tracking[guild_id]) > max_joins:
            # RAID обнаружен
            await self.handle_raid(member.guild, len(self.join_tracking[guild_id]))
            return False

        return True

    async def handle_raid(self, guild: discord.Guild, join_count: int):
        """Обработка RAID"""
        config = self.config.get_security_config("anti_raid")
        lockdown_duration = config.get("lockdown_duration", 300)

        # Логирование
        await self.log_raid(guild, join_count)

        # Временное закрытие сервера (установка верификации)
        try:
            # Здесь можно установить уровень верификации сервера
            # Но это требует специальных прав
            pass
        except:
            pass

        # Блокировка всех каналов
        try:
            for channel in guild.channels:
                if isinstance(channel, discord.TextChannel):
                    try:
                        await channel.set_permissions(
                            guild.default_role,
                            send_messages=False,
                            reason="Anti-Raid: Временная блокировка"
                        )
                    except:
                        pass
        except:
            pass

    async def log_raid(self, guild: discord.Guild, join_count: int):
        """Логирование RAID"""
        log_channel_id = self.config.get_channel("security_logs")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title="🚨 Обнаружен RAID!",
            description=f"**Сервер:** {guild.name}\n**Количество присоединений:** {join_count}\n**Действие:** Временная блокировка сервера",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)



