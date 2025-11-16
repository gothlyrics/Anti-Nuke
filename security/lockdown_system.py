import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional

class LockdownSystem:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        self.owner_id = 1329899250758451300
        
        # Состояния блокировки
        self.full_lockdown_active: Dict[int, bool] = {}  # {guild_id: bool}
        self.raid_lockdown_active: Dict[int, bool] = {}  # {guild_id: bool}

    async def enable_full_lockdown(self, guild: discord.Guild):
        """Включение FULL LOCKDOWN MODE"""
        self.full_lockdown_active[guild.id] = True
        
        # Блокировка создания каналов
        try:
            await guild.default_role.edit(permissions=discord.Permissions(
                create_instant_invite=False,
                manage_channels=False,
                manage_roles=False,
                send_messages=False,
                send_messages_in_threads=False,
                create_public_threads=False,
                create_private_threads=False
            ))
        except:
            pass
        
        # Блокировка всех каналов
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.set_permissions(guild.default_role, send_messages=False)
                except:
                    pass
        
        await self.log_lockdown_event(guild, "full_lockdown_enabled", "Полная блокировка сервера активирована")

    async def disable_full_lockdown(self, guild: discord.Guild):
        """Отключение FULL LOCKDOWN MODE"""
        self.full_lockdown_active[guild.id] = False
        
        # Восстановление прав
        try:
            await guild.default_role.edit(permissions=discord.Permissions.all())
        except:
            pass
        
        # Разблокировка всех каналов
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.set_permissions(guild.default_role, send_messages=True)
                except:
                    pass
        
        await self.log_lockdown_event(guild, "full_lockdown_disabled", "Полная блокировка сервера отключена")

    async def enable_raid_lockdown(self, guild: discord.Guild):
        """Включение RAID LOCKDOWN MODE"""
        self.raid_lockdown_active[guild.id] = True
        
        # Блокировка присоединений
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.set_permissions(guild.default_role, send_messages=False)
                except:
                    pass
        
        await self.log_lockdown_event(guild, "raid_lockdown_enabled", "RAID блокировка активирована")

    async def disable_raid_lockdown(self, guild: discord.Guild):
        """Отключение RAID LOCKDOWN MODE"""
        self.raid_lockdown_active[guild.id] = False
        
        # Разблокировка каналов
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                try:
                    await channel.set_permissions(guild.default_role, send_messages=True)
                except:
                    pass
        
        await self.log_lockdown_event(guild, "raid_lockdown_disabled", "RAID блокировка отключена")

    async def check_lockdown(self, guild: discord.Guild) -> bool:
        """Проверка, активна ли блокировка"""
        return self.full_lockdown_active.get(guild.id, False) or self.raid_lockdown_active.get(guild.id, False)

    async def log_lockdown_event(self, guild: discord.Guild, event_type: str, details: str):
        """Логирование событий блокировки"""
        log_channel_id = self.config.get_channel("security_logs")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title=f"**Lockdown** `{event_type}`",
            description=f"↳ **Guild:** `{guild.name}` || **ID:** `{guild.id}` ||\n↳ **Details:** `{details}`",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)



