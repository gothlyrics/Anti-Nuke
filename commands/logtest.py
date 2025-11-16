import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime

class LogTestCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, config):
        self.bot = bot
        self.config = config

    async def check_permissions(self, interaction: discord.Interaction) -> bool:
        """Проверка прав на использование команд"""
        admin_role_id = self.config.get_role("admin")
        if admin_role_id:
            if isinstance(admin_role_id, list):
                for role_id in admin_role_id:
                    admin_role = interaction.guild.get_role(int(role_id))
                    if admin_role and admin_role in interaction.user.roles:
                        return True
            else:
                admin_role = interaction.guild.get_role(int(admin_role_id))
                if admin_role and admin_role in interaction.user.roles:
                    return True
        
        if interaction.user.guild_permissions.administrator:
            return True
        
        return False

    @app_commands.command(name="logtest", description="Отправить тест-лог каждого типа для проверки")
    async def logtest(self, interaction: discord.Interaction):
        """Отправить тест-лог каждого типа"""
        if not await self.check_permissions(interaction):
            await interaction.response.send_message(
                "**Доступ запрещён.** У вас нет прав для использования этой команды.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        test_user = interaction.user
        
        # Тест-логи для разных каналов
        logs_sent = []
        
        # 1. Лог верификации
        verification_logs_id = self.config.get_channel("verification_logs")
        if verification_logs_id:
            channel = guild.get_channel(int(verification_logs_id))
            if channel:
                embed = discord.Embed(
                    title=f"**{test_user.name}#{test_user.discriminator} verification**",
                    description=f"↳ **Member:** `{test_user.name}#{test_user.discriminator}` || ID: `{test_user.id}` ||\n↳ **Reason:** `Тестовый лог верификации`",
                    color=discord.Color.dark_grey(),
                    timestamp=datetime.utcnow()
                )
                await channel.send(embed=embed)
                logs_sent.append("✅ Верификация")
        
        # 2. Лог присоединений
        join_logs_id = self.config.get_channel("join_logs")
        if join_logs_id:
            channel = guild.get_channel(int(join_logs_id))
            if channel:
                embed = discord.Embed(
                    title=f"**{test_user.name}#{test_user.discriminator} join**",
                    description=f"↳ **Member:** `{test_user.name}#{test_user.discriminator}` || ID: `{test_user.id}` ||\n↳ **Reason:** `Тестовый лог присоединения`",
                    color=discord.Color.dark_grey(),
                    timestamp=datetime.utcnow()
                )
                await channel.send(embed=embed)
                logs_sent.append("✅ Присоединения")
        
        # 3. Лог безопасности
        security_logs_id = self.config.get_channel("security_logs")
        if security_logs_id:
            channel = guild.get_channel(int(security_logs_id))
            if channel:
                embed = discord.Embed(
                    title=f"**SECURITY ALERT**",
                    description=f"↳ **Type:** `Тестовый лог безопасности`\n↳ **User:** `{test_user.name}#{test_user.discriminator}` || ID: `{test_user.id}` ||\n↳ **Reason:** `Тестовое событие безопасности`",
                    color=discord.Color.dark_grey(),
                    timestamp=datetime.utcnow()
                )
                await channel.send(embed=embed)
                logs_sent.append("✅ Безопасность")
        
        # 4. Лог модерации
        moderation_logs_id = self.config.get_channel("moderation_logs")
        if moderation_logs_id:
            channel = guild.get_channel(int(moderation_logs_id))
            if channel:
                embed = discord.Embed(
                    title=f"**{test_user.name}#{test_user.discriminator} mute**",
                    description=f"↳ **Member:** `{test_user.name}#{test_user.discriminator}` || ID: `{test_user.id}` ||\n↳ **Reason:** `Тестовый лог модерации`",
                    color=discord.Color.dark_grey(),
                    timestamp=datetime.utcnow()
                )
                await channel.send(embed=embed)
                logs_sent.append("✅ Модерация")
        
        # 5. Лог действий модераторов
        moderator_action_logs_id = self.config.get_channel("moderator_action_logs")
        if moderator_action_logs_id:
            channel = guild.get_channel(int(moderator_action_logs_id))
            if channel:
                embed = discord.Embed(
                    title=f"**MODERATOR ACTION**",
                    description=f"↳ **Moderator:** `{test_user.name}#{test_user.discriminator}` || ID: `{test_user.id}` ||\n↳ **Action:** `Тестовое действие`\n↳ **Reason:** `Тестовый лог действий модератора`",
                    color=discord.Color.dark_grey(),
                    timestamp=datetime.utcnow()
                )
                await channel.send(embed=embed)
                logs_sent.append("✅ Действия модераторов")
        
        # 6. Лог чёрного списка
        blacklist_logs_id = self.config.get_channel("blacklist_logs")
        if blacklist_logs_id:
            channel = guild.get_channel(int(blacklist_logs_id))
            if channel:
                embed = discord.Embed(
                    title=f"**BLACKLIST ACTION**",
                    description=f"↳ **User:** `{test_user.name}#{test_user.discriminator}` || ID: `{test_user.id}` ||\n↳ **Action:** `Тестовое добавление в чёрный список`\n↳ **Reason:** `Тестовый лог чёрного списка`",
                    color=discord.Color.dark_grey(),
                    timestamp=datetime.utcnow()
                )
                await channel.send(embed=embed)
                logs_sent.append("✅ Чёрный список")
        
        # Результат
        if logs_sent:
            result_embed = discord.Embed(
                title="**LOG TEST COMPLETE**",
                description="↳ **Status:** `Тестовые логи отправлены`\n\n" + "\n".join(logs_sent),
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
        else:
            result_embed = discord.Embed(
                title="**LOG TEST FAILED**",
                description="↳ **Status:** `Не удалось отправить тестовые логи`\n↳ **Reason:** `Каналы логов не настроены`",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
        
        await interaction.followup.send(embed=result_embed)

