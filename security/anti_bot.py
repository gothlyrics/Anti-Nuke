import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional

class AntiBot:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config

    async def check_bot_join(self, member: discord.Member) -> bool:
        """Проверка бота при присоединении. Возвращает True если бот разрешён"""
        if not self.config.is_enabled("security", "anti_bot"):
            return True

        if not member.bot:
            return True

        bot_id = member.id
        is_whitelisted = await self.db.is_bot_whitelisted(bot_id)

        if not is_whitelisted:
            # Логирование попытки
            await self.log_bot_attempt(member, "Неавторизованный бот попытался присоединиться")
            
            # Кик/бан
            try:
                await member.ban(reason="Неавторизованный бот (Anti-Bot система)")
            except:
                try:
                    await member.kick(reason="Неавторизованный бот (Anti-Bot система)")
                except:
                    pass

            return False

        return True

    async def log_bot_attempt(self, member: discord.Member, reason: str):
        """Логирование попытки добавления бота"""
        log_channel_id = self.config.get_channel("security_logs")
        if not log_channel_id:
            return

        guild = member.guild
        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title="🚫 Блокировка бота",
            description=f"**Пользователь:** {member.mention} (`{member.id}`)\n**Причина:** {reason}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.add_field(name="Действие", value="Бот был забанен/кикнут", inline=False)

        await log_channel.send(embed=embed)

    async def add_to_whitelist(self, bot_id: int, added_by: int):
        """Добавление бота в whitelist"""
        await self.db.add_bot_to_whitelist(bot_id, added_by)



