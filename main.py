import discord
from discord.ext import commands
import asyncio
import sys
from datetime import datetime

from config import Config
from database import Database
from security import VerificationSystem, AntiBot, AntiNuke, AntiSpam, AntiRaid
from security.advanced_protection import AdvancedProtection
from security.super_anti_nuke import SuperAntiNuke
from security.super_anti_webhook import SuperAntiWebhook
from security.lockdown_system import LockdownSystem
from security.trust_system import TrustSystem
from security.protection_shadows import ProtectionShadows
from security.alarm_system import AlarmSystem
from security.shadow_logs import ShadowLogs
from security.moderator_logs import ModeratorLogs
from security.server_backup import ServerBackupManager
from security.owner_lock import OwnerLock
from security.anti_permission_elevation import AntiPermissionElevation
from commands.moderation import ModerationCommands
from commands.blacklist import BlacklistCommands
from commands.help import HelpCommands
from commands.utility import UtilityCommands
from commands.audit import AuditCommands
from commands.logtest import LogTestCommands
from commands.owner_commands import OwnerCommands
from commands.security_dashboard import SecurityDashboard
from events.member_events import MemberEvents
from events.guild_events import GuildEvents
from events.message_events import MessageEvents
from events.enhanced_guild_events import EnhancedGuildEvents

class SecurityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.guild_messages = True
        intents.guild_reactions = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.config = Config()
        self.db = Database()
        
        # Инициализация систем безопасности
        self.verification_system = None
        self.anti_bot = None
        self.anti_nuke = None
        self.anti_spam = None
        self.anti_raid = None
        self.advanced_protection = None
        self.super_anti_nuke = None
        self.super_anti_webhook = None
        self.lockdown_system = None
        self.trust_system = None
        self.protection_shadows = None
        self.alarm_system = None
        self.shadow_logs = None
        self.moderator_logs = None
        self.server_backup = None
        self.owner_lock = None
        self.anti_permission_elevation = None
        self.owner_commands = None  # Для доступа к protection_enabled

    async def setup_hook(self):
        """Настройка бота при запуске"""
        # Подключение к БД
        await self.db.connect()
        
        # Инициализация систем безопасности
        self.verification_system = VerificationSystem(self, self.db, self.config)
        self.anti_bot = AntiBot(self, self.db, self.config)
        self.anti_nuke = AntiNuke(self, self.db, self.config)
        self.anti_spam = AntiSpam(self, self.db, self.config)
        self.anti_raid = AntiRaid(self, self.db, self.config)
        self.advanced_protection = AdvancedProtection(self, self.db, self.config)
        self.super_anti_nuke = SuperAntiNuke(self, self.db, self.config)
        self.super_anti_webhook = SuperAntiWebhook(self, self.db, self.config)
        self.lockdown_system = LockdownSystem(self, self.db, self.config)
        self.trust_system = TrustSystem(self, self.db, self.config)
        self.protection_shadows = ProtectionShadows(self, self.db, self.config)
        self.shadow_logs = ShadowLogs(self, self.config)
        self.moderator_logs = ModeratorLogs(self, self.config)
        self.server_backup = ServerBackupManager(self, self.db, self.config)
        self.owner_lock = OwnerLock(self, self.db, self.config)
        self.alarm_system = AlarmSystem(self, self.db, self.config, self.lockdown_system)
        self.anti_permission_elevation = AntiPermissionElevation(self, self.db, self.config, self.moderator_logs)
        
        # Загрузка когов
        await self.load_cogs()
        
        # Мгновенная синхронизация команд с конкретным сервером
        await self.sync_commands()
        
        # Запуск фоновых задач
        self.loop.create_task(self.check_mutes_task())
        self.loop.create_task(self.server_backup.start_backup_task())
    
    async def sync_commands(self):
        """Мгновенная синхронизация команд с конкретным сервером"""
        try:
            server_sync_id = self.config.get("bot", "serversynh", default=None)
            
            if server_sync_id:
                # Синхронизация с конкретным сервером
                guild = discord.Object(id=int(server_sync_id))
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"Синхронизировано {len(synced)} команд с сервером {server_sync_id}")
            else:
                # Глобальная синхронизация (может занять до часа)
                synced = await self.tree.sync()
                print(f"Синхронизировано {len(synced)} команд глобально.")
        except Exception as e:
            print(f"Ошибка синхронизации команд: {e}")
            # Попытка глобальной синхронизации в случае ошибки
            try:
                synced = await self.tree.sync()
                print(f"Глобальная синхронизация: {len(synced)} команд.")
            except Exception as e2:
                print(f"Ошибка глобальной синхронизации: {e2}")

    async def load_cogs(self):
        """Загрузка всех когов"""
        # Команды модерации
        await self.add_cog(ModerationCommands(self, self.db, self.config, self.moderator_logs))
        
        # Команды чёрного списка
        await self.add_cog(BlacklistCommands(self, self.db, self.config))
        
        # Команда помощи
        await self.add_cog(HelpCommands(self, self.config))
        
        # Утилитарные команды
        await self.add_cog(UtilityCommands(self, self.config))
        
        # Команды аудита
        await self.add_cog(AuditCommands(self, self.config))
        
        # Команды тестирования логов
        await self.add_cog(LogTestCommands(self, self.config))
        
        # Команды владельца
        owner_cog = OwnerCommands(self, self.db, self.config, self.protection_shadows, self.lockdown_system, self.server_backup, self.owner_lock)
        await self.add_cog(owner_cog)
        self.owner_commands = owner_cog  # Сохранение ссылки для доступа к protection_enabled
        
        # Security Dashboard
        await self.add_cog(SecurityDashboard(self, self.db, self.config, self.trust_system))
        
        # События
        await self.add_cog(MemberEvents(
            self, self.db, self.config,
            self.verification_system, self.anti_bot, self.anti_raid, self.advanced_protection,
            self.alarm_system, self.shadow_logs, self.anti_permission_elevation
        ))
        await self.add_cog(GuildEvents(
            self, self.db, self.config,
            self.anti_nuke, self.advanced_protection, self.anti_permission_elevation
        ))
        await self.add_cog(EnhancedGuildEvents(
            self, self.db, self.config,
            self.super_anti_nuke, self.super_anti_webhook, self.protection_shadows, self.shadow_logs, self.server_backup
        ))
        await self.add_cog(MessageEvents(
            self, self.db, self.config,
            self.anti_spam, self.advanced_protection, self.moderator_logs
        ))

    async def on_ready(self):
        """Событие готовности бота"""
        print(f"{self.user} готов к работе!")
        print(f"Бот подключён к {len(self.guilds)} серверам")
        
        # Повторная синхронизация команд при готовности (на случай если сервер ещё не был доступен)
        await self.sync_commands()
        
        # Установка статуса бота из конфига
        await self.update_bot_status()
        
        # Отправка эмбеда верификации во все каналы верификации
        verification_channel_id = self.config.get_channel("verification")
        if verification_channel_id:
            for guild in self.guilds:
                channel = guild.get_channel(int(verification_channel_id))
                if channel:
                    # Проверка, есть ли уже сообщение верификации
                    async for message in channel.history(limit=10):
                        if message.author == self.user and message.embeds:
                            break
                    else:
                        # Отправка эмбеда верификации
                        await self.verification_system.send_verification_embed(channel)
        
        # Сохранение бэкапа серверов
        for guild in self.guilds:
            await self.db.save_server_backup(
                guild.id,
                guild.name,
                guild.icon.url if guild.icon else None
            )

    async def on_message(self, message: discord.Message):
        """Обработка сообщений"""
        # Обработка команд
        if message.content.startswith(self.config.get_prefix()):
            # Команда !addl для добавления бота в whitelist
            if message.content.startswith(f"{self.config.get_prefix()}addl"):
                await self.handle_addl_command(message)
                return
            
            # Команда !logs для вывода эмбеда
            if message.content.startswith(f"{self.config.get_prefix()}logs"):
                await self.handle_logs_command(message)
                return
            
            # Команда !vfy для отправки эмбеда верификации
            if message.content.startswith(f"{self.config.get_prefix()}vfy"):
                await self.handle_vfy_command(message)
                return

        await self.process_commands(message)

    async def handle_addl_command(self, message: discord.Message):
        """Обработка команды !addl"""
        # Проверка прав
        admin_role_id = self.config.get_role("admin")
        has_permission = False
        
        if admin_role_id:
            admin_role = message.guild.get_role(int(admin_role_id))
            if admin_role and admin_role in message.author.roles:
                has_permission = True
        
        if not has_permission and not message.author.guild_permissions.administrator:
            await message.channel.send("❌ У вас нет прав для использования этой команды!")
            return

        # Парсинг ID
        parts = message.content.split()
        if len(parts) < 2:
            await message.channel.send("❌ Использование: `!addl <bot_id>`")
            return

        try:
            bot_id = int(parts[1])
            await self.anti_bot.add_to_whitelist(bot_id, message.author.id)
            
            embed = discord.Embed(
                title="✅ Бот добавлен в whitelist",
                description=f"**ID бота:** {bot_id}\n**Добавил:** {message.author.mention}",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            await message.delete()
            await message.channel.send(embed=embed)
        except ValueError:
            await message.channel.send("❌ Неверный ID бота!")
        except Exception as e:
            await message.channel.send(f"❌ Ошибка: {str(e)}")

    async def handle_vfy_command(self, message: discord.Message):
        """Обработка команды !vfy - отправка эмбеда верификации"""
        # Проверка прав
        admin_role_id = self.config.get_role("admin")
        has_permission = False
        
        if admin_role_id:
            if isinstance(admin_role_id, list):
                for role_id in admin_role_id:
                    admin_role = message.guild.get_role(int(role_id))
                    if admin_role and admin_role in message.author.roles:
                        has_permission = True
                        break
            else:
                admin_role = message.guild.get_role(int(admin_role_id))
                if admin_role and admin_role in message.author.roles:
                    has_permission = True
        
        if not has_permission and not message.author.guild_permissions.administrator:
            await message.channel.send("**Доступ запрещён.** У вас нет прав для использования этой команды.")
            return
        
        # Отправка эмбеда верификации
        if self.verification_system:
            await self.verification_system.send_verification_embed(message.channel)
            await message.delete()
        else:
            await message.channel.send("❌ Система верификации не инициализирована!")

    async def handle_logs_command(self, message: discord.Message):
        """Обработка команды !logs - вывод эмбеда"""
        embed = discord.Embed(
            title="📊 Система логирования",
            description="Бот ведёт логирование всех важных событий на сервере.",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="📝 Каналы логов",
            value=f"**Верификация:** <#{self.config.get_channel('verification')}>\n"
                  f"**Присоединения:** <#{self.config.get_channel('join_logs')}>\n"
                  f"**Безопасность:** <#{self.config.get_channel('security_logs')}>\n"
                  f"**Модерация:** <#{self.config.get_channel('moderation_logs')}>",
            inline=False
        )
        
        embed.add_field(
            name="🛡️ Активные системы защиты",
            value=f"**Anti-Bot:** {'✅' if self.config.is_enabled('security', 'anti_bot') else '❌'}\n"
                  f"**Anti-Nuke:** {'✅' if self.config.is_enabled('security', 'anti_nuke') else '❌'}\n"
                  f"**Anti-Spam:** {'✅' if self.config.is_enabled('security', 'anti_spam') else '❌'}\n"
                  f"**Anti-Raid:** {'✅' if self.config.is_enabled('security', 'anti_raid') else '❌'}\n"
                  f"**Верификация:** {'✅' if self.config.is_enabled('verification') else '❌'}",
            inline=False
        )
        
        embed.set_footer(text=f"Запросил: {message.author}", icon_url=message.author.display_avatar.url)
        
        await message.channel.send(embed=embed)

    async def close(self):
        """Закрытие бота"""
        await self.db.close()
        await super().close()

    async def update_bot_status(self):
        """Обновление статуса бота из конфига"""
        # Discord статус (online, idle, dnd, invisible, offline)
        discord_status_str = self.config.get("bot", "status", default="online")
        # Тип активности (stream, playing, listening, watching, competing)
        activity_type = self.config.get("bot", "activity_type", default="playing")
        activity_text = self.config.get("bot", "activity", default="Защита сервера")
        stream_url = self.config.get("bot", "stream_url", default=None)
        
        # Определение типа активности
        activity = None
        if activity_type == "stream" and stream_url:
            activity = discord.Streaming(name=activity_text, url=stream_url)
        elif activity_type == "playing":
            activity = discord.Game(name=activity_text)
        elif activity_type == "listening":
            activity = discord.Activity(type=discord.ActivityType.listening, name=activity_text)
        elif activity_type == "watching":
            activity = discord.Activity(type=discord.ActivityType.watching, name=activity_text)
        elif activity_type == "competing":
            activity = discord.Activity(type=discord.ActivityType.competing, name=activity_text)
        else:
            activity = discord.Game(name=activity_text)
        
        # Определение статуса Discord
        discord_status = discord.Status.online
        if discord_status_str == "idle":
            discord_status = discord.Status.idle
        elif discord_status_str == "dnd":
            discord_status = discord.Status.dnd
        elif discord_status_str == "invisible":
            discord_status = discord.Status.invisible
        elif discord_status_str == "offline":
            discord_status = discord.Status.offline
        
        await self.change_presence(status=discord_status, activity=activity)
        print(f"✅ Статус бота обновлён: {discord_status_str} | Активность: {activity_type} - {activity_text}")

    async def check_mutes_task(self):
        """Фоновая задача для проверки и снятия истёкших мутов"""
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                import time
                current_time = time.time()
                
                # Получение всех истёкших мутов
                expired_mutes = await self.db.get_all_expired_mutes(current_time)
                
                for mute_data in expired_mutes:
                    guild = self.get_guild(mute_data["guild_id"])
                    if not guild:
                        continue
                    
                    member = guild.get_member(mute_data["user_id"])
                    if not member:
                        # Удаляем мут из БД, если пользователя нет на сервере
                        await self.db.remove_mute(mute_data["user_id"], mute_data["guild_id"])
                        continue
                    
                    mute_role = discord.utils.get(guild.roles, name="Muted")
                    if mute_role and mute_role in member.roles:
                        try:
                            await member.remove_roles(mute_role, reason="Автоматическое снятие мута")
                            await self.db.remove_mute(mute_data["user_id"], mute_data["guild_id"])
                        except Exception as e:
                            print(f"Ошибка при снятии мута с {member}: {e}")
                
                await asyncio.sleep(60)  # Проверка каждую минуту
            except Exception as e:
                print(f"Ошибка при проверке мутов: {e}")
                await asyncio.sleep(60)


async def main():
    """Главная функция"""
    bot = SecurityBot()
    
    token = bot.config.get_bot_token()
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("❌ Ошибка: Токен бота не установлен в config.json!")
        sys.exit(1)
    
    try:
        await bot.start(token)
    except KeyboardInterrupt:
        print("\nОстановка бота...")
        await bot.close()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
        await bot.close()


if __name__ == "__main__":
    asyncio.run(main())

