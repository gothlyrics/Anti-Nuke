import discord
from discord.ext import commands
from datetime import datetime
from typing import Optional

class MemberEvents(commands.Cog):
    def __init__(self, bot: commands.Bot, db, config, verification_system, anti_bot, anti_raid, advanced_protection, alarm_system, shadow_logs, anti_permission_elevation):
        self.bot = bot
        self.db = db
        self.config = config
        self.verification_system = verification_system
        self.anti_bot = anti_bot
        self.anti_raid = anti_raid
        self.advanced_protection = advanced_protection
        self.alarm_system = alarm_system
        self.shadow_logs = shadow_logs
        self.anti_permission_elevation = anti_permission_elevation
        self.join_times = {}  # Для проверки подозрительных часов входа

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Обработка присоединения нового участника"""
        guild = member.guild

        # Проверка на чёрный список
        blacklist_info = await self.db.is_blacklisted(member.id, guild.id)
        if blacklist_info:
            try:
                await member.ban(reason=f"Чёрный список: {blacklist_info['reason']}", delete_message_days=0)
            except:
                try:
                    await member.kick(reason=f"Чёрный список: {blacklist_info['reason']}")
                except:
                    pass
            return

        # Проверка на RAID
        if not await self.anti_raid.check_join(member):
            return

        # Проверка бота
        if member.bot:
            if not await self.anti_bot.check_bot_join(member):
                return

        # Выдача роли непроверенного
        unverified_role_id = self.config.get_role("unverified")
        if unverified_role_id:
            unverified_role = guild.get_role(int(unverified_role_id))
            if unverified_role:
                try:
                    await member.add_roles(unverified_role, reason="Автовыдача роли при входе")
                except:
                    pass

        # Логирование присоединения
        await self.log_member_join(member)

        # Проверка на фейковый аккаунт
        if await self.advanced_protection.check_fake_account(member):
            await self.log_fake_account(member)

        # Проверка подозрительного никнейма
        if await self.advanced_protection.check_suspicious_nickname(member):
            await self.log_suspicious_nickname(member)

        # Проверка подозрительных часов входа (ночные регистрации)
        current_hour = datetime.utcnow().hour
        if current_hour >= 2 and current_hour <= 6:  # Ночь (2-6 утра)
            self.join_times[member.id] = datetime.utcnow()
            # Если много регистраций ночью - пометка как RAID
            night_joins = sum(1 for join_time in self.join_times.values() 
                            if (datetime.utcnow() - join_time).total_seconds() < 300)
            if night_joins >= 5:
                await self.alarm_system.trigger_alarm(member.guild, "night_raid", "Много регистраций ночью")
                await self.shadow_logs.send_shadow_log("night_raid", member.guild, f"Обнаружено {night_joins} регистраций ночью", None)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Обработка обновления участника"""
        # Проверка изменения никнейма
        if before.display_name != after.display_name:
            if await self.advanced_protection.check_suspicious_nickname(after):
                await self.log_suspicious_nickname(after)
                # Можно автоматически изменить никнейм обратно
                try:
                    await after.edit(nick=before.display_name, reason="Подозрительный никнейм")
                except:
                    pass
        
        # Проверка Anti-Permission Elevation (выдача ролей)
        if before.roles != after.roles:
            added_roles = [r for r in after.roles if r not in before.roles]
            if added_roles and after.guild.me.guild_permissions.view_audit_log:
                async for entry in after.guild.audit_logs(action=discord.AuditLogAction.member_role_update, limit=1):
                    if entry.user and entry.user.id != self.bot.user.id:
                        for role in added_roles:
                            await self.anti_permission_elevation.check_member_role_add(after, role, entry.user)
                        break

    async def log_member_join(self, member: discord.Member):
        """Логирование присоединения"""
        log_channel_id = self.config.get_channel("join_logs")
        if not log_channel_id:
            return

        log_channel = member.guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        account_age = (datetime.utcnow() - member.created_at).days

        embed = discord.Embed(
            title="👤 Новый участник",
            description=f"**Пользователь:** {member.mention} (`{member.id}`)\n**Аккаунт создан:** {member.created_at.strftime('%d.%m.%Y %H:%M')}\n**Возраст аккаунта:** {account_age} дней",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)
        embed.set_footer(text=f"Всего участников: {member.guild.member_count}")

        await log_channel.send(embed=embed)

    async def log_fake_account(self, member: discord.Member):
        """Логирование фейкового аккаунта"""
        log_channel_id = self.config.get_channel("security_logs")
        if not log_channel_id:
            return

        log_channel = member.guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title="⚠️ Подозрительный аккаунт",
            description=f"**Пользователь:** {member.mention} (`{member.id}`)\n**Возраст аккаунта:** {(datetime.utcnow() - member.created_at).days} дней",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)

        await log_channel.send(embed=embed)

    async def log_suspicious_nickname(self, member: discord.Member):
        """Логирование подозрительного никнейма"""
        log_channel_id = self.config.get_channel("security_logs")
        if not log_channel_id:
            return

        log_channel = member.guild.get_channel(int(log_channel_id))
        if not log_channel:
            return

        embed = discord.Embed(
            title="⚠️ Подозрительный никнейм",
            description=f"**Пользователь:** {member.mention} (`{member.id}`)\n**Никнейм:** {member.display_name}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_author(name=str(member), icon_url=member.display_avatar.url)

        await log_channel.send(embed=embed)

