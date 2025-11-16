import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional
import re

class BlacklistCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config

    async def check_permissions(self, interaction: discord.Interaction) -> bool:
        """Проверка прав на использование команд"""
        admin_role_id = self.config.get_role("admin")
        if admin_role_id:
            admin_role = interaction.guild.get_role(int(admin_role_id))
            if admin_role and admin_role in interaction.user.roles:
                return True
        
        if interaction.user.guild_permissions.administrator:
            return True
        
        return False

    def parse_duration(self, duration_str: str) -> Optional[int]:
        """Парсинг длительности (например: 1d, 2h, 30m, 7d)"""
        if not duration_str:
            return None
        
        duration_str = duration_str.lower().strip()
        
        # Проверка на "навсегда"
        if duration_str in ['permanent', 'perm', 'forever', 'навсегда']:
            return None
        
        # Регулярное выражение для парсинга
        pattern = r'(\d+)([dhms])'
        match = re.match(pattern, duration_str)
        
        if not match:
            return None
        
        value = int(match.group(1))
        unit = match.group(2)
        
        multipliers = {
            's': 1,
            'm': 60,
            'h': 3600,
            'd': 86400
        }
        
        return value * multipliers.get(unit, 0)

    @app_commands.command(name="blacklistadd", description="Добавить пользователя в чёрный список")
    @app_commands.describe(
        user="Пользователь для добавления в чёрный список",
        duration="Длительность (например: 1d, 2h, 30m, permanent)",
        reason="Причина добавления в чёрный список"
    )
    async def blacklist_add(self, interaction: discord.Interaction, user: discord.Member, duration: Optional[str] = None, reason: Optional[str] = None):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("У вас нет прав для использования этой команды!", ephemeral=True)
            return

        if user.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("Вы не можете добавить этого пользователя в чёрный список!", ephemeral=True)
            return

        # Парсинг длительности
        expires_at = None
        if duration:
            duration_seconds = self.parse_duration(duration)
            if duration_seconds:
                expires_at = (datetime.utcnow() + timedelta(seconds=duration_seconds)).timestamp()
            elif duration.lower() not in ['permanent', 'perm', 'forever', 'навсегда']:
                await interaction.response.send_message("Неверный формат длительности! Используйте: 1d, 2h, 30m или permanent", ephemeral=True)
                return

        try:
            await self.db.add_to_blacklist(
                user.id,
                interaction.guild.id,
                interaction.user.id,
                expires_at,
                reason or "Не указана"
            )

            # Кик/бан пользователя
            try:
                await user.ban(reason=f"Чёрный список: {reason or 'Не указана'}", delete_message_days=0)
            except:
                try:
                    await user.kick(reason=f"Чёрный список: {reason or 'Не указана'}")
                except:
                    pass

            # Логирование
            await self.log_blacklist_action(interaction.guild, "blacklistadd", user, interaction.user, reason, expires_at)

            duration_text = "Навсегда" if not expires_at else f"до {datetime.fromtimestamp(expires_at).strftime('%d.%m.%Y %H:%M')}"
            
            embed = discord.Embed(
                title=f"**{user.name}#{user.discriminator}** `blacklistadd`",
                description=f"↳ **Member:** `{user.name}#{user.discriminator}` || **ID:** `{user.id}` ||\n↳ **Reason:** `{reason or 'Не указана'}`\n↳ **Duration:** `{duration_text}`",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="blacklistcheck", description="Проверить, находится ли пользователь в чёрном списке")
    @app_commands.describe(user="Пользователь для проверки")
    async def blacklist_check(self, interaction: discord.Interaction, user: discord.Member):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("У вас нет прав для использования этой команды!", ephemeral=True)
            return

        blacklist_info = await self.db.is_blacklisted(user.id, interaction.guild.id)
        
        if blacklist_info:
            added_by = interaction.guild.get_member(blacklist_info["added_by"])
            added_by_name = f"{added_by.name}#{added_by.discriminator}" if added_by else f"ID: {blacklist_info['added_by']}"
            
            expires_at = blacklist_info["expires_at"]
            duration_text = "Навсегда" if not expires_at else f"до {datetime.fromtimestamp(expires_at).strftime('%d.%m.%Y %H:%M')}"
            
            embed = discord.Embed(
                title=f"**{user.name}#{user.discriminator}** `blacklistcheck`",
                description=f"↳ **Member:** `{user.name}#{user.discriminator}` || **ID:** `{user.id}` ||\n↳ **Status:** `В чёрном списке`\n↳ **Added by:** `{added_by_name}`\n↳ **Reason:** `{blacklist_info['reason']}`\n↳ **Duration:** `{duration_text}`",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
        else:
            embed = discord.Embed(
                title=f"**{user.name}#{user.discriminator}** `blacklistcheck`",
                description=f"↳ **Member:** `{user.name}#{user.discriminator}` || **ID:** `{user.id}` ||\n↳ **Status:** `Не в чёрном списке`",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="blacklistremove", description="Удалить пользователя из чёрного списка")
    @app_commands.describe(user="Пользователь для удаления из чёрного списка")
    async def blacklist_remove(self, interaction: discord.Interaction, user: discord.Member):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("У вас нет прав для использования этой команды!", ephemeral=True)
            return

        blacklist_info = await self.db.get_blacklist_info(user.id, interaction.guild.id)
        
        if not blacklist_info:
            await interaction.response.send_message("Пользователь не находится в чёрном списке!", ephemeral=True)
            return

        try:
            await self.db.remove_from_blacklist(user.id, interaction.guild.id)
            
            # Логирование
            await self.log_blacklist_action(interaction.guild, "blacklistremove", user, interaction.user, None, None)

            embed = discord.Embed(
                title=f"**{user.name}#{user.discriminator}** `blacklistremove`",
                description=f"↳ **Member:** `{user.name}#{user.discriminator}` || **ID:** `{user.id}` ||\n↳ **Reason:** `Удалён из чёрного списка`",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            await interaction.response.send_message(f"Ошибка: {str(e)}", ephemeral=True)

    async def log_blacklist_action(self, guild: discord.Guild, action: str, member: discord.Member, moderator: discord.Member, reason: Optional[str], expires_at: Optional[float]):
        """Логирование действий с чёрным списком"""
        log_channel_id = self.config.get_channel("blacklist_logs")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        duration_text = "Навсегда" if not expires_at else f"до {datetime.fromtimestamp(expires_at).strftime('%d.%m.%Y %H:%M')}"
        
        embed = discord.Embed(
            title=f"**{member.name}#{member.discriminator}** `{action}`",
            description=f"↳ **Member:** `{member.name}#{member.discriminator}` || **ID:** `{member.id}` ||\n↳ **Moderator:** `{moderator.name}#{moderator.discriminator}` || **ID:** `{moderator.id}` ||" + 
                       (f"\n↳ **Reason:** `{reason}`" if reason else "") +
                       (f"\n↳ **Duration:** `{duration_text}`" if action == "blacklistadd" else ""),
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)

