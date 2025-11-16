import discord
from discord.ext import commands
from datetime import datetime
import time
from typing import Dict, List

class SuperAntiWebhook:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        self.owner_id = 1329899250758451300
        
        # Отслеживание вебхуков
        self.webhook_messages: Dict[int, List[float]] = {}  # {webhook_id: [timestamps]}
        self.suspicious_webhooks: set = set()

    async def check_webhook_creation(self, webhook: discord.Webhook):
        """Проверка создания вебхука"""
        # Автоматическое удаление подозрительных вебхуков
        if await self.is_suspicious_webhook(webhook):
            try:
                await webhook.delete(reason="Super Anti-Webhook: Подозрительный вебхук")
                await self.log_webhook_event(webhook.guild, "webhook_deleted", webhook, "Подозрительный вебхук удалён")
            except:
                pass

    async def check_webhook_message(self, webhook: discord.Webhook):
        """Проверка сообщений от вебхука"""
        webhook_id = webhook.id
        now = time.time()
        
        if webhook_id not in self.webhook_messages:
            self.webhook_messages[webhook_id] = []
        
        # Очистка старых записей (окно 5 секунд)
        self.webhook_messages[webhook_id] = [ts for ts in self.webhook_messages[webhook_id] if now - ts < 5]
        self.webhook_messages[webhook_id].append(now)
        
        # Если вебхук создаёт >10 сообщений за 5 сек → удаление
        if len(self.webhook_messages[webhook_id]) > 10:
            try:
                await webhook.delete(reason="Super Anti-Webhook: Спам вебхука (>10 сообщений за 5 сек)")
                await self.log_webhook_event(webhook.guild, "webhook_spam", webhook, f"{len(self.webhook_messages[webhook_id])} сообщений за 5 секунд")
                del self.webhook_messages[webhook_id]
            except:
                pass

    async def is_suspicious_webhook(self, webhook: discord.Webhook) -> bool:
        """Проверка, является ли вебхук подозрительным"""
        # Проверка имени вебхука на подозрительные паттерны
        suspicious_patterns = [
            'raid', 'nuke', 'spam', 'bot', 'hack', 'crack',
            'discord.gg', 'http', 'www', 'free', 'nitro'
        ]
        
        webhook_name_lower = webhook.name.lower()
        for pattern in suspicious_patterns:
            if pattern in webhook_name_lower:
                return True
        
        return False

    async def log_webhook_event(self, guild: discord.Guild, event_type: str, webhook: discord.Webhook, details: str):
        """Логирование событий вебхуков"""
        log_channel_id = self.config.get_channel("security_logs")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title=f"**Webhook** `{event_type}`",
            description=f"↳ **Webhook:** `{webhook.name}` || **ID:** `{webhook.id}` ||\n↳ **Channel:** {webhook.channel.mention if webhook.channel else 'Неизвестно'}\n↳ **Reason:** `{details}`",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)



