import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional

class EnhancedGuildEvents(commands.Cog):
    def __init__(self, bot: commands.Bot, db, config, super_anti_nuke, super_anti_webhook, protection_shadows, shadow_logs, server_backup):
        self.bot = bot
        self.db = db
        self.config = config
        self.super_anti_nuke = super_anti_nuke
        self.super_anti_webhook = super_anti_webhook
        self.protection_shadows = protection_shadows
        self.shadow_logs = shadow_logs
        self.server_backup = server_backup

    @commands.Cog.listener()
    async def on_thread_delete(self, thread: discord.Thread):
        """Обработка удаления треда"""
        if thread.guild.me.guild_permissions.view_audit_log:
            async for entry in thread.guild.audit_logs(action=discord.AuditLogAction.thread_delete, limit=1):
                if entry.user and entry.user.id != self.bot.user.id:
                    if not await self.super_anti_nuke.check_thread_delete(thread, entry.user):
                        await self.shadow_logs.send_shadow_log("thread_nuke", thread.guild, f"Удалено тредов: {thread.name}", entry.user)
                    break

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
        """Обработка обновления канала"""
        if isinstance(before, discord.TextChannel) and isinstance(after, discord.TextChannel):
            if before.guild.me.guild_permissions.view_audit_log:
                async for entry in before.guild.audit_logs(action=discord.AuditLogAction.channel_update, limit=1):
                    if entry.user and entry.user.id != self.bot.user.id:
                        # Проверка массового редактирования
                        if not await self.super_anti_nuke.check_channel_edit(before, after, entry.user):
                            await self.shadow_logs.send_shadow_log("mass_channel_edit", before.guild, f"Массовое редактирование каналов", entry.user)
                        
                        # Проверка смены темы
                        if not await self.super_anti_nuke.check_theme_change(before, after, entry.user):
                            await self.shadow_logs.send_shadow_log("mass_theme_change", before.guild, f"Массовая смена тем", entry.user)
                        break

    @commands.Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild):
        """Обработка обновления сервера"""
        if after.me.guild_permissions.view_audit_log:
            async for entry in after.audit_logs(action=discord.AuditLogAction.guild_update, limit=1):
                if entry.user and entry.user.id != self.bot.user.id:
                    # Проверка изменения региона
                    if not await self.super_anti_nuke.check_region_change(before, after, entry.user):
                        await self.shadow_logs.send_shadow_log("region_change", before.guild, f"Попытка изменить регион", entry.user)
                    break

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Обработка обновления участника (для проверки 2FA)"""
        # Проверка изменения 2FA
        if before.guild_permissions.administrator != after.guild_permissions.administrator:
            # Здесь можно добавить проверку 2FA, но Discord API не предоставляет прямой доступ к статусу 2FA
            pass

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.TextChannel):
        """Обработка обновления вебхуков"""
        webhooks = await channel.webhooks()
        for webhook in webhooks:
            await self.super_anti_webhook.check_webhook_creation(webhook)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        """Создание канала - создание тени"""
        if isinstance(channel, discord.TextChannel):
            await self.protection_shadows.create_shadow_channel(channel)
        elif isinstance(channel, discord.CategoryChannel):
            await self.protection_shadows.create_shadow_category(channel)

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Создание роли - создание тени"""
        await self.protection_shadows.create_shadow_role(role)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        """Удаление канала - восстановление из тени"""
        if isinstance(channel, discord.TextChannel):
            restored = await self.protection_shadows.restore_channel(channel.guild, channel.id)
            if restored:
                await self.shadow_logs.send_shadow_log("channel_restored", channel.guild, f"Канал восстановлен: {channel.name}", None)
        
        # Проверка подозрительных изменений и автовосстановление
        await self.server_backup.auto_restore_if_needed(channel.guild)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Удаление роли - восстановление из тени"""
        restored = await self.protection_shadows.restore_role(role.guild, role.id)
        if restored:
            await self.shadow_logs.send_shadow_log("role_restored", role.guild, f"Роль восстановлена: {role.name}", None)
        
        # Проверка подозрительных изменений и автовосстановление
        await self.server_backup.auto_restore_if_needed(role.guild)

