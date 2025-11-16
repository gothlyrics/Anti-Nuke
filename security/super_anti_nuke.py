import discord
from discord.ext import commands
from datetime import datetime
import time
from typing import Dict, List

class SuperAntiNuke:
    def __init__(self, bot: commands.Bot, db, config):
        self.bot = bot
        self.db = db
        self.config = config
        self.owner_id = 1329899250758451300
        
        # Отслеживание действий
        self.thread_deletes: Dict[int, List[float]] = {}  # {user_id: [timestamps]}
        self.channel_edits: Dict[int, List[float]] = {}  # {user_id: [timestamps]}
        self.theme_changes: Dict[int, List[float]] = {}  # {user_id: [timestamps]}

    async def check_thread_delete(self, thread: discord.Thread, user: discord.Member) -> bool:
        """Проверка удаления тредов (thread nuking)"""
        if user.id == self.owner_id or user.id == self.bot.user.id:
            return True
            
        guild_id = thread.guild.id
        user_id = user.id
        now = time.time()
        
        if user_id not in self.thread_deletes:
            self.thread_deletes[user_id] = []
        
        # Очистка старых записей (окно 10 секунд)
        self.thread_deletes[user_id] = [ts for ts in self.thread_deletes[user_id] if now - ts < 10]
        self.thread_deletes[user_id].append(now)
        
        if len(self.thread_deletes[user_id]) >= 3:
            # Thread nuking обнаружен
            await self.handle_thread_nuke(user, thread.guild, len(self.thread_deletes[user_id]))
            return False
        
        return True

    async def check_channel_edit(self, before: discord.TextChannel, after: discord.TextChannel, user: discord.Member) -> bool:
        """Проверка массового редактирования каналов"""
        if user.id == self.owner_id or user.id == self.bot.user.id:
            return True
            
        if before.name == after.name and before.topic == after.topic:
            return True
            
        user_id = user.id
        now = time.time()
        
        if user_id not in self.channel_edits:
            self.channel_edits[user_id] = []
        
        # Очистка старых записей (окно 10 секунд)
        self.channel_edits[user_id] = [ts for ts in self.channel_edits[user_id] if now - ts < 10]
        self.channel_edits[user_id].append(now)
        
        if len(self.channel_edits[user_id]) >= 5:
            # Mass channel edit обнаружен
            await self.handle_mass_edit(user, after.guild, len(self.channel_edits[user_id]))
            return False
        
        return True

    async def check_region_change(self, before: discord.Guild, after: discord.Guild, user: discord.Member) -> bool:
        """Защита от изменения RTC-региона"""
        if user.id == self.owner_id:
            return True
            
        if before.region != after.region:
            # Попытка изменить регион
            try:
                await after.edit(region=before.region, reason="Super Anti-Nuke: Защита от изменения региона")
                await self.log_security_event(after, "region_change_blocked", user, f"Попытка изменить регион с {before.region} на {after.region}")
            except:
                pass
            return False
        
        return True

    async def check_2fa_change(self, guild: discord.Guild, user: discord.Member, enabled: bool):
        """Защита от отключения 2FA у админов"""
        if user.id == self.owner_id:
            return
            
        # Проверка, является ли пользователь администратором
        if user.guild_permissions.administrator:
            if not enabled:
                # 2FA отключено у администратора
                await self.log_security_event(guild, "2fa_disabled", user, "2FA отключено у администратора")
                # Отправка предупреждения владельцу
                owner = guild.get_member(self.owner_id)
                if owner:
                    try:
                        embed = discord.Embed(
                            title="⚠️ КРИТИЧЕСКОЕ ПРЕДУПРЕЖДЕНИЕ",
                            description=f"**2FA отключено у администратора:** {user.mention} (`{user.id}`)\n**Сервер:** {guild.name}",
                            color=discord.Color.red(),
                            timestamp=datetime.utcnow()
                        )
                        await owner.send(embed=embed)
                    except:
                        pass

    async def check_theme_change(self, before: discord.TextChannel, after: discord.TextChannel, user: discord.Member) -> bool:
        """Защита от массовой смены тем каналов"""
        if user.id == self.owner_id or user.id == self.bot.user.id:
            return True
            
        if before.nsfw == after.nsfw:
            return True
            
        user_id = user.id
        now = time.time()
        
        if user_id not in self.theme_changes:
            self.theme_changes[user_id] = []
        
        # Очистка старых записей (окно 10 секунд)
        self.theme_changes[user_id] = [ts for ts in self.theme_changes[user_id] if now - ts < 10]
        self.theme_changes[user_id].append(now)
        
        if len(self.theme_changes[user_id]) >= 3:
            # Mass theme change обнаружен
            await self.handle_mass_theme_change(user, after.guild, len(self.theme_changes[user_id]))
            return False
        
        return True

    async def handle_thread_nuke(self, user: discord.Member, guild: discord.Guild, count: int):
        """Обработка thread nuking"""
        try:
            await user.ban(reason=f"Super Anti-Nuke: Thread nuking ({count} тредов)", delete_message_days=0)
            await self.log_security_event(guild, "thread_nuke", user, f"Удалено {count} тредов")
        except:
            try:
                await user.kick(reason=f"Super Anti-Nuke: Thread nuking ({count} тредов)")
            except:
                pass

    async def handle_mass_edit(self, user: discord.Member, guild: discord.Guild, count: int):
        """Обработка массового редактирования каналов"""
        try:
            await user.ban(reason=f"Super Anti-Nuke: Mass channel edit ({count} каналов)", delete_message_days=0)
            await self.log_security_event(guild, "mass_channel_edit", user, f"Отредактировано {count} каналов")
        except:
            try:
                await user.kick(reason=f"Super Anti-Nuke: Mass channel edit ({count} каналов)")
            except:
                pass

    async def handle_mass_theme_change(self, user: discord.Member, guild: discord.Guild, count: int):
        """Обработка массовой смены тем"""
        try:
            await user.ban(reason=f"Super Anti-Nuke: Mass theme change ({count} каналов)", delete_message_days=0)
            await self.log_security_event(guild, "mass_theme_change", user, f"Изменено тем {count} каналов")
        except:
            try:
                await user.kick(reason=f"Super Anti-Nuke: Mass theme change ({count} каналов)")
            except:
                pass

    async def log_security_event(self, guild: discord.Guild, event_type: str, user: discord.Member, details: str):
        """Логирование событий безопасности"""
        log_channel_id = self.config.get_channel("security_logs")
        if not log_channel_id:
            return

        log_channel = guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title=f"**{user.name}#{user.discriminator}** `{event_type}`",
            description=f"↳ **Member:** `{user.name}#{user.discriminator}` || **ID:** `{user.id}` ||\n↳ **Reason:** `{details}`",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )

        await log_channel.send(embed=embed)



