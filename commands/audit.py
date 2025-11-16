import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import List, Optional

class AuditCommands(commands.Cog):
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
        
        if interaction.user.guild_permissions.view_audit_log:
            return True
        
        return False

    @app_commands.command(name="audit", description="Показать последние 200 действий из Audit Log")
    async def audit(self, interaction: discord.Interaction):
        """Показать последние 200 действий из Audit Log"""
        if not await self.check_permissions(interaction):
            await interaction.response.send_message(
                "**Доступ запрещён.** У вас нет прав для просмотра Audit Log.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            # Получение последних 200 записей из Audit Log
            entries = []
            async for entry in interaction.guild.audit_logs(limit=200):
                entries.append(entry)
            
            if not entries:
                await interaction.followup.send("**Audit Log пуст.** Нет записей для отображения.")
                return
            
            # Создание view с пагинацией
            view = AuditLogView(entries, interaction.user)
            embed = view.create_embed(0)
            
            await interaction.followup.send(embed=embed, view=view)
        except discord.Forbidden:
            await interaction.followup.send("**Ошибка.** У бота нет прав для просмотра Audit Log.")
        except Exception as e:
            await interaction.followup.send(f"**Ошибка.** Не удалось получить Audit Log: {str(e)}")


class AuditLogView(discord.ui.View):
    def __init__(self, entries: List[discord.AuditLogEntry], user: discord.Member):
        super().__init__(timeout=300)
        self.entries = entries
        self.user = user
        self.current_page = 0
        self.entries_per_page = 10
        self.max_page = (len(entries) - 1) // self.entries_per_page
        
        # Обновление кнопок
        self.update_buttons()
    
    def update_buttons(self):
        """Обновление состояния кнопок"""
        self.first_page.disabled = self.current_page == 0
        self.prev_page.disabled = self.current_page == 0
        self.next_page.disabled = self.current_page >= self.max_page
        self.last_page.disabled = self.current_page >= self.max_page
    
    def create_embed(self, page: int) -> discord.Embed:
        """Создание эмбеда для страницы"""
        start_idx = page * self.entries_per_page
        end_idx = min(start_idx + self.entries_per_page, len(self.entries))
        page_entries = self.entries[start_idx:end_idx]
        
        embed = discord.Embed(
            title="**AUDIT LOG**",
            description=f"↳ **Total:** `{len(self.entries)}` entries || **Page:** `{page + 1}/{self.max_page + 1}` ||",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )
        
        # Типы действий
        action_types = {
            discord.AuditLogAction.channel_create: "📝 Создан канал",
            discord.AuditLogAction.channel_delete: "🗑️ Удалён канал",
            discord.AuditLogAction.channel_update: "✏️ Обновлён канал",
            discord.AuditLogAction.role_create: "📝 Создана роль",
            discord.AuditLogAction.role_delete: "🗑️ Удалена роль",
            discord.AuditLogAction.role_update: "✏️ Обновлена роль",
            discord.AuditLogAction.member_kick: "👢 Кикнут участник",
            discord.AuditLogAction.member_ban: "🔨 Забанен участник",
            discord.AuditLogAction.member_unban: "✅ Разбанен участник",
            discord.AuditLogAction.member_update: "✏️ Обновлён участник",
            discord.AuditLogAction.message_delete: "🗑️ Удалено сообщение",
            discord.AuditLogAction.guild_update: "✏️ Обновлён сервер",
        }
        
        for entry in page_entries:
            action_name = action_types.get(entry.action, f"**{str(entry.action).replace('_', ' ').title()}**")
            user_name = entry.user.name if entry.user else "Неизвестно"
            user_id = entry.user.id if entry.user else "N/A"
            
            # Форматирование времени
            time_str = entry.created_at.strftime("%d.%m.%Y %H:%M:%S")
            
            # Детали действия
            details = []
            if entry.target:
                if isinstance(entry.target, discord.Member):
                    details.append(f"**Target:** `{entry.target.name}#{entry.target.discriminator}`")
                elif isinstance(entry.target, (discord.Role, discord.TextChannel, discord.VoiceChannel)):
                    details.append(f"**Target:** `{entry.target.name}`")
                else:
                    details.append(f"**Target:** `{str(entry.target)}`")
            
            if entry.reason:
                details.append(f"**Reason:** `{entry.reason}`")
            
            details_str = "\n".join(details) if details else "Нет деталей"
            
            embed.add_field(
                name=f"**{action_name}**",
                value=f"↳ **User:** `{user_name}` || ID: `{user_id}` ||\n"
                      f"↳ **Time:** `{time_str}`\n"
                      f"{details_str}",
                inline=False
            )
        
        embed.set_footer(text=f"Запросил: {self.user.name}")
        
        return embed
    
    @discord.ui.button(label="⏮️", style=discord.ButtonStyle.grey, row=0)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("**Доступ запрещён.** Это не ваша панель.", ephemeral=True)
            return
        
        self.current_page = 0
        self.update_buttons()
        embed = self.create_embed(self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.grey, row=0)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("**Доступ запрещён.** Это не ваша панель.", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.grey, row=0)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("**Доступ запрещён.** Это не ваша панель.", ephemeral=True)
            return
        
        if self.current_page < self.max_page:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="⏭️", style=discord.ButtonStyle.grey, row=0)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("**Доступ запрещён.** Это не ваша панель.", ephemeral=True)
            return
        
        self.current_page = self.max_page
        self.update_buttons()
        embed = self.create_embed(self.current_page)
        await interaction.response.edit_message(embed=embed, view=self)


