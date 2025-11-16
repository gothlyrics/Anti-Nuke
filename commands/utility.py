import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import Optional

class UtilityCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, config):
        self.bot = bot
        self.config = config

    @app_commands.command(name="avatar", description="Показать аватар пользователя")
    @app_commands.describe(user="Пользователь (по умолчанию вы)")
    async def avatar(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Показать аватар пользователя"""
        target = user or interaction.user
        
        embed = discord.Embed(
            title=f"**{target.name}#{target.discriminator}**",
            description=f"↳ **Member:** `{target.name}#{target.discriminator}` || ID: `{target.id}` ||",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_image(url=target.display_avatar.url)
        embed.set_footer(text=f"Запросил: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Полные данные пользователя")
    @app_commands.describe(user="Пользователь (по умолчанию вы)")
    async def userinfo(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Полные данные пользователя"""
        target = user or interaction.user
        
        # Основная информация
        created_at = target.created_at.strftime("%d.%m.%Y %H:%M:%S")
        joined_at = target.joined_at.strftime("%d.%m.%Y %H:%M:%S") if target.joined_at else "Неизвестно"
        
        # Роли
        roles = [role.mention for role in target.roles[1:]]  # Исключаем @everyone
        roles_str = ", ".join(roles[:10]) if roles else "Нет ролей"
        if len(roles) > 10:
            roles_str += f" и ещё {len(roles) - 10}"
        
        # Статус
        status_emoji = {
            discord.Status.online: "🟢",
            discord.Status.idle: "🟡",
            discord.Status.dnd: "🔴",
            discord.Status.offline: "⚫"
        }
        status = status_emoji.get(target.status, "⚫")
        
        embed = discord.Embed(
            title=f"**{target.name}#{target.discriminator}**",
            description=f"↳ **Member:** `{target.name}#{target.discriminator}` || ID: `{target.id}` ||",
            color=target.color if target.color.value != 0 else discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(
            name="**Основная информация**",
            value=f"**Статус:** {status} `{str(target.status).upper()}`\n"
                  f"**Аккаунт создан:** `{created_at}`\n"
                  f"**Присоединился:** `{joined_at}`\n"
                  f"**Бот:** `{'Да' if target.bot else 'Нет'}`",
            inline=False
        )
        
        embed.add_field(
            name="**Роли**",
            value=roles_str if len(roles_str) < 1024 else f"{len(roles)} ролей",
            inline=False
        )
        
        embed.add_field(
            name="**Права**",
            value=f"**Администратор:** `{'Да' if target.guild_permissions.administrator else 'Нет'}`\n"
                  f"**Модератор:** `{'Да' if target.guild_permissions.manage_messages else 'Нет'}`\n"
                  f"**Высшая роль:** {target.top_role.mention if target.top_role else 'Нет'}",
            inline=False
        )
        
        embed.set_footer(text=f"Запросил: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Информация о сервере")
    async def serverinfo(self, interaction: discord.Interaction):
        """Информация о сервере"""
        guild = interaction.guild
        
        # Основная информация
        created_at = guild.created_at.strftime("%d.%m.%Y %H:%M:%S")
        owner = guild.owner.mention if guild.owner else "Неизвестно"
        
        # Статистика
        text_channels = len([ch for ch in guild.channels if isinstance(ch, discord.TextChannel)])
        voice_channels = len([ch for ch in guild.channels if isinstance(ch, discord.VoiceChannel)])
        categories = len(guild.categories)
        roles_count = len(guild.roles)
        emojis_count = len(guild.emojis)
        members_count = guild.member_count
        online_members = len([m for m in guild.members if m.status != discord.Status.offline])
        
        embed = discord.Embed(
            title=f"**{guild.name}**",
            description=f"↳ **Server:** `{guild.name}` || ID: `{guild.id}` ||",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(
            name="**Основная информация**",
            value=f"**Владелец:** {owner}\n"
                  f"**Создан:** `{created_at}`\n"
                  f"**Регион:** `{guild.region if hasattr(guild, 'region') else 'N/A'}`\n"
                  f"**Уровень верификации:** `{str(guild.verification_level).replace('_', ' ').title()}`",
            inline=False
        )
        
        embed.add_field(
            name="**Статистика**",
            value=f"**Участников:** `{members_count}` (🟢 `{online_members}` онлайн)\n"
                  f"**Каналов:** `{text_channels}` текстовых, `{voice_channels}` голосовых\n"
                  f"**Категорий:** `{categories}`\n"
                  f"**Ролей:** `{roles_count}`\n"
                  f"**Эмодзи:** `{emojis_count}`",
            inline=False
        )
        
        embed.add_field(
            name="**Особенности**",
            value=f"**Бусты:** `{guild.premium_tier}` уровень (`{guild.premium_subscription_count}` бустов)\n"
                  f"**Системный канал:** {guild.system_channel.mention if guild.system_channel else 'Не установлен'}\n"
                  f"**AFK канал:** {guild.afk_channel.mention if guild.afk_channel else 'Не установлен'}",
            inline=False
        )
        
        embed.set_footer(text=f"Запросил: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="channelinfo", description="Информация о канале")
    @app_commands.describe(channel="Канал (по умолчанию текущий)")
    async def channelinfo(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Информация о канале"""
        target = channel or interaction.channel
        
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("**Ошибка.** Эта команда работает только с текстовыми каналами.", ephemeral=True)
            return
        
        created_at = target.created_at.strftime("%d.%m.%Y %H:%M:%S")
        category = target.category.name if target.category else "Без категории"
        
        embed = discord.Embed(
            title=f"**#{target.name}**",
            description=f"↳ **Channel:** `#{target.name}` || ID: `{target.id}` ||",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="**Основная информация**",
            value=f"**Название:** `#{target.name}`\n"
                  f"**Категория:** `{category}`\n"
                  f"**Создан:** `{created_at}`\n"
                  f"**Позиция:** `{target.position}`",
            inline=False
        )
        
        embed.add_field(
            name="**Настройки**",
            value=f"**NSFW:** `{'Да' if target.nsfw else 'Нет'}`\n"
                  f"**Медленный режим:** `{target.slowmode_delay} секунд`\n"
                  f"**Тема:** `{target.topic if target.topic else 'Не установлена'}`",
            inline=False
        )
        
        # Подсчёт участников с доступом
        members_with_access = 0
        for member in target.guild.members:
            if target.permissions_for(member).view_channel:
                members_with_access += 1
        
        embed.add_field(
            name="**Доступ**",
            value=f"**Участников с доступом:** `{members_with_access}`\n"
                  f"**Тематических разрешений:** `{len(target.overwrites)}`",
            inline=False
        )
        
        embed.set_footer(text=f"Запросил: {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)


