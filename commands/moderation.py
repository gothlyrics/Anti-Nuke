import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional

class ModerationCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, db, config, moderator_logs):
        self.bot = bot
        self.db = db
        self.config = config
        self.moderator_logs = moderator_logs

    async def check_permissions(self, interaction: discord.Interaction) -> bool:
        """Проверка прав на использование команд модерации"""
        admin_roles_data = self.config.get("roles", "admin", default=[])
        if isinstance(admin_roles_data, str):
            admin_roles_data = [admin_roles_data]
        elif not isinstance(admin_roles_data, list):
            admin_roles_data = []
        
        # Проверка админ ролей
        for admin_role_id in admin_roles_data:
            try:
                admin_role = interaction.guild.get_role(int(admin_role_id))
                if admin_role and admin_role in interaction.user.roles:
                    return True
            except:
                pass
        
        # Проверка прав администратора
        if interaction.user.guild_permissions.administrator:
            return True
        
        return False

    @app_commands.command(name="mute", description="Заглушить пользователя")
    @app_commands.describe(
        member="Пользователь для мута",
        duration="Длительность в минутах (0 = навсегда)",
        reason="Причина мута"
    )
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: int = 0, reason: Optional[str] = None):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ Вы не можете замутить этого пользователя!", ephemeral=True)
            return

        # Получение или создание роли мута
        mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not mute_role:
            mute_role = await interaction.guild.create_role(
                name="Muted",
                reason="Автоматическое создание роли мута"
            )
            for channel in interaction.guild.channels:
                try:
                    await channel.set_permissions(mute_role, send_messages=False, speak=False)
                except:
                    pass

        expires_at = None
        if duration > 0:
            expires_at = (datetime.utcnow() + timedelta(minutes=duration)).timestamp()

        try:
            await member.add_roles(mute_role, reason=reason or "Мут через команду")
            await self.db.add_mute(member.id, interaction.guild.id, expires_at, reason or "Мут через команду", interaction.user.id)
            
            embed = discord.Embed(
                title=f"**{member.name}#{member.discriminator}** `mute`",
                description=f"↳ **Member:** `{member.name}#{member.discriminator}` || **ID:** `{member.id}` ||\n↳ **Moderator:** `{interaction.user.name}#{interaction.user.discriminator}` || **ID:** `{interaction.user.id}` ||\n↳ **Duration:** `{'Навсегда' if duration == 0 else f'{duration} минут'}`\n↳ **Reason:** `{reason or 'Не указана'}`",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
            await self.log_moderation_action(interaction.guild, "Mute", member, interaction.user, reason)
            await self.moderator_logs.log_moderator_action(interaction.guild, "mute", interaction.user, member, reason)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="unmute", description="Снять мут с пользователя")
    @app_commands.describe(member="Пользователь для снятия мута")
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not mute_role or mute_role not in member.roles:
            await interaction.response.send_message("❌ Пользователь не заглушён!", ephemeral=True)
            return

        try:
            await member.remove_roles(mute_role, reason="Снятие мута через команду")
            await self.db.remove_mute(member.id, interaction.guild.id)
            
            embed = discord.Embed(
                title=f"**{member.name}#{member.discriminator}** `unmute`",
                description=f"↳ **Member:** `{member.name}#{member.discriminator}` || **ID:** `{member.id}` ||\n↳ **Moderator:** `{interaction.user.name}#{interaction.user.discriminator}` || **ID:** `{interaction.user.id}` ||",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
            await self.log_moderation_action(interaction.guild, "Unmute", member, interaction.user, None)
            await self.moderator_logs.log_moderator_action(interaction.guild, "unmute", interaction.user, member)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="kick", description="Исключить пользователя")
    @app_commands.describe(member="Пользователь для кика", reason="Причина кика")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ Вы не можете кикнуть этого пользователя!", ephemeral=True)
            return

        try:
            await member.kick(reason=reason or "Кик через команду")
            embed = discord.Embed(
                title=f"**{member.name}#{member.discriminator}** `kick`",
                description=f"↳ **Member:** `{member.name}#{member.discriminator}` || **ID:** `{member.id}` ||\n↳ **Moderator:** `{interaction.user.name}#{interaction.user.discriminator}` || **ID:** `{interaction.user.id}` ||\n↳ **Reason:** `{reason or 'Не указана'}`",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
            await self.log_moderation_action(interaction.guild, "Kick", member, interaction.user, reason)
            await self.moderator_logs.log_moderator_action(interaction.guild, "kick", interaction.user, member, reason)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="ban", description="Забанить пользователя")
    @app_commands.describe(member="Пользователь для бана", reason="Причина бана", delete_days="Удалить сообщения за последние N дней")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None, delete_days: int = 0):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        if member.top_role >= interaction.user.top_role and interaction.user != interaction.guild.owner:
            await interaction.response.send_message("❌ Вы не можете забанить этого пользователя!", ephemeral=True)
            return

        try:
            await member.ban(reason=reason or "Бан через команду", delete_message_days=delete_days)
            embed = discord.Embed(
                title=f"**{member.name}#{member.discriminator}** `ban`",
                description=f"↳ **Member:** `{member.name}#{member.discriminator}` || **ID:** `{member.id}` ||\n↳ **Moderator:** `{interaction.user.name}#{interaction.user.discriminator}` || **ID:** `{interaction.user.id}` ||\n↳ **Reason:** `{reason or 'Не указана'}`\n↳ **Delete Days:** `{delete_days}`",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
            await self.log_moderation_action(interaction.guild, "Ban", member, interaction.user, reason)
            await self.moderator_logs.log_moderator_action(interaction.guild, "ban", interaction.user, member, reason)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="warn", description="Выдать предупреждение")
    @app_commands.describe(member="Пользователь для предупреждения", reason="Причина предупреждения")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: Optional[str] = None):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        try:
            await self.db.add_warning(member.id, interaction.user.id, reason or "Предупреждение через команду")
            warnings = await self.db.get_warnings(member.id)
            
            # Проверка на автоматический мут
            mod_config = self.config.get_moderation_config("auto_mute")
            if mod_config.get("enabled", True):
                warnings_before_mute = mod_config.get("warnings_before_mute", 3)
                if len(warnings) >= warnings_before_mute:
                    # Автоматический мут
                    mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
                    if mute_role:
                        mute_duration = mod_config.get("mute_duration_base", 300) * (mod_config.get("mute_duration_multiplier", 1.5) ** (len(warnings) - warnings_before_mute))
                        expires_at = (datetime.utcnow() + timedelta(seconds=mute_duration)).timestamp()
                        await member.add_roles(mute_role, reason=f"Автомут после {len(warnings)} предупреждений")
                        await self.db.add_mute(member.id, interaction.guild.id, expires_at, f"Автомут после {len(warnings)} предупреждений", self.bot.user.id)
            
            embed = discord.Embed(
                title=f"**{member.name}#{member.discriminator}** `warn`",
                description=f"↳ **Member:** `{member.name}#{member.discriminator}` || **ID:** `{member.id}` ||\n↳ **Moderator:** `{interaction.user.name}#{interaction.user.discriminator}` || **ID:** `{interaction.user.id}` ||\n↳ **Reason:** `{reason or 'Не указана'}`\n↳ **Total Warnings:** `{len(warnings)}`",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
            await self.log_moderation_action(interaction.guild, "Warn", member, interaction.user, reason)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="unwarn", description="Снять предупреждение")
    @app_commands.describe(member="Пользователь", warning_id="ID предупреждения (оставьте пустым для удаления последнего)")
    async def unwarn(self, interaction: discord.Interaction, member: discord.Member, warning_id: Optional[int] = None):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        try:
            warnings = await self.db.get_warnings(member.id)
            if not warnings:
                await interaction.response.send_message("❌ У пользователя нет предупреждений!", ephemeral=True)
                return

            if warning_id:
                await self.db.remove_warning(warning_id)
            else:
                # Удаление последнего предупреждения
                await self.db.remove_warning(warnings[0]["id"])

            embed = discord.Embed(
                title=f"**{member.name}#{member.discriminator}** `unwarn`",
                description=f"↳ **Member:** `{member.name}#{member.discriminator}` || **ID:** `{member.id}` ||\n↳ **Moderator:** `{interaction.user.name}#{interaction.user.discriminator}` || **ID:** `{interaction.user.id}` ||",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
            await self.log_moderation_action(interaction.guild, "Unwarn", member, interaction.user, None)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="clear", description="Очистить сообщения")
    @app_commands.describe(amount="Количество сообщений для удаления (1-100)")
    async def clear(self, interaction: discord.Interaction, amount: int):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        if amount < 1 or amount > 100:
            await interaction.response.send_message("❌ Количество должно быть от 1 до 100!", ephemeral=True)
            return

        try:
            deleted = await interaction.channel.purge(limit=amount)
            embed = discord.Embed(
                title=f"**{interaction.user.name}#{interaction.user.discriminator}** `clear`",
                description=f"↳ **Deleted:** `{len(deleted)} сообщений`\n↳ **Moderator:** `{interaction.user.name}#{interaction.user.discriminator}` || **ID:** `{interaction.user.id}` ||",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed, delete_after=5)
            await self.log_moderation_action(interaction.guild, "Clear", None, interaction.user, f"{len(deleted)} сообщений")
            await self.moderator_logs.log_moderator_action(interaction.guild, "clear", interaction.user, None, None, f"{len(deleted)} сообщений")
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="slowmode", description="Установить медленный режим")
    @app_commands.describe(seconds="Задержка в секундах (0-21600)")
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        if seconds < 0 or seconds > 21600:
            await interaction.response.send_message("❌ Задержка должна быть от 0 до 21600 секунд!", ephemeral=True)
            return

        try:
            await interaction.channel.edit(slowmode_delay=seconds)
            embed = discord.Embed(
                title=f"**{interaction.user.name}#{interaction.user.discriminator}** `slowmode`",
                description=f"↳ **Channel:** {interaction.channel.mention}\n↳ **Delay:** `{seconds} секунд`\n↳ **Moderator:** `{interaction.user.name}#{interaction.user.discriminator}` || **ID:** `{interaction.user.id}` ||",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
            await self.log_moderation_action(interaction.guild, "Slowmode", None, interaction.user, f"{seconds} секунд")
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="lock", description="Заблокировать канал")
    async def lock(self, interaction: discord.Interaction):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=False)
            embed = discord.Embed(
                title=f"**{interaction.user.name}#{interaction.user.discriminator}** `lock`",
                description=f"↳ **Channel:** {interaction.channel.mention}\n↳ **Moderator:** `{interaction.user.name}#{interaction.user.discriminator}` || **ID:** `{interaction.user.id}` ||",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
            await self.log_moderation_action(interaction.guild, "Lock", None, interaction.user, None)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)

    @app_commands.command(name="unlock", description="Разблокировать канал")
    async def unlock(self, interaction: discord.Interaction):
        if not await self.check_permissions(interaction):
            await interaction.response.send_message("❌ У вас нет прав для использования этой команды!", ephemeral=True)
            return

        try:
            await interaction.channel.set_permissions(interaction.guild.default_role, send_messages=True)
            embed = discord.Embed(
                title=f"**{interaction.user.name}#{interaction.user.discriminator}** `unlock`",
                description=f"↳ **Channel:** {interaction.channel.mention}\n↳ **Moderator:** `{interaction.user.name}#{interaction.user.discriminator}` || **ID:** `{interaction.user.id}` ||",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=embed)
            await self.log_moderation_action(interaction.guild, "Unlock", None, interaction.user, None)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка: {str(e)}", ephemeral=True)

    async def log_moderation_action(self, guild: discord.Guild, action: str, member: Optional[discord.Member], moderator: discord.Member, reason: Optional[str]):
        """Логирование действий модерации"""
        log_channel_id = self.config.get_channel("moderation_logs")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        if member:
            title = f"{member.name}#{member.discriminator} {action.lower()}"
            description = f"↳ Member: {member.name}#{member.discriminator} || ID: {member.id} ||\n↳ Moderator: {moderator.name}#{moderator.discriminator} || ID: {moderator.id} ||"
        else:
            title = f"{moderator.name}#{moderator.discriminator} {action.lower()}"
            description = f"↳ Moderator: {moderator.name}#{moderator.discriminator} || ID: {moderator.id} ||"

        if reason:
            description += f"\n↳ Reason: {reason}"

        embed = discord.Embed(
            title=title,
            description=description,
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)

