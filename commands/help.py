import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

class HelpCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, config):
        self.bot = bot
        self.config = config

    def create_main_embed(self) -> discord.Embed:
        """Создание главного эмбеда помощи"""
        embed = discord.Embed(
            title="**SECURITY BOT HELP**",
            description="Выберите категорию команд для просмотра подробной информации\n\n"
                       "Используйте кнопки ниже для навигации по разделам",
            color=discord.Color.dark_grey()
        )
        
        embed.add_field(
            name="**Доступные категории**",
            value="`Модерация` - Команды для управления сервером\n"
                  "`Чёрный список` - Управление чёрным списком\n"
                  "`Владелец` - Команды только для владельца\n"
                  "`Безопасность` - Панель управления защитой",
            inline=False
        )
        
        embed.add_field(
            name="**Префиксные команды**",
            value="`!addl <bot_id>` - Добавить бота в whitelist\n"
                  "`!logs` - Показать информацию о системе логирования",
            inline=False
        )
        
        embed.set_footer(text="Security Bot")
        
        return embed

    def create_moderation_embed(self) -> discord.Embed:
        """Создание эмбеда команд модерации"""
        embed = discord.Embed(
            title="**MODERATION COMMANDS**",
            description="Команды для управления сервером и модерации",
            color=discord.Color.dark_grey()
        )
        
        embed.add_field(
            name="**Основные команды**",
            value="`/mute <member> [duration] [reason]` - Заглушить пользователя\n"
                  "`/unmute <member>` - Снять мут с пользователя\n"
                  "`/kick <member> [reason]` - Исключить пользователя\n"
                  "`/ban <member> [reason] [delete_days]` - Забанить пользователя",
            inline=False
        )
        
        embed.add_field(
            name="**Предупреждения**",
            value="`/warn <member> [reason]` - Выдать предупреждение\n"
                  "`/unwarn <member> [warning_id]` - Снять предупреждение",
            inline=False
        )
        
        embed.add_field(
            name="**Управление каналами**",
            value="`/clear <amount>` - Очистить сообщения (1-100)\n"
                  "`/slowmode <seconds>` - Установить медленный режим\n"
                  "`/lock` - Заблокировать канал\n"
                  "`/unlock` - Разблокировать канал",
            inline=False
        )
        
        embed.set_footer(text="Security Bot")
        
        return embed

    def create_blacklist_embed(self) -> discord.Embed:
        """Создание эмбеда команд чёрного списка"""
        embed = discord.Embed(
            title="**BLACKLIST COMMANDS**",
            description="Команды для управления чёрным списком",
            color=discord.Color.dark_grey()
        )
        
        embed.add_field(
            name="**Команды чёрного списка**",
            value="`/blacklistadd <user> [duration] [reason]` - Добавить пользователя в чёрный список\n"
                  "`/blacklistcheck <user>` - Проверить пользователя в чёрном списке\n"
                  "`/blacklistremove <user>` - Удалить пользователя из чёрного списка",
            inline=False
        )
        
        embed.add_field(
            name="**Формат длительности**",
            value="`1d` - 1 день\n"
                  "`2h` - 2 часа\n"
                  "`30m` - 30 минут\n"
                  "`permanent` - Навсегда",
            inline=False
        )
        
        embed.set_footer(text="Security Bot")
        
        return embed

    def create_owner_embed(self) -> discord.Embed:
        """Создание эмбеда команд владельца"""
        embed = discord.Embed(
            title="**OWNER COMMANDS**",
            description="Команды доступные только владельцу бота",
            color=discord.Color.dark_grey()
        )
        
        embed.add_field(
            name="**Команды защиты**",
            value="`/protectionoff` - Отключить абсолютно всю защиту\n"
                  "`/protectionon` - Включить обратно всю защиту",
            inline=False
        )
        
        embed.add_field(
            name="**Управление сервером**",
            value="`/restoreall` - Перепривязать всем роль unverified\n"
                  "`/restore` - Восстановить сервер из бэкапа\n"
                  "`/ownerlock` - Заблокировать всех модераторов",
            inline=False
        )
        
        embed.set_footer(text="Security Bot | Owner Only")
        
        return embed

    def create_security_embed(self) -> discord.Embed:
        """Создание эмбеда команд безопасности"""
        embed = discord.Embed(
            title="**SECURITY COMMANDS**",
            description="Команды для управления безопасностью сервера",
            color=discord.Color.dark_grey()
        )
        
        embed.add_field(
            name="**Панель управления**",
            value="`/panel` - Открыть панель управления безопасностью",
            inline=False
        )
        
        embed.add_field(
            name="**Активные системы защиты**",
            value=f"Anti-Bot: `{'Включено' if self.config.is_enabled('security', 'anti_bot') else 'Выключено'}`\n"
                  f"Anti-Nuke: `{'Включено' if self.config.is_enabled('security', 'anti_nuke') else 'Выключено'}`\n"
                  f"Anti-Spam: `{'Включено' if self.config.is_enabled('security', 'anti_spam') else 'Выключено'}`\n"
                  f"Anti-Raid: `{'Включено' if self.config.is_enabled('security', 'anti_raid') else 'Выключено'}`\n"
                  f"Верификация: `{'Включено' if self.config.is_enabled('verification') else 'Выключено'}`",
            inline=False
        )
        
        embed.set_footer(text="Security Bot")
        
        return embed

    @app_commands.command(name="help", description="Показать справку по командам бота")
    async def help_command(self, interaction: discord.Interaction):
        view = HelpView(self)
        embed = self.create_main_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class HelpView(discord.ui.View):
    def __init__(self, help_cog: HelpCommands):
        super().__init__(timeout=300)
        self.help_cog = help_cog
        self.current_page = "main"

    @discord.ui.button(label="Модерация", style=discord.ButtonStyle.grey, row=0)
    async def moderation_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.help_cog.create_moderation_embed()
        self.current_page = "moderation"
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Чёрный список", style=discord.ButtonStyle.grey, row=0)
    async def blacklist_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.help_cog.create_blacklist_embed()
        self.current_page = "blacklist"
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Владелец", style=discord.ButtonStyle.grey, row=0)
    async def owner_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.help_cog.create_owner_embed()
        self.current_page = "owner"
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Безопасность", style=discord.ButtonStyle.grey, row=0)
    async def security_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.help_cog.create_security_embed()
        self.current_page = "security"
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Главная", style=discord.ButtonStyle.grey, row=1)
    async def main_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = self.help_cog.create_main_embed()
        self.current_page = "main"
        await interaction.response.edit_message(embed=embed, view=self)
