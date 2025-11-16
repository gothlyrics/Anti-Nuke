import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional

class GuildEvents(commands.Cog):
    def __init__(self, bot: commands.Bot, db, config, anti_nuke, advanced_protection, anti_permission_elevation):
        self.bot = bot
        self.db = db
        self.config = config
        self.anti_nuke = anti_nuke
        self.advanced_protection = advanced_protection
        self.anti_permission_elevation = anti_permission_elevation

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Обработка создания канала"""
        # Можно добавить логирование
        pass

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Обработка удаления канала"""
        # Проверка на анти-нюк
        if channel.guild.me.guild_permissions.view_audit_log:
            async for entry in channel.guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
                if entry.user and entry.user.id != self.bot.user.id:
                    if not await self.anti_nuke.check_action(entry.user, "channels_delete"):
                        # Попытка восстановления канала
                        await self.anti_nuke.handle_channel_delete(channel)
                    break

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Обработка создания роли"""
        # Проверка на анти-нюк
        if role.guild.me.guild_permissions.view_audit_log:
            async for entry in role.guild.audit_logs(action=discord.AuditLogAction.role_create, limit=1):
                if entry.user and entry.user.id != self.bot.user.id:
                    if not await self.anti_nuke.check_action(entry.user, "roles_create"):
                        # Удаление созданной роли
                        try:
                            await role.delete(reason="Anti-Nuke: Массовое создание ролей")
                        except:
                            pass
                    break

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Обработка удаления роли"""
        # Проверка на попытку удалить роль бота
        if role.guild.me.top_role <= role:
            await self.anti_nuke.handle_role_delete(role)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """Обработка обновления роли"""
        # Проверка на изменение прав роли
        if before.permissions != after.permissions:
            if after.guild.me.guild_permissions.view_audit_log:
                async for entry in after.guild.audit_logs(action=discord.AuditLogAction.role_update, limit=1):
                    if entry.user and entry.user.id != self.bot.user.id:
                        # Проверка Anti-Permission Elevation
                        if not await self.anti_permission_elevation.check_role_update(before, after):
                            return
                        
                        if not await self.anti_nuke.check_action(entry.user, "permissions"):
                            # Восстановление прав
                            try:
                                await after.edit(permissions=before.permissions, reason="Anti-Nuke: Изменение прав роли")
                            except:
                                pass
                        break

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        """Обработка бана пользователя"""
        # Проверка на анти-нюк
        if guild.me.guild_permissions.view_audit_log:
            async for entry in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
                if entry.user and entry.user.id != self.bot.user.id:
                    if not await self.anti_nuke.check_action(entry.user, "bans"):
                        # Разбан пользователя
                        try:
                            await guild.unban(user, reason="Anti-Nuke: Массовые баны")
                        except:
                            pass
                    break

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Обработка удаления участника (кик)"""
        # Проверка на анти-нюк
        if member.guild.me.guild_permissions.view_audit_log:
            async for entry in member.guild.audit_logs(action=discord.AuditLogAction.kick, limit=1):
                if entry.user and entry.user.id != self.bot.user.id:
                    if not await self.anti_nuke.check_action(entry.user, "kicks"):
                        pass
                    break

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        """Обработка обновления сервера"""
        # Защита от изменения названия
        if self.config.is_enabled("security", "server_name_protection"):
            if before.name != after.name:
                # Восстановление названия
                backup = await self.db.get_server_backup(after.id)
                if backup and backup["name"]:
                    try:
                        await after.edit(name=backup["name"], reason="Защита от изменения названия")
                    except:
                        pass
                else:
                    # Сохранение текущего названия
                    await self.db.save_server_backup(after.id, after.name, after.icon.url if after.icon else None)

        # Защита от изменения иконки
        if self.config.is_enabled("security", "server_icon_protection"):
            if before.icon != after.icon:
                # Восстановление иконки
                backup = await self.db.get_server_backup(after.id)
                if backup and backup["icon"]:
                    try:
                        # Здесь нужно загрузить иконку из URL и установить её
                        # Это требует дополнительной логики
                        pass
                    except:
                        pass
                else:
                    # Сохранение текущей иконки
                    await self.db.save_server_backup(after.id, after.name, after.icon.url if after.icon else None)

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.TextChannel):
        """Обработка обновления вебхуков"""
        # Проверка на создание вебхука
        if self.config.is_enabled("security", "anti_webhook"):
            webhooks = await channel.webhooks()
            for webhook in webhooks:
                # Логирование
                await self.advanced_protection.log_webhook_creation(webhook)

