import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional

class MessageEvents(commands.Cog):
    def __init__(self, bot: commands.Bot, db, config, anti_spam, advanced_protection, moderator_logs):
        self.bot = bot
        self.db = db
        self.config = config
        self.anti_spam = anti_spam
        self.advanced_protection = advanced_protection
        self.moderator_logs = moderator_logs

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Обработка сообщений"""
        if message.author.bot:
            return

        if not message.guild:
            return

        # Проверка на чёрный список
        blacklist_info = await self.db.is_blacklisted(message.author.id, message.guild.id)
        if blacklist_info:
            try:
                await message.delete()
                await message.author.ban(reason=f"Чёрный список: {blacklist_info['reason']}", delete_message_days=0)
            except:
                try:
                    await message.author.kick(reason=f"Чёрный список: {blacklist_info['reason']}")
                except:
                    pass
            return

        # Проверка на спам
        if not await self.anti_spam.check_message(message):
            return

        # Проверка содержимого сообщения
        allowed, reason = await self.advanced_protection.check_message_content(message)
        if not allowed:
            try:
                await message.delete()
                
                # Действие в зависимости от типа нарушения
                config = self.config.get_security_config("blacklist_words")
                if reason and "Запрещённое слово" in reason:
                    action = config.get("action", "mute")
                    duration = config.get("duration", 600)
                    
                    if action == "mute":
                        mute_role = discord.utils.get(message.guild.roles, name="Muted")
                        if mute_role:
                            try:
                                await message.author.add_roles(mute_role, reason=reason)
                                import time
                                expires_at = time.time() + duration
                                await self.db.add_mute(
                                    message.author.id,
                                    message.guild.id,
                                    expires_at,
                                    reason,
                                    self.bot.user.id
                                )
                            except:
                                pass

                # Отправка предупреждения пользователю
                try:
                    embed = discord.Embed(
                        title="⚠️ Сообщение удалено",
                        description=f"Ваше сообщение было удалено.\n**Причина:** {reason}",
                        color=discord.Color.red()
                    )
                    await message.author.send(embed=embed)
                except:
                    pass

                # Логирование
                await self.log_message_violation(message, reason)
            except:
                pass

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """Обработка удаления сообщения"""
        # Проверка на ghost ping
        if self.config.is_enabled("security", "anti_ghost_ping"):
            if message.mentions or message.role_mentions:
                # Логирование ghost ping
                await self.log_ghost_ping(message)
        
        # Логирование удаления сообщения модератором
        if message.guild and message.guild.me.guild_permissions.view_audit_log:
            try:
                async for entry in message.guild.audit_logs(action=discord.AuditLogAction.message_delete, limit=1):
                    if entry.user and entry.user.id != self.bot.user.id and entry.user.id != message.author.id:
                        # Модератор удалил сообщение
                        await self.moderator_logs.log_moderator_action(
                            message.guild,
                            "delete",
                            entry.user,
                            message.author,
                            None,
                            f"Сообщение: {message.content[:100] if message.content else 'Нет текста'}"
                        )
                        break
            except:
                pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """Обработка редактирования сообщения"""
        if before.content == after.content:
            return

        # Повторная проверка содержимого
        allowed, reason = await self.advanced_protection.check_message_content(after)
        if not allowed:
            try:
                await after.delete()
                await self.log_message_violation(after, reason)
            except:
                pass

    async def log_message_violation(self, message: discord.Message, reason: str):
        """Логирование нарушения в сообщении"""
        log_channel_id = self.config.get_channel("moderation_logs")
        if not log_channel_id:
            return

        log_channel = message.guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        action_name = "message_deleted"
        if "ссылки" in reason.lower() or "link" in reason.lower():
            action_name = "link_detected"
        elif "лесенкой" in reason.lower() or "ladder" in reason.lower():
            action_name = "ladder_spam"
        elif "пингами" in reason.lower() or "ping" in reason.lower():
            action_name = "ping_spam"
        elif "капс" in reason.lower() or "caps" in reason.lower():
            action_name = "caps_detected"

        embed = discord.Embed(
            title=f"{message.author.name}#{message.author.discriminator} {action_name}",
            description=f"↳ Member: {message.author.name}#{message.author.discriminator} || ID: {message.author.id} ||\n↳ Reason: {reason}\n↳ Channel: {message.channel.mention}\n↳ Message: {message.content[:200]}",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)

    async def log_ghost_ping(self, message: discord.Message):
        """Логирование ghost ping"""
        log_channel_id = self.config.get_channel("moderation_logs")
        if not log_channel_id:
            return

        log_channel = message.guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        mentions = [f"{m.name}#{m.discriminator}" for m in message.mentions]
        role_mentions = [r.name for r in message.role_mentions]

        embed = discord.Embed(
            title=f"{message.author.name}#{message.author.discriminator} ghost_ping",
            description=f"↳ Member: {message.author.name}#{message.author.discriminator} || ID: {message.author.id} ||\n↳ Reason: Ghost ping обнаружен\n↳ Channel: {message.channel.mention}\n↳ Mentions: {', '.join(mentions + role_mentions) if mentions or role_mentions else 'Нет'}",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)

