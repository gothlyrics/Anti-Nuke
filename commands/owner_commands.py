import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from typing import Optional


class BackupGroup(app_commands.Group):
    """Группа команд для управления бэкапами"""
    def __init__(self, bot: commands.Bot, db, config, server_backup, owner_id: int):
        super().__init__(name="backup", description="Управление бэкапами сервера")
        self.bot = bot
        self.db = db
        self.config = config
        self.server_backup = server_backup
        self.owner_id = owner_id

    async def is_owner(self, user: discord.User) -> bool:
        """Проверка, является ли пользователь владельцем"""
        return user.id == self.owner_id

    @app_commands.command(name="create", description="Создать резервную копию сервера")
    async def backup_create(self, interaction: discord.Interaction):
        """Создать резервную копию сервера"""
        if not await self.is_owner(interaction.user):
            await interaction.response.send_message("**Доступ запрещён.** Только владелец может использовать эту команду.", ephemeral=True)
            return
        
        await interaction.response.defer()
        await self.server_backup.create_backup(interaction.guild)
        
        embed = discord.Embed(
            title="**BACKUP CREATED**",
            description=f"↳ **Status:** `Бэкап создан успешно`\n↳ **Guild:** `{interaction.guild.name}`",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="restore", description="Восстановить структуру сервера")
    @app_commands.describe(backup_id="ID бэкапа (оставьте пустым для последнего)")
    async def backup_restore(self, interaction: discord.Interaction, backup_id: Optional[str] = None):
        """Восстановить структуру сервера"""
        if not await self.is_owner(interaction.user):
            await interaction.response.send_message("**Доступ запрещён.** Только владелец может использовать эту команду.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        if backup_id:
            # Восстановление конкретного бэкапа (если будет реализовано)
            success = await self.server_backup.restore_from_backup(interaction.guild)
        else:
            # Восстановление последнего бэкапа
            success = await self.server_backup.restore_from_backup(interaction.guild)
        
        if success:
            embed = discord.Embed(
                title="**BACKUP RESTORED**",
                description=f"↳ **Status:** `Сервер восстановлен из бэкапа`\n↳ **Guild:** `{interaction.guild.name}`",
                color=discord.Color.dark_grey(),
                timestamp=datetime.utcnow()
            )
        else:
            embed = discord.Embed(
                title="**RESTORE FAILED**",
                description=f"↳ **Status:** `Ошибка восстановления`\n↳ **Reason:** `Бэкап не найден`",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="list", description="Показать доступные бэкапы")
    async def backup_list(self, interaction: discord.Interaction):
        """Показать доступные бэкапы"""
        if not await self.is_owner(interaction.user):
            await interaction.response.send_message("**Доступ запрещён.** Только владелец может использовать эту команду.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Получение списка бэкапов из БД
        try:
            cursor = await self.db.conn.execute("""
                SELECT created_at FROM server_backups
                WHERE guild_id = ?
                ORDER BY created_at DESC
                LIMIT 10
            """, (interaction.guild.id,))
            rows = await cursor.fetchall()
            
            if not rows:
                embed = discord.Embed(
                    title="**BACKUP LIST**",
                    description="↳ **Status:** `Бэкапы не найдены`",
                    color=discord.Color.dark_grey(),
                    timestamp=datetime.utcnow()
                )
            else:
                backup_list = []
                for idx, row in enumerate(rows, 1):
                    timestamp = datetime.fromtimestamp(row[0])
                    backup_list.append(f"`{idx}.` {timestamp.strftime('%d.%m.%Y %H:%M:%S')}")
                
                embed = discord.Embed(
                    title="**BACKUP LIST**",
                    description=f"↳ **Total:** `{len(rows)} бэкапов`\n\n" + "\n".join(backup_list),
                    color=discord.Color.dark_grey(),
                    timestamp=datetime.utcnow()
                )
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="**ERROR**",
                description=f"↳ **Status:** `Ошибка получения списка бэкапов`\n↳ **Error:** `{str(e)}`",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await interaction.followup.send(embed=embed)


class OwnerCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, db, config, protection_shadows, lockdown_system, server_backup, owner_lock):
        self.bot = bot
        self.db = db
        self.config = config
        self.protection_shadows = protection_shadows
        self.lockdown_system = lockdown_system
        self.server_backup = server_backup
        self.owner_lock = owner_lock
        self.owner_id = 1329899250758451300
        self.protection_enabled = True  # Глобальный флаг защиты
        
        # Регистрация группы команд backup
        self.backup_group = BackupGroup(bot, db, config, server_backup, self.owner_id)
        self.bot.tree.add_command(self.backup_group)

    async def is_owner(self, user: discord.User) -> bool:
        """Проверка, является ли пользователь владельцем"""
        return user.id == self.owner_id

    @app_commands.command(name="protectionoff", description="Отключить абсолютно всю защиту (только владелец)")
    async def protection_off(self, interaction: discord.Interaction):
        if not await self.is_owner(interaction.user):
            await interaction.response.send_message("**Доступ запрещён.** Только владелец может использовать эту команду.", ephemeral=True)
            return

        self.protection_enabled = False
        
        embed = discord.Embed(
            title="**PROTECTION OFF**",
            description="↳ **Status:** `Вся защита отключена`\n↳ **Warning:** `Сервер уязвим для атак`",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="protectionon", description="Включить обратно абсолютно всю защиту (только владелец)")
    async def protection_on(self, interaction: discord.Interaction):
        if not await self.is_owner(interaction.user):
            await interaction.response.send_message("**Доступ запрещён.** Только владелец может использовать эту команду.", ephemeral=True)
            return

        self.protection_enabled = True
        
        embed = discord.Embed(
            title="**PROTECTION ON**",
            description="↳ **Status:** `Вся защита включена`",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="restoreall", description="Перепривязать всем роль unverified (только владелец)")
    async def restore_all_roles(self, interaction: discord.Interaction):
        if not await self.is_owner(interaction.user):
            await interaction.response.send_message("**Доступ запрещён.** Только владелец может использовать эту команду.", ephemeral=True)
            return

        guild = interaction.guild
        unverified_role_id = self.config.get_role("unverified")
        verified_role_id = self.config.get_role("verified")
        
        if not unverified_role_id:
            await interaction.response.send_message("**Ошибка:** Роль unverified не настроена.", ephemeral=True)
            return

        unverified_role = guild.get_role(int(unverified_role_id))
        verified_role = guild.get_role(int(verified_role_id)) if verified_role_id else None
        
        if not unverified_role:
            await interaction.response.send_message("**Ошибка:** Роль unverified не найдена.", ephemeral=True)
            return

        await interaction.response.defer()
        
        restored_count = 0
        for member in guild.members:
            if member.bot:
                continue
            
            try:
                # Удаляем verified роль если есть
                if verified_role and verified_role in member.roles:
                    await member.remove_roles(verified_role, reason="Перепривязка ролей после атаки")
                
                # Добавляем unverified роль если её нет
                if unverified_role not in member.roles:
                    await member.add_roles(unverified_role, reason="Перепривязка ролей после атаки")
                    restored_count += 1
            except:
                pass

        embed = discord.Embed(
            title="**ROLES RESTORED**",
            description=f"↳ **Restored:** `{restored_count} пользователей`\n↳ **Role:** `{unverified_role.name}`",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="ownerlock", description="Заблокировать всех модераторов (только владелец)")
    async def owner_lock(self, interaction: discord.Interaction):
        if not await self.is_owner(interaction.user):
            await interaction.response.send_message("**Доступ запрещён.** Только владелец может использовать эту команду.", ephemeral=True)
            return

        if self.owner_lock.is_locked(interaction.guild.id):
            await self.owner_lock.disable_owner_lock(interaction.guild)
            status = "отключён"
        else:
            await self.owner_lock.enable_owner_lock(interaction.guild)
            status = "включён"

        embed = discord.Embed(
            title="**OWNER LOCK**",
            description=f"↳ **Status:** `Owner Lock {status}`\n↳ **Guild:** `{interaction.guild.name}`",
            color=discord.Color.dark_grey(),
            timestamp=datetime.utcnow()
        )
        
        await interaction.response.send_message(embed=embed)

