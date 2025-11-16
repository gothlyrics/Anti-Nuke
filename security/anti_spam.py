import discord
from discord.ext import commands
from datetime import datetime
import time
from typing import Optional

class AntiSpam:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config

    async def check_message(self, message: discord.Message) -> bool:
        """Проверка сообщения на спам. Возвращает True если сообщение разрешено"""
        if not self.config.is_enabled("security", "anti_spam"):
            return True

        if message.author.bot:
            return True

        config = self.config.get_security_config("anti_spam")
        max_messages = config.get("max_messages", 5)
        time_window = config.get("time_window", 5)

        # Отслеживание сообщения
        await self.db.track_message(message.author.id, message.guild.id)
        count = await self.db.get_spam_count(message.author.id, message.guild.id, time_window)

        if count > max_messages:
            # Спам обнаружен
            await self.handle_spam(message.author, message.guild, count)
            try:
                await message.delete()
            except:
                pass
            return False

        return True

    async def handle_spam(self, user: discord.Member, guild: discord.Guild, count: int):
        """Обработка спама"""
        config = self.config.get_security_config("anti_spam")
        mute_duration = config.get("mute_duration", 300)

        # Получение роли мута
        mute_role = discord.utils.get(guild.roles, name="Muted")
        if not mute_role:
            # Создание роли мута если её нет
            mute_role = await guild.create_role(
                name="Muted",
                reason="Автоматическое создание роли мута"
            )
            # Удаление прав у роли мута
            for channel in guild.channels:
                try:
                    await channel.set_permissions(mute_role, send_messages=False, speak=False)
                except:
                    pass

        try:
            await user.add_roles(mute_role, reason=f"Anti-Spam: {count} сообщений за короткое время")
            
            # Сохранение мута в БД
            expires_at = time.time() + mute_duration
            await self.db.add_mute(
                user.id,
                guild.id,
                expires_at,
                f"Anti-Spam: {count} сообщений",
                self.bot.user.id
            )

            # Логирование
            await self.log_spam_action(user, count, mute_duration)
        except Exception as e:
            print(f"Ошибка при муте за спам: {e}")

    async def log_spam_action(self, user: discord.Member, count: int, duration: int):
        """Логирование действия анти-спама"""
        log_channel_id = self.config.get_channel("moderation_logs")
        if not log_channel_id:
            return

        guild = user.guild
        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title="🚫 Обнаружен спам",
            description=f"**Пользователь:** {user.mention} (`{user.id}`)\n**Количество сообщений:** {count}\n**Действие:** Мут на {duration} секунд",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=str(user), icon_url=user.display_avatar.url)

        await log_channel.send(embed=embed)



