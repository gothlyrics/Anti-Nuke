import discord
from discord.ext import commands
from datetime import datetime
from typing import List

class AlarmSystem:
    def __init__(self, bot: commands.Bot, db, config, lockdown_system):
        self.bot = bot
        self.db = db
        self.config = config
        self.lockdown_system = lockdown_system
        self.owner_id = 1329899250758451300

    async def trigger_alarm(self, guild: discord.Guild, alarm_type: str, details: str):
        """Активация Alarm Mode"""
        # Уведомление всех модераторов
        await self.notify_moderators(guild, alarm_type, details)
        
        # Включение полной защиты
        await self.lockdown_system.enable_full_lockdown(guild)
        
        # Закрытие сервера (установка верификации на максимальный уровень)
        try:
            # Здесь можно установить уровень верификации, если есть права
            pass
        except:
            pass
        
        # Логирование
        await self.log_alarm(guild, alarm_type, details)

    async def notify_moderators(self, guild: discord.Guild, alarm_type: str, details: str):
        """Уведомление модераторов"""
        admin_role_id = self.config.get_role("admin")
        moderators = []
        
        if admin_role_id:
            admin_role = guild.get_role(int(admin_role_id))
            if admin_role:
                moderators = [member for member in guild.members if admin_role in member.roles]
        
        # Добавляем администраторов
        for member in guild.members:
            if member.guild_permissions.administrator and member not in moderators:
                moderators.append(member)
        
        embed = discord.Embed(
            title="🚨 **ALARM MODE АКТИВИРОВАН**",
            description=f"**Тип:** `{alarm_type}`\n**Детали:** `{details}`\n**Сервер:** `{guild.name}`",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        for moderator in moderators:
            try:
                await moderator.send(embed=embed)
            except:
                pass

    async def log_alarm(self, guild: discord.Guild, alarm_type: str, details: str):
        """Логирование тревоги"""
        log_channel_id = self.config.get_channel("security_logs")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title="🚨 **ALARM MODE**",
            description=f"↳ **Type:** `{alarm_type}`\n↳ **Guild:** `{guild.name}` || **ID:** `{guild.id}` ||\n↳ **Details:** `{details}`",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)



