import discord
from discord.ext import commands
from datetime import datetime
import re
from typing import List, Optional, Tuple

class AdvancedProtection:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config

    async def check_message_content(self, message: discord.Message) -> Tuple[bool, Optional[str]]:
        """Проверка содержимого сообщения. Возвращает (разрешено, причина)"""
        if message.author.bot:
            return True, None

        # Anti-Caps
        if self.config.is_enabled("security", "anti_caps"):
            if await self.check_caps(message):
                return False, "Слишком много заглавных букв"

        # Anti-Link
        if self.config.is_enabled("security", "anti_link"):
            if await self.check_links(message):
                return False, "Ссылки запрещены"

        # Blacklist Words
        if self.config.is_enabled("security", "blacklist_words"):
            word = await self.check_blacklist(message)
            if word:
                return False, f"Запрещённое слово: {word}"

        # Anti-Token Grabber
        if self.config.is_enabled("security", "anti_token_grabber"):
            if await self.check_token_grabber(message):
                return False, "Подозрительное содержимое (токен-граббер)"

        # Anti-NSFW
        if self.config.is_enabled("security", "anti_nsfw"):
            if await self.check_nsfw(message):
                return False, "NSFW контент запрещён"

        # Anti-Invite
        if self.config.is_enabled("security", "anti_invite"):
            if await self.check_invites(message):
                return False, "Приглашения запрещены"

        # Anti-Mass Mention
        if self.config.is_enabled("security", "anti_mass_mention"):
            if await self.check_mass_mention(message):
                return False, "Слишком много упоминаний"

        # Disguised URLs
        if await self.check_disguised_urls(message):
            return False, "Маскирующие ссылки запрещены"

        # Anti-Ladder Spam (спам лесенкой)
        if await self.check_ladder_spam(message):
            return False, "Спам лесенкой запрещён"

        # Anti-Ping Spam
        if await self.check_ping_spam(message):
            return False, "Спам пингами запрещён"

        return True, None

    async def check_caps(self, message: discord.Message) -> bool:
        """Проверка на капс"""
        config = self.config.get_security_config("anti_caps")
        max_caps_percent = config.get("max_caps_percent", 70)
        min_length = config.get("min_length", 10)

        content = message.content
        if len(content) < min_length:
            return False

        if not content.replace(" ", ""):
            return False

        caps_count = sum(1 for c in content if c.isupper())
        total_letters = sum(1 for c in content if c.isalpha())
        
        if total_letters == 0:
            return False

        caps_percent = (caps_count / total_letters) * 100
        return caps_percent > max_caps_percent

    async def check_links(self, message: discord.Message) -> bool:
        """Проверка на ссылки"""
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        if url_pattern.search(message.content):
            # Проверка разрешённых ролей
            config = self.config.get_security_config("anti_link")
            allowed_roles = config.get("allowed_roles", [])
            
            if allowed_roles:
                user_roles = [str(role.id) for role in message.author.roles]
                if any(role_id in user_roles for role_id in allowed_roles):
                    return False

            return True
        return False

    async def check_blacklist(self, message: discord.Message) -> Optional[str]:
        """Проверка на слова из чёрного списка"""
        config = self.config.get_security_config("blacklist_words")
        words = config.get("words", [])
        
        content_lower = message.content.lower()
        for word in words:
            if word.lower() in content_lower:
                return word
        return None

    async def check_token_grabber(self, message: discord.Message) -> bool:
        """Проверка на токен-граббер"""
        suspicious_patterns = [
            r'[a-zA-Z0-9_-]{23}\.[a-zA-Z0-9_-]{6}\.[a-zA-Z0-9_-]{27}',  # Discord token pattern
            r'[mM][tT][oO][aA][uU][rR][nN]',  # token grabber keywords
        ]
        
        content = message.content
        for pattern in suspicious_patterns:
            if re.search(pattern, content):
                return True
        return False

    async def check_nsfw(self, message: discord.Message) -> bool:
        """Проверка на NSFW контент"""
        if message.channel.is_nsfw():
            return False

        nsfw_keywords = ['nsfw', 'porn', 'xxx', 'sex']
        content_lower = message.content.lower()
        return any(keyword in content_lower for keyword in nsfw_keywords)

    async def check_invites(self, message: discord.Message) -> bool:
        """Проверка на приглашения"""
        invite_pattern = re.compile(r'(?:https?://)?(?:www\.)?(?:discord\.(?:gg|io|me|li)|discordapp\.com/invite)/[a-zA-Z0-9]+')
        if invite_pattern.search(message.content):
            config = self.config.get_security_config("anti_invite")
            allowed_domains = config.get("allowed_domains", [])
            
            # Здесь можно добавить проверку разрешённых доменов
            return True
        return False

    async def check_mass_mention(self, message: discord.Message) -> bool:
        """Проверка на массовые упоминания"""
        config = self.config.get_security_config("anti_mass_mention")
        max_mentions = config.get("max_mentions", 5)
        
        mention_count = len(message.mentions) + len(message.role_mentions)
        return mention_count > max_mentions

    async def check_disguised_urls(self, message: discord.Message) -> bool:
        """Проверка на маскирующие ссылки"""
        # Проверка на markdown ссылки с подозрительными доменами
        markdown_link_pattern = re.compile(r'\[([^\]]+)\]\((https?://[^\)]+)\)')
        matches = markdown_link_pattern.findall(message.content)
        
        for text, url in matches:
            # Если текст ссылки не совпадает с URL, это может быть маскирующая ссылка
            if text.lower() not in url.lower() and 'discord' not in url.lower():
                return True
        
        return False

    async def check_ghost_ping(self, message: discord.Message) -> bool:
        """Проверка на ghost ping (упоминание с последующим удалением)"""
        if self.config.is_enabled("security", "anti_ghost_ping"):
            # Эта проверка должна выполняться при удалении сообщения
            # Сохраняем информацию о сообщениях с упоминаниями
            if message.mentions or message.role_mentions:
                # Сохраняем в БД для последующей проверки
                pass
        return False

    async def check_webhook(self, webhook: discord.Webhook) -> bool:
        """Проверка вебхука"""
        if self.config.is_enabled("security", "anti_webhook"):
            # Логирование создания вебхука
            await self.log_webhook_creation(webhook)
            return False
        return True

    async def log_webhook_creation(self, webhook: discord.Webhook):
        """Логирование создания вебхука"""
        log_channel_id = self.config.get_channel("security_logs")
        if not log_channel_id:
            return

        guild = webhook.guild
        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title="⚠️ Создан вебхук",
            description=f"**Вебхук:** {webhook.name}\n**Канал:** {webhook.channel.mention if webhook.channel else 'Неизвестно'}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)

    async def check_suspicious_nickname(self, member: discord.Member) -> bool:
        """Проверка подозрительного никнейма"""
        if not self.config.is_enabled("security", "suspicious_nickname"):
            return False

        suspicious_patterns = [
            r'@everyone',
            r'@here',
            r'<@',
            r'<#',
            r'<:',
            r'<a:',
            r'discord\.gg',
            r'http',
        ]

        nickname = member.display_name.lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, nickname):
                return True
        return False

    async def check_fake_account(self, member: discord.Member) -> bool:
        """Проверка на фейковый аккаунт"""
        if not self.config.is_enabled("security", "anti_fake_account"):
            return False

        config = self.config.get_security_config("anti_fake_account")
        min_age_days = config.get("min_account_age_days", 7)

        account_age = (datetime.utcnow() - member.created_at).days
        return account_age < min_age_days

    async def check_ladder_spam(self, message: discord.Message) -> bool:
        """Проверка на спам лесенкой (повторяющиеся символы)"""
        content = message.content
        
        # Проверка на повторяющиеся символы (например: аааа, 1111, !!!!)
        if len(content) >= 5:
            # Проверка на одинаковые символы подряд
            max_repeat = 0
            current_repeat = 1
            for i in range(1, len(content)):
                if content[i] == content[i-1] and content[i] not in [' ', '\n', '\t']:
                    current_repeat += 1
                    max_repeat = max(max_repeat, current_repeat)
                else:
                    current_repeat = 1
            
            if max_repeat >= 5:
                return True
        
        # Проверка на лесенку (постепенное увеличение символов)
        # Например: a, aa, aaa, aaaa
        lines = content.split('\n')
        if len(lines) >= 3:
            lengths = [len(line.strip()) for line in lines if line.strip()]
            if len(lengths) >= 3:
                # Проверка на монотонное увеличение или уменьшение
                increasing = all(lengths[i] < lengths[i+1] for i in range(len(lengths)-1))
                decreasing = all(lengths[i] > lengths[i+1] for i in range(len(lengths)-1))
                if increasing or decreasing:
                    # Проверка на одинаковый символ
                    if all(len(set(line.strip())) <= 2 for line in lines[:3] if line.strip()):
                        return True
        
        return False

    async def check_ping_spam(self, message: discord.Message) -> bool:
        """Проверка на спам пингами"""
        # Подсчёт упоминаний
        mention_count = len(message.mentions) + len(message.role_mentions)
        
        # Если больше 3 упоминаний - это спам
        if mention_count > 3:
            return True
        
        # Проверка на повторяющиеся упоминания одного пользователя
        if message.mentions:
            user_ids = [user.id for user in message.mentions]
            if len(user_ids) != len(set(user_ids)):
                return True
        
        return False

